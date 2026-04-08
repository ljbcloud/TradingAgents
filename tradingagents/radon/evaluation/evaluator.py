"""RadonEvaluator — 7-milestone evaluation pipeline.

Adapted from radon/scripts/evaluate.py. Orchestrates parallel data fetch
milestones (M1-M3B) and sequential decision milestones (M4-M7).

Milestones:
  M1  — Data availability check
  M2  — Strategy scan
  M3A — Convexity check
  M3B — Edge determination
  M4  — Risk management
  M5  — Kelly criterion sizing
  M6  — No naked shorts
  M7  — Final decision synthesis

Actual data wiring happens in T17; milestone functions return sensible stubs.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from tradingagents.radon.evaluation.models import (
    EvaluationResult,
    MilestoneResult,
    TradeDecision,
    ValidationStatus,
)

logger = logging.getLogger(__name__)

# Thresholds adapted from radon evaluate.py determine_edge()
_MIN_SUSTAINED_DAYS = 3
_MIN_FLOW_STRENGTH = 50.0
_ALT_RECENT_STRENGTH = 70.0
_MIN_WIN_RATE = 0.0
_MIN_RISK_REWARD = 0.0
_MIN_KELLY_FRACTION = 0.0


class RadonEvaluator:
    """Evaluate a ticker through 7 milestones.

    Parameters
    ----------
    config : dict | None
        Optional configuration overrides. Recognised keys:
        - ``skip_ib`` (bool): skip IB price fetch
        - ``flow_days`` (int): dark-pool lookback window
        - ``bankroll`` (float): starting capital for Kelly sizing
        - ``min_flow_strength`` (float): minimum aggregate flow strength
        - ``min_sustained_days`` (int): consecutive flow-direction days
        - ``alt_recent_strength`` (float): alternative single-day threshold
    """

    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}
        self.skip_ib: bool = cfg.get("skip_ib", False)
        self.flow_days: int = cfg.get("flow_days", 5)
        self.bankroll: float = cfg.get("bankroll", 1_200_000)
        self.min_flow_strength: float = cfg.get("min_flow_strength", _MIN_FLOW_STRENGTH)
        self.min_sustained_days: int = cfg.get(
            "min_sustained_days", _MIN_SUSTAINED_DAYS
        )
        self.alt_recent_strength: float = cfg.get(
            "alt_recent_strength", _ALT_RECENT_STRENGTH
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def milestone_names(self) -> list[str]:
        """Return the 7 milestone names in pipeline order."""
        return [
            "Data Fetch",
            "Strategy Scan",
            "Convexity",
            "Edge",
            "Risk Management",
            "Kelly Sizing",
            "No Naked Shorts",
        ]

    def evaluate(
        self,
        ticker: str,
        asset_type: str,
        trade_decision: str,
    ) -> EvaluationResult:
        """Run the full 7-milestone evaluation pipeline.

        Parameters
        ----------
        ticker : str
            Ticker symbol (e.g. ``"AAPL"``).
        asset_type : str
            Asset class (``"stock"``, ``"crypto"``, etc.).
        trade_decision : str
            Proposed trade direction (``"BUY"``, ``"SELL"``).

        Returns
        -------
        EvaluationResult
            Aggregated evaluation result with milestone outcomes.
        """
        logger.info(
            "Evaluating %s (%s) decision=%s", ticker, asset_type, trade_decision
        )

        # Crypto passthrough — skip Radon validation entirely
        if asset_type == "crypto":
            logger.info("Crypto passthrough for %s", ticker)
            return EvaluationResult(
                ticker=ticker.upper(),
                status=ValidationStatus.SKIP,
                decision=TradeDecision.PENDING,
                summary="Crypto assets skip Radon validation",
            )

        result = EvaluationResult(
            ticker=ticker.upper(),
            status=ValidationStatus.PENDING,
        )

        # ── Phase 1: Parallel milestones M1-M3B ────────────────────────
        milestones: dict[str, MilestoneResult] = {}
        parallel_results = self._run_parallel_milestones(ticker)

        # M1: Data Fetch — early exit on failure
        m1 = parallel_results.get("M1")
        if m1 is not None:
            milestones["M1"] = m1
            if not m1.passed:
                result.status = ValidationStatus.FAIL
                result.decision = TradeDecision.NO_TRADE
                result.milestones = list(milestones.values())
                result.summary = f"M1 Data Fetch failed: {m1.reason}"
                logger.warning("M1 failed for %s: %s", ticker, m1.reason)
                return result
        else:
            milestones["M1"] = MilestoneResult(
                milestone="M1", passed=False, reason="M1 result missing"
            )
            result.status = ValidationStatus.FAIL
            result.decision = TradeDecision.NO_TRADE
            result.milestones = list(milestones.values())
            result.summary = "M1 Data Fetch result missing"
            return result

        # M2: Strategy Scan
        m2 = parallel_results.get("M2")
        if m2 is not None:
            milestones["M2"] = m2

        # M3A: Convexity
        m3a = parallel_results.get("M3A")
        if m3a is not None:
            milestones["M3A"] = m3a

        # M3B: Edge determination
        m3b = parallel_results.get("M3B")
        if m3b is not None:
            milestones["M3B"] = m3b

        # ── Phase 2: Sequential milestones M4-M7 ───────────────────────

        # M4: Risk Management — early exit on failure
        m4 = self._milestone_m4_risk_management(ticker, milestones)
        milestones["M4"] = m4
        if not m4.passed:
            result.status = ValidationStatus.FAIL
            result.decision = TradeDecision.NO_TRADE
            result.milestones = list(milestones.values())
            result.summary = f"M4 Risk Management failed: {m4.reason}"
            logger.warning("M4 failed for %s: %s", ticker, m4.reason)
            return result

        # M5: Kelly Sizing
        m5 = self._milestone_m5_kelly_sizing(ticker, milestones)
        milestones["M5"] = m5

        # M6: No Naked Shorts
        m6 = self._milestone_m6_no_naked_shorts(ticker, trade_decision, milestones)
        milestones["M6"] = m6

        # M7: Final Decision
        m7 = self._milestone_m7_final_decision(ticker, trade_decision, milestones)
        milestones["M7"] = m7

        # Aggregate result
        result.milestones = list(milestones.values())
        result.status = ValidationStatus.PASS
        result.decision = TradeDecision.TRADE
        result.summary = "All milestones passed"
        logger.info("Evaluation passed for %s", ticker)
        return result

    # ------------------------------------------------------------------
    # Edge determination (adapted from evaluate.py determine_edge)
    # ------------------------------------------------------------------

    def determine_edge(
        self,
        flow: dict,
        options: dict | None = None,
        oi_changes: list[dict] | None = None,
        price_history: list[dict] | None = None,
        news: dict | None = None,
    ) -> dict[str, Any]:
        """Evaluate whether an actionable edge exists.

        Adapted from radon evaluate.py ``determine_edge()``.

        Criteria (ALL must be met, OR alternative):
          Primary:
            1. Sustained direction >= min_sustained_days consecutive days
            2. Aggregate flow strength > min_flow_strength
            3. Options confirm or don't contradict
            4. Signal not yet reflected in price

          Alternative (can replace criterion 1):
            1a. Most recent day flow strength > alt_recent_strength
        """
        dp = flow.get("dark_pool", {})
        agg = dp.get("aggregate", {})
        daily = dp.get("daily", [])

        agg_direction = agg.get("flow_direction", "NEUTRAL")
        agg_strength = float(agg.get("flow_strength", 0))
        agg_buy_ratio = float(agg.get("dp_buy_ratio") or 0.5)

        sustained = self._compute_sustained_days(daily, direction=agg_direction)
        recent_strength = float(daily[0].get("flow_strength", 0)) if daily else 0.0

        # Check if signal is priced in
        signal_priced_in = False
        if price_history and len(price_history) >= 2:
            first_close = price_history[0].get("close", 0)
            last_close = price_history[-1].get("close", 0)
            if first_close and last_close:
                pct_change = (last_close - first_close) / first_close
                if (agg_direction == "ACCUMULATION" and pct_change > 0.05) or (
                    agg_direction == "DISTRIBUTION" and pct_change < -0.05
                ):
                    signal_priced_in = True

        # Check options for conflict
        options_conflict = False
        if options:
            analysis = options.get("analysis", {})
            combined_bias = analysis.get("combined_bias", "NO_DATA")
            bias_map = {
                "BULLISH": "ACCUMULATION",
                "LEAN_BULLISH": "ACCUMULATION",
                "BEARISH": "DISTRIBUTION",
                "LEAN_BEARISH": "DISTRIBUTION",
            }
            expected_dp = bias_map.get(combined_bias)
            if expected_dp and expected_dp != agg_direction:
                options_conflict = True

        result: dict[str, Any] = {
            "passed": False,
            "reason": "",
            "sustained_days": sustained,
            "flow_strength": agg_strength,
            "recent_strength": recent_strength,
            "agg_direction": agg_direction,
            "agg_buy_ratio": agg_buy_ratio,
            "options_conflict": options_conflict,
            "signal_priced_in": signal_priced_in,
        }

        # Gate checks
        if agg_direction == "NEUTRAL":
            result["reason"] = (
                f"Aggregate flow direction is NEUTRAL (buy ratio {agg_buy_ratio:.1%})"
            )
            return result

        if agg_strength < self.min_flow_strength:
            result["reason"] = (
                f"Aggregate flow strength {agg_strength:.1f} below threshold "
                f"(need >{self.min_flow_strength})"
            )
            return result

        if signal_priced_in:
            result["reason"] = "Signal already reflected in price (>5% move)"
            return result

        primary_pass = sustained >= self.min_sustained_days
        alt_pass = recent_strength > self.alt_recent_strength

        if not primary_pass and not alt_pass:
            result["reason"] = (
                f"Sustained {agg_direction.lower()} days = {sustained} "
                f"(need >= {self.min_sustained_days}). "
                f"Recent strength = {recent_strength:.1f} "
                f"(need > {self.alt_recent_strength} for alternative). "
                f"Signal fading."
            )
            return result

        result["passed"] = True
        if primary_pass:
            result["reason"] = (
                f"{sustained} consecutive days of {agg_direction.lower()}, "
                f"strength {agg_strength:.1f}"
            )
        else:
            result["reason"] = (
                f"Recent strength {recent_strength:.1f} "
                f">{self.alt_recent_strength} (alternative criterion). "
                f"Sustained days = {sustained}."
            )
        return result

    # ------------------------------------------------------------------
    # Parallel milestone execution (M1-M3B)
    # ------------------------------------------------------------------

    def _run_parallel_milestones(self, ticker: str) -> dict[str, MilestoneResult]:
        """Execute M1-M3B concurrently via ThreadPoolExecutor.

        Returns dict keyed by milestone ID (``"M1"``, ``"M2"``, etc.).
        """
        results: dict[str, MilestoneResult] = {}

        def _m1() -> tuple[str, MilestoneResult]:
            return ("M1", self._milestone_m1_data_fetch(ticker))

        def _m2() -> tuple[str, MilestoneResult]:
            return ("M2", self._milestone_m2_strategy_scan(ticker))

        def _m3a() -> tuple[str, MilestoneResult]:
            return ("M3A", self._milestone_m3a_convexity(ticker))

        def _m3b() -> tuple[str, MilestoneResult]:
            return ("M3B", self._milestone_m3b_edge(ticker))

        tasks = [_m1, _m2, _m3a, _m3b]

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fn): fn.__name__ for fn in tasks}
            for future in as_completed(futures):
                fn_name = futures[future]
                try:
                    key, ms_result = future.result()
                    results[key] = ms_result
                except Exception:
                    logger.exception("Parallel milestone %s raised", fn_name)

        return results

    # ------------------------------------------------------------------
    # Individual milestone implementations (stubs)
    # ------------------------------------------------------------------

    def _milestone_m1_data_fetch(self, ticker: str) -> MilestoneResult:
        """M1 — Data availability check.

        Stub: returns passed=True. Actual data wiring in T17.
        """
        logger.debug("M1 Data Fetch (stub) for %s", ticker)
        return MilestoneResult(
            milestone="M1",
            passed=True,
            reason="Data available (stub)",
            data={"ticker": ticker.upper(), "verified": True},
        )

    def _milestone_m2_strategy_scan(self, ticker: str) -> MilestoneResult:
        """M2 — Strategy scan.

        Stub: returns passed=True with empty strategy data.
        """
        logger.debug("M2 Strategy Scan (stub) for %s", ticker)
        return MilestoneResult(
            milestone="M2",
            passed=True,
            reason="No conflicting signals (stub)",
            data={"ticker": ticker.upper(), "strategies": []},
        )

    def _milestone_m3a_convexity(self, ticker: str) -> MilestoneResult:
        """M3A — Convexity check.

        Stub: returns passed=True.
        """
        logger.debug("M3A Convexity (stub) for %s", ticker)
        return MilestoneResult(
            milestone="M3A",
            passed=True,
            reason="Convex structure (stub)",
            data={"ticker": ticker.upper()},
        )

    def _milestone_m3b_edge(self, ticker: str) -> MilestoneResult:
        """M3B — Edge determination.

        Stub: returns passed=True with default edge data.
        Actual flow/options/price analysis wired in T17.
        """
        logger.debug("M3B Edge (stub) for %s", ticker)
        return MilestoneResult(
            milestone="M3B",
            passed=True,
            reason="Edge present (stub)",
            data={
                "ticker": ticker.upper(),
                "edge_details": {
                    "sustained_days": 3,
                    "flow_strength": 60.0,
                    "agg_direction": "ACCUMULATION",
                },
            },
        )

    def _milestone_m4_risk_management(
        self, ticker: str, milestones: dict[str, MilestoneResult]
    ) -> MilestoneResult:
        """M4 — Risk management check.

        Stub: returns passed=True. In production this checks position sizing,
        portfolio risk, and drawdown limits.
        """
        logger.debug("M4 Risk Management (stub) for %s", ticker)
        return MilestoneResult(
            milestone="M4",
            passed=True,
            reason="Risk within limits (stub)",
            data={
                "ticker": ticker.upper(),
                "position_limit_ok": True,
                "portfolio_risk_ok": True,
            },
        )

    def _milestone_m5_kelly_sizing(
        self, ticker: str, milestones: dict[str, MilestoneResult]
    ) -> MilestoneResult:
        """M5 — Kelly criterion sizing.

        Stub: returns passed=True with a default fractional Kelly.
        Actual Kelly calculation wired via kelly.py in T17.
        """
        logger.debug("M5 Kelly Sizing (stub) for %s", ticker)
        return MilestoneResult(
            milestone="M5",
            passed=True,
            reason="Kelly size within bounds (stub)",
            data={
                "ticker": ticker.upper(),
                "kelly_fraction": 0.25,
                "suggested_size": self.bankroll * 0.25,
            },
        )

    def _milestone_m6_no_naked_shorts(
        self,
        ticker: str,
        trade_decision: str,
        milestones: dict[str, MilestoneResult],
    ) -> MilestoneResult:
        """M6 — No naked shorts check.

        Ensures no unlimited-risk positions are taken.
        Stub: returns passed=True.
        """
        logger.debug("M6 No Naked Shorts (stub) for %s", ticker)
        return MilestoneResult(
            milestone="M6",
            passed=True,
            reason="No naked short exposure (stub)",
            data={
                "ticker": ticker.upper(),
                "trade_decision": trade_decision,
                "naked_short_detected": False,
            },
        )

    def _milestone_m7_final_decision(
        self,
        ticker: str,
        trade_decision: str,
        milestones: dict[str, MilestoneResult],
    ) -> MilestoneResult:
        """M7 — Final decision synthesis.

        Aggregates all previous milestone results into a final go/no-go.
        Stub: returns passed=True.
        """
        logger.debug("M7 Final Decision (stub) for %s", ticker)
        all_passed = all(ms.passed for ms in milestones.values())
        return MilestoneResult(
            milestone="M7",
            passed=all_passed,
            reason=(
                "All milestones passed (stub)"
                if all_passed
                else "One or more milestones failed"
            ),
            data={
                "ticker": ticker.upper(),
                "trade_decision": trade_decision,
                "milestones_passed": sum(1 for ms in milestones.values() if ms.passed),
                "milestones_total": len(milestones),
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_sustained_days(
        daily: list[dict], direction: str = "ACCUMULATION"
    ) -> int:
        """Count consecutive days matching *direction* from most recent day.

        ``daily`` must be sorted most-recent-first (index 0 = today).
        Adapted from evaluate.py ``compute_sustained_days()``.
        """
        streak = 0
        for day in daily:
            if day.get("flow_direction") == direction:
                streak += 1
            else:
                break
        return streak

    def _run_in_ib_thread(self, coro: Any) -> Any:
        """Run an async coroutine in a dedicated thread with its own event loop.

        ib_insync requires its own asyncio event loop. This method creates
        a new event loop in a background thread, runs the coroutine, and
        returns the result. Actual IB calls wired in T8/T17.
        """
        result_container: dict[str, Any] = {}
        error_container: dict[str, str] = {}

        def _target() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_container["value"] = loop.run_until_complete(coro)
            except Exception as exc:
                error_container["error"] = str(exc)
            finally:
                loop.close()

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=30)

        if "error" in error_container:
            logger.warning("IB thread error: %s", error_container["error"])
            return None
        return result_container.get("value")
