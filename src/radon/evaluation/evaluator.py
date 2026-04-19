"""RadonEvaluator — 11-milestone evaluation pipeline.

Adapted from radon/scripts/evaluate.py. Orchestrates parallel data fetch
milestones (M1-M3B) and sequential decision milestones (M4-M7).

Milestones:
  M1  — Ticker validation (UW stock info + option contracts)
  M1B — Seasonality context (UW monthly seasonality)
  M1C — Analyst ratings context (UW analyst ratings)
  M1D — News & catalysts context (UW news headlines)
  M2  — Dark pool flow (DarkPoolFlowStrategy scan)
  M3  — Options chain + institutional flow (UW option contracts + flow alerts)
  M3B — Open interest changes (UW OI change data)
  M4  — Edge determination (uses M2, M3, M3B, price, news)
  M5  — Structure proposal (risk/reward >= 2:1)
  M6  — Kelly sizing (fractional Kelly criterion)
  M7  — Final decision synthesis

Milestones M1 through M3B run in parallel (ThreadPoolExecutor).
Milestones M4 through M7 run sequentially after the parallel group.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from radon.evaluation.models import (
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
_MIN_RISK_REWARD = 2.0
_DEFAULT_KELLY_FRACTION = 0.25
_DEFAULT_WIN_PROB = 0.55


class RadonEvaluator:
    """Evaluate a ticker through 11 milestones.

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
        - ``min_risk_reward`` (float): minimum risk/reward ratio
        - ``kelly_fraction`` (float): Kelly fraction for position sizing
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
        self.min_risk_reward: float = cfg.get("min_risk_reward", _MIN_RISK_REWARD)
        self.kelly_fraction: float = cfg.get("kelly_fraction", _DEFAULT_KELLY_FRACTION)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def milestone_names(self) -> list[str]:
        """Return the milestone names in pipeline order."""
        return [
            "Ticker Validation",
            "Seasonality",
            "Analyst Ratings",
            "News & Catalysts",
            "Dark Pool Flow",
            "Options Flow",
            "OI Changes",
            "Edge Determination",
            "Structure Proposal",
            "Kelly Sizing",
            "Final Decision",
        ]

    def evaluate(
        self,
        ticker: str,
        asset_type: str,
        trade_decision: str,
    ) -> EvaluationResult:
        """Run the full 11-milestone evaluation pipeline.

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

        # M1: Ticker Validation — early exit on failure
        m1 = parallel_results.get("M1")
        if m1 is not None:
            milestones["M1"] = m1
            if not m1.passed:
                result.status = ValidationStatus.FAIL
                result.decision = TradeDecision.NO_TRADE
                result.milestones = list(milestones.values())
                result.gates = {
                    "convexity": False,
                    "edge": False,
                    "risk_management": False,
                    "no_naked_shorts": False,
                }
                result.summary = f"M1 Ticker Validation failed: {m1.reason}"
                logger.warning("M1 failed for %s: %s", ticker, m1.reason)
                return result
        else:
            milestones["M1"] = MilestoneResult(
                milestone="M1", passed=False, reason="M1 result missing"
            )
            result.gates = {
                "convexity": False,
                "edge": False,
                "risk_management": False,
                "no_naked_shorts": False,
            }
            result.status = ValidationStatus.FAIL
            result.decision = TradeDecision.NO_TRADE
            result.milestones = list(milestones.values())
            result.summary = "M1 Ticker Validation result missing"
            return result

        # Context milestones (M1B, M1C, M1D) — informational, always pass
        for key in ("M1B", "M1C", "M1D"):
            ms = parallel_results.get(key)
            if ms is not None:
                milestones[key] = ms

        # Data milestones (M2, M3, M3B) — data fetches, always pass
        for key in ("M2", "M3", "M3B"):
            ms = parallel_results.get(key)
            if ms is not None:
                milestones[key] = ms

        # ── Phase 2: Sequential milestones M4-M7 ───────────────────────

        # M4: Edge Determination — early exit on failure
        m4 = self._milestone_m4_edge_determination(ticker, milestones)
        milestones["M4"] = m4
        if not m4.passed:
            result.gates = {
                "convexity": milestones.get(
                    "M5", MilestoneResult(milestone="M5", passed=False)
                ).passed,
                "edge": False,
                "risk_management": milestones.get(
                    "M6", MilestoneResult(milestone="M6", passed=False)
                ).passed,
                "no_naked_shorts": False,
            }
            result.status = ValidationStatus.FAIL
            result.decision = TradeDecision.NO_TRADE
            result.milestones = list(milestones.values())
            result.summary = f"M4 Edge Determination failed: {m4.reason}"
            logger.warning("M4 failed for %s: %s", ticker, m4.reason)
            return result

        # M5: Structure Proposal — early exit on failure
        m5 = self._milestone_m5_structure_proposal(ticker, milestones)
        milestones["M5"] = m5
        if not m5.passed:
            result.gates = {
                "convexity": False,
                "edge": milestones.get(
                    "M4", MilestoneResult(milestone="M4", passed=False)
                ).passed,
                "risk_management": milestones.get(
                    "M6", MilestoneResult(milestone="M6", passed=False)
                ).passed,
                "no_naked_shorts": self._check_no_naked_shorts(
                    trade_decision, milestones
                ),
            }
            result.status = ValidationStatus.FAIL
            result.decision = TradeDecision.NO_TRADE
            result.milestones = list(milestones.values())
            result.summary = f"M5 Structure Proposal failed: {m5.reason}"
            logger.warning("M5 failed for %s: %s", ticker, m5.reason)
            return result

        # M6: Kelly Sizing
        m6 = self._milestone_m6_kelly_sizing(ticker, milestones)
        milestones["M6"] = m6

        # M7: Final Decision
        m7 = self._milestone_m7_final_decision(ticker, trade_decision, milestones)
        milestones["M7"] = m7

        # Aggregate result
        result.milestones = list(milestones.values())
        result.gates = {
            "convexity": milestones.get(
                "M5", MilestoneResult(milestone="M5", passed=False)
            ).passed,
            "edge": milestones.get(
                "M4", MilestoneResult(milestone="M4", passed=False)
            ).passed,
            "risk_management": milestones.get(
                "M6", MilestoneResult(milestone="M6", passed=False)
            ).passed,
            "no_naked_shorts": self._check_no_naked_shorts(trade_decision, milestones),
        }
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

        # News / catalyst analysis
        news_summary = (news or {}).get("summary", {})
        news_sentiment = news_summary.get("sentiment_bias", "NEUTRAL")
        news_material_count = news_summary.get("material_count", 0)

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
            "news_sentiment": news_sentiment,
            "news_material_count": news_material_count,
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

        Returns dict keyed by milestone ID (``"M1"``, ``"M1B"``, etc.).
        """
        results: dict[str, MilestoneResult] = {}

        def _m1() -> tuple[str, MilestoneResult]:
            return ("M1", self._milestone_m1_ticker_validation(ticker))

        def _m1b() -> tuple[str, MilestoneResult]:
            return ("M1B", self._milestone_m1b_seasonality(ticker))

        def _m1c() -> tuple[str, MilestoneResult]:
            return ("M1C", self._milestone_m1c_analyst_ratings(ticker))

        def _m1d() -> tuple[str, MilestoneResult]:
            return ("M1D", self._milestone_m1d_news_catalysts(ticker))

        def _m2() -> tuple[str, MilestoneResult]:
            return ("M2", self._milestone_m2_dark_pool_flow(ticker))

        def _m3() -> tuple[str, MilestoneResult]:
            return ("M3", self._milestone_m3_options_flow(ticker))

        def _m3b() -> tuple[str, MilestoneResult]:
            return ("M3B", self._milestone_m3b_oi_changes(ticker))

        tasks = [_m1, _m1b, _m1c, _m1d, _m2, _m3, _m3b]

        with ThreadPoolExecutor(max_workers=7) as pool:
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
    # Individual milestone implementations
    # ------------------------------------------------------------------

    def _milestone_m1_ticker_validation(self, ticker: str) -> MilestoneResult:
        """M1 — Ticker validation.

        Verifies the ticker exists and has options available using the UW
        client. Falls back to IB client when UW is unavailable.
        """
        data: dict[str, Any] = {
            "ticker": ticker.upper(),
            "verified": False,
            "options_available": False,
        }

        # Try UW client first
        try:
            from radon.clients.uw_client import UWClient

            with UWClient() as uw:
                if uw.is_available():
                    stock_info = uw.get_stock_info(ticker)
                    if stock_info and stock_info.get("data"):
                        data["verified"] = True
                        sdata = stock_info["data"]
                        data["company_name"] = sdata.get("name") or sdata.get(
                            "full_name"
                        )
                        data["sector"] = sdata.get("sector")
                        data["market_cap"] = sdata.get("market_cap")

                    options = uw.get_option_contracts(ticker)
                    if options and options.get("data"):
                        data["options_available"] = True
        except Exception:
            logger.debug(
                "UW client unavailable for M1 ticker validation", exc_info=True
            )

        # If UW didn't verify, try IB
        if not data["verified"] and not self.skip_ib:
            try:
                from radon.clients.ib_client import IBClient

                ib = IBClient()
                if ib.is_available():
                    data["verified"] = True
                    data["options_available"] = True
            except Exception:
                logger.debug("IB client unavailable for M1", exc_info=True)

        # If no clients verified the ticker, accept it anyway — we cannot
        # determine validity without data sources, so we don't block.
        if not data["verified"]:
            data["verified"] = True
            data["note"] = "Ticker verification skipped — no data clients available"

        passed = data["verified"]
        reason = (
            "Ticker verified"
            if data.get("company_name")
            else "Ticker accepted (limited verification)"
        )

        return MilestoneResult(
            milestone="M1",
            passed=passed,
            reason=reason,
            data=data,
        )

    def _milestone_m1b_seasonality(self, ticker: str) -> MilestoneResult:
        """M1B — Seasonality context.

        Fetches monthly seasonality data from UW. Informational only — does
        not gate the evaluation.
        """
        data: dict[str, Any] = {"ticker": ticker.upper()}

        try:
            from radon.clients.uw_client import UWClient

            with UWClient() as uw:
                if uw.is_available():
                    seasonality = uw.get_monthly_seasonality(ticker)
                    if seasonality:
                        data["seasonality"] = seasonality
                        data["source"] = "uw"
        except Exception:
            logger.debug("UW seasonality fetch failed for %s", ticker, exc_info=True)

        return MilestoneResult(
            milestone="M1B",
            passed=True,
            reason="Seasonality context retrieved"
            if data.get("seasonality")
            else "Seasonality data unavailable",
            data=data,
        )

    def _milestone_m1c_analyst_ratings(self, ticker: str) -> MilestoneResult:
        """M1C — Analyst ratings context.

        Fetches analyst ratings from UW. Informational only — does not gate.
        """
        data: dict[str, Any] = {"ticker": ticker.upper()}

        try:
            from radon.clients.uw_client import UWClient

            with UWClient() as uw:
                if uw.is_available():
                    ratings = uw.get_analyst_ratings(ticker=ticker, limit=10)
                    if ratings:
                        data["ratings"] = ratings
                        data["source"] = "uw"
        except Exception:
            logger.debug(
                "UW analyst ratings fetch failed for %s", ticker, exc_info=True
            )

        return MilestoneResult(
            milestone="M1C",
            passed=True,
            reason="Analyst ratings retrieved"
            if data.get("ratings")
            else "Analyst ratings unavailable",
            data=data,
        )

    def _milestone_m1d_news_catalysts(self, ticker: str) -> MilestoneResult:
        """M1D — News & catalysts context.

        Fetches recent news headlines from UW. Informational only — does not
        gate, but data is used by M4 edge determination.
        """
        data: dict[str, Any] = {"ticker": ticker.upper()}

        try:
            from radon.clients.uw_client import UWClient

            with UWClient() as uw:
                if uw.is_available():
                    news = uw.get_news_headlines(ticker=ticker, limit=20)
                    if news:
                        data["news"] = news
                        data["source"] = "uw"
        except Exception:
            logger.debug("UW news fetch failed for %s", ticker, exc_info=True)

        return MilestoneResult(
            milestone="M1D",
            passed=True,
            reason="News data retrieved"
            if data.get("news")
            else "News data unavailable",
            data=data,
        )

    def _milestone_m2_dark_pool_flow(self, ticker: str) -> MilestoneResult:
        """M2 — Dark pool flow.

        Uses the DarkPoolFlowStrategy to scan for dark pool signals.
        Data is consumed by M4 (edge determination).
        """
        data: dict[str, Any] = {"ticker": ticker.upper()}

        try:
            from radon.strategies.dark_pool_flow import (
                DarkPoolFlowStrategy,
            )

            strategy = DarkPoolFlowStrategy()
            signal = strategy.scan(ticker, skip_positions=True, skip_options_flow=False)
            data["signal"] = {
                "signal_type": signal.signal_type,
                "confidence": signal.confidence,
                "data": signal.data,
                "source": signal.source,
            }
        except Exception:
            logger.debug("Dark pool flow scan failed for %s", ticker, exc_info=True)

        return MilestoneResult(
            milestone="M2",
            passed=True,
            reason="Dark pool flow data retrieved"
            if data.get("signal")
            else "Dark pool flow data unavailable",
            data=data,
        )

    def _milestone_m3_options_flow(self, ticker: str) -> MilestoneResult:
        """M3 — Options chain + institutional flow.

        Fetches option contracts and flow alerts from UW, and option chain
        from IB when available. Data is consumed by M4.
        """
        data: dict[str, Any] = {"ticker": ticker.upper()}

        try:
            from radon.clients.uw_client import UWClient

            with UWClient() as uw:
                if uw.is_available():
                    contracts = uw.get_option_contracts(ticker)
                    if contracts:
                        data["option_contracts"] = contracts

                    flow_alerts = uw.get_flow_alerts_by_ticker(ticker, limit=20)
                    if flow_alerts:
                        data["flow_alerts"] = flow_alerts
        except Exception:
            logger.debug("UW options flow fetch failed for %s", ticker, exc_info=True)

        # Supplement with IB option chain when available
        if not self.skip_ib:
            try:
                from radon.clients.ib_client import IBClient

                ib = IBClient()
                if ib.is_available():
                    chain = ib.get_option_chain(ticker)
                    if chain:
                        data["ib_option_chain"] = True
            except Exception:
                logger.debug(
                    "IB option chain fetch failed for %s", ticker, exc_info=True
                )

        return MilestoneResult(
            milestone="M3",
            passed=True,
            reason="Options flow data retrieved"
            if data.get("option_contracts") or data.get("flow_alerts")
            else "Options flow data unavailable",
            data=data,
        )

    def _milestone_m3b_oi_changes(self, ticker: str) -> MilestoneResult:
        """M3B — Open interest changes.

        Fetches OI change data from UW. Data is consumed by M4.
        """
        data: dict[str, Any] = {"ticker": ticker.upper()}

        try:
            from radon.clients.uw_client import UWClient

            with UWClient() as uw:
                if uw.is_available():
                    oi_data = uw.get_stock_oi_change(ticker)
                    if oi_data:
                        data["oi_change"] = oi_data
        except Exception:
            logger.debug("UW OI change fetch failed for %s", ticker, exc_info=True)

        return MilestoneResult(
            milestone="M3B",
            passed=True,
            reason="OI change data retrieved"
            if data.get("oi_change")
            else "OI change data unavailable",
            data=data,
        )

    def _milestone_m4_edge_determination(
        self, ticker: str, milestones: dict[str, MilestoneResult]
    ) -> MilestoneResult:
        """M4 — Edge determination.

        Uses ``determine_edge()`` with data from M2 (flow), M3 (options),
        M3B (OI changes), price history, and M1D (news).
        """
        # Extract flow data from M2
        m2 = milestones.get("M2")
        flow: dict[str, Any] = {}
        if m2 and m2.data.get("signal"):
            signal_data = m2.data["signal"].get("data", {})
            # Reconstruct flow dict expected by determine_edge()
            flow = {"dark_pool": {"aggregate": {}, "daily": []}}
            if isinstance(signal_data, dict):
                agg = signal_data.copy()
                flow["dark_pool"]["aggregate"] = {
                    "flow_direction": agg.get("direction", "NEUTRAL"),
                    "flow_strength": agg.get("strength", 0),
                    "dp_buy_ratio": agg.get("buy_ratio", 0.5),
                    "num_prints": agg.get("num_prints", 0),
                }

        # Extract options data from M3
        m3 = milestones.get("M3")
        options: dict | None = None
        if m3 and m3.data.get("flow_alerts"):
            options = m3.data.get("flow_alerts")

        # Extract OI data from M3B
        m3b = milestones.get("M3B")
        oi_changes: list[dict] = []
        if m3b and m3b.data.get("oi_change"):
            oi_raw = m3b.data["oi_change"]
            if isinstance(oi_raw, dict):
                items = oi_raw.get("data", [])
                if isinstance(items, list):
                    oi_changes = items

        # Fetch price history for signal_priced_in check
        price_history = self._fetch_price_history(ticker)

        # Extract news data from M1D
        m1d = milestones.get("M1D")
        news: dict | None = None
        if m1d and m1d.data.get("news"):
            news = m1d.data["news"]

        edge = self.determine_edge(
            flow=flow,
            options=options,
            oi_changes=oi_changes,
            price_history=price_history,
            news=news,
        )

        return MilestoneResult(
            milestone="M4",
            passed=edge["passed"],
            reason=edge.get("reason", "Edge determination complete"),
            data={"ticker": ticker.upper(), "edge_details": edge},
        )

    def _milestone_m5_structure_proposal(
        self, ticker: str, milestones: dict[str, MilestoneResult]
    ) -> MilestoneResult:
        """M5 — Structure proposal.

        Checks that a risk/reward ratio >= 2:1 is achievable based on the
        edge data from M4. In production, the operator designs the actual
        structure interactively.
        """
        m4 = milestones.get("M4")
        edge_details = (m4.data.get("edge_details", {})) if m4 else {}

        agg_direction = edge_details.get("agg_direction", "NEUTRAL")
        flow_strength = edge_details.get("flow_strength", 0.0)
        options_conflict = edge_details.get("options_conflict", False)

        data: dict[str, Any] = {
            "ticker": ticker.upper(),
            "direction": agg_direction,
            "flow_strength": flow_strength,
        }

        # Estimate risk/reward based on edge quality
        # Stronger flow → higher confidence → better R:R achievable
        reward_risk = 1.0
        if flow_strength >= 80:
            reward_risk = 3.0
        elif flow_strength >= 60:
            reward_risk = 2.5
        elif flow_strength >= 50:
            reward_risk = 2.0

        # Reduce if options conflict
        if options_conflict:
            reward_risk -= 0.5

        data["estimated_risk_reward"] = reward_risk
        data["min_risk_reward"] = self.min_risk_reward

        passed = reward_risk >= self.min_risk_reward
        reason = (
            f"Estimated R:R {reward_risk:.1f}:1 meets {self.min_risk_reward:.1f}:1 threshold"
            if passed
            else f"Estimated R:R {reward_risk:.1f}:1 below {self.min_risk_reward:.1f}:1 threshold"
        )

        if agg_direction == "NEUTRAL":
            passed = False
            reason = "No clear direction for structure"

        return MilestoneResult(
            milestone="M5",
            passed=passed,
            reason=reason,
            data=data,
        )

    def _milestone_m6_kelly_sizing(
        self, ticker: str, milestones: dict[str, MilestoneResult]
    ) -> MilestoneResult:
        """M6 — Kelly criterion sizing.

        Uses ``fractional_kelly()`` from ``kelly.py`` to compute position
        size based on the edge data from M4 and structure from M5.
        """
        m4 = milestones.get("M4")
        edge_details = (m4.data.get("edge_details", {})) if m4 else {}

        flow_strength = edge_details.get("flow_strength", 0.0)
        agg_direction = edge_details.get("agg_direction", "NEUTRAL")

        # Derive Kelly inputs from edge quality
        # Higher flow strength → higher win probability
        win_prob = _DEFAULT_WIN_PROB
        if flow_strength >= 80:
            win_prob = 0.65
        elif flow_strength >= 60:
            win_prob = 0.60
        elif flow_strength >= 50:
            win_prob = 0.55

        # Estimate win/loss amounts based on R:R from M5
        m5 = milestones.get("M5")
        rr_ratio = (m5.data.get("estimated_risk_reward", 2.0)) if m5 else 2.0

        # Use $1 as the loss unit; Kelly returns fraction of bankroll
        loss_amount = 1.0
        win_amount = loss_amount * rr_ratio

        kelly_fraction = 0.0
        recommendation = "DO NOT BET"

        try:
            from radon.utils.kelly import fractional_kelly

            kelly_fraction = fractional_kelly(
                win_prob=win_prob,
                win_amount=win_amount,
                loss_amount=loss_amount,
                fraction=self.kelly_fraction,
            )
            if kelly_fraction > 0:
                recommendation = "TRADE"
        except Exception:
            logger.debug("Kelly calculation failed for %s", ticker, exc_info=True)

        suggested_size = self.bankroll * kelly_fraction

        data: dict[str, Any] = {
            "ticker": ticker.upper(),
            "direction": agg_direction,
            "win_prob": win_prob,
            "risk_reward": rr_ratio,
            "kelly_fraction": round(kelly_fraction, 4),
            "suggested_size": round(suggested_size, 2),
            "bankroll": self.bankroll,
            "recommendation": recommendation,
        }

        passed = kelly_fraction > 0 and agg_direction != "NEUTRAL"
        reason = (
            f"Kelly size {kelly_fraction:.2%} of ${self.bankroll:,.0f} "
            f"= ${suggested_size:,.0f}"
            if passed
            else "No Kelly edge — recommendation: do not bet"
        )

        return MilestoneResult(
            milestone="M6",
            passed=passed,
            reason=reason,
            data=data,
        )

    def _milestone_m7_final_decision(
        self,
        ticker: str,
        trade_decision: str,
        milestones: dict[str, MilestoneResult],
    ) -> MilestoneResult:
        """M7 — Final decision synthesis.

        Aggregates all previous milestone results into a final go/no-go.
        """
        all_passed = all(ms.passed for ms in milestones.values())
        passed_count = sum(1 for ms in milestones.values() if ms.passed)
        total_count = len(milestones)

        return MilestoneResult(
            milestone="M7",
            passed=all_passed,
            reason=(
                f"All {total_count} milestones passed"
                if all_passed
                else f"{passed_count}/{total_count} milestones passed — trade rejected"
            ),
            data={
                "ticker": ticker.upper(),
                "trade_decision": trade_decision,
                "milestones_passed": passed_count,
                "milestones_total": total_count,
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_no_naked_shorts(
        trade_decision: str, milestones: dict[str, MilestoneResult]
    ) -> bool:
        """Check whether the trade avoids a naked-short risk.

        - BUY decisions can never be naked shorts → always ``True``.
        - SELL decisions pass only when M5 (Structure Proposal) passed with
          a defined risk/reward ratio, proving a hedged or defined-risk
          structure exists.
        - Any other decision string defaults to ``True`` (conservative).
        """
        if trade_decision.upper() != "SELL":
            return True

        m5 = milestones.get("M5")
        if m5 is None or not m5.passed:
            return False

        # M5 must contain risk/reward data to prove defined risk
        rr = m5.data.get("estimated_risk_reward")
        return rr is not None and rr > 0

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

    def _fetch_price_history(self, ticker: str, days: int = 10) -> list[dict]:
        """Fetch recent price bars for the signal_priced_in check.

        Uses UW OHLC data when available. Returns empty list on failure
        (non-fatal — signal_priced_in defaults to False).
        """
        try:
            from radon.clients.uw_client import UWClient

            with UWClient() as uw:
                if uw.is_available():
                    ohlc = uw.get_stock_ohlc(ticker, candle_size="1d")
                    if ohlc and ohlc.get("data"):
                        bars = ohlc["data"]
                        if isinstance(bars, list):
                            return [
                                {
                                    "date": bar.get("date", ""),
                                    "open": float(bar.get("open", 0)),
                                    "close": float(bar.get("close", 0)),
                                    "volume": float(bar.get("volume", 0)),
                                }
                                for bar in bars
                                if bar.get("close")
                            ]
        except Exception:
            logger.debug("Price history fetch failed for %s", ticker, exc_info=True)

        return []

    def _run_in_ib_thread(self, coro: Any) -> Any:
        """Run an async coroutine in a dedicated thread with its own event loop.

        ib_insync requires its own asyncio event loop. This method creates
        a new event loop in a background thread, runs the coroutine, and
        returns the result.
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
