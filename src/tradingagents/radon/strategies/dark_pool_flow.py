"""Dark pool flow scanner strategy.

Vendored and adapted from ``radon/scripts/scanner.py``.  Analyzes dark pool
flow data for a single ticker and produces a confidence-scored
:class:`StrategySignal`.

Required clients
----------------
- **uw** - Unusual Whales API (dark pool trades, options flow).
- **ib** - Interactive Brokers (open-position filtering, optional in practice).

Both clients degrade gracefully when their optional dependencies are missing.
"""

from __future__ import annotations

import logging
from typing import Any

from tradingagents.radon.strategies.base import StrategyRegistry, StrategySignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring thresholds (from the original scanner.py)
# ---------------------------------------------------------------------------

_STRONG_THRESHOLD: float = 60.0
_MODERATE_THRESHOLD: float = 40.0

_DIRECTION_SIGNAL: dict[str, str] = {
    "ACCUMULATION": "bullish",
    "DISTRIBUTION": "bearish",
}

_BIAS_TO_DIRECTION: dict[str, str] = {
    "BULLISH": "ACCUMULATION",
    "LEAN_BULLISH": "ACCUMULATION",
    "BEARISH": "DISTRIBUTION",
    "LEAN_BEARISH": "DISTRIBUTION",
}


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------


class DarkPoolFlowStrategy:
    """Scan a single ticker for dark pool flow signals.

    The core scoring algorithm is adapted from the Radon project's
    ``scanner.py``:

    1.  Fetch dark pool aggregate and daily breakdown from Unusual Whales.
    2.  Score based on flow strength, sustained direction, print count,
        and options-flow conflict.
    3.  Return a :class:`StrategySignal` with a normalised confidence
        value (0.0 - 1.0).
    """

    strategy_id: str = "dark-pool-flow"
    strategy_name: str = "Dark Pool Flow Scanner"
    required_clients: list[str] = ["ib", "uw"]

    # -- lazy client access --------------------------------------------------

    def __init__(self) -> None:
        self._ib_client: Any = None
        self._uw_client: Any = None

    def _get_ib_client(self) -> Any:
        """Lazily instantiate an :class:`IBClient` (no hard import)."""
        if self._ib_client is None:
            try:
                from tradingagents.radon.clients.ib_client import IBClient

                self._ib_client = IBClient()
            except Exception:
                logger.debug("IBClient unavailable", exc_info=True)
        return self._ib_client

    def _get_uw_client(self) -> Any:
        """Lazily instantiate a :class:`UWClient` (no hard import)."""
        if self._uw_client is None:
            try:
                from tradingagents.radon.clients.uw_client import UWClient

                self._uw_client = UWClient()
            except Exception:
                logger.debug("UWClient unavailable", exc_info=True)
        return self._uw_client

    # -- availability --------------------------------------------------------

    def is_available(self) -> bool:
        """Return ``True`` when the UW data source is reachable.

        IB is listed in :attr:`required_clients` for position filtering
        but is not a hard gate — scans proceed without it.
        """
        uw = self._get_uw_client()
        if uw is None:
            return False
        return uw.is_available()

    # -- data fetching -------------------------------------------------------

    def _fetch_darkpool_data(self, ticker: str) -> dict | None:
        uw = self._get_uw_client()
        if uw is None or not uw.is_available():
            return None
        try:
            return uw.get_darkpool_flow(ticker)
        except Exception:
            logger.warning(
                "Failed to fetch dark pool data for %s", ticker, exc_info=True
            )
            return None

    def _fetch_options_flow(self, ticker: str) -> dict | None:
        uw = self._get_uw_client()
        if uw is None or not uw.is_available():
            return None
        try:
            return uw.get_flow_alerts_by_ticker(ticker, limit=20)
        except Exception:
            logger.warning("Failed to fetch options flow for %s", ticker, exc_info=True)
            return None

    def _has_open_position(self, ticker: str) -> bool:
        ib = self._get_ib_client()
        if ib is None or not ib.is_available():
            return False
        try:
            positions = ib.get_positions()
        except Exception:
            return False
        if positions is None:
            return False
        return any(
            getattr(pos, "symbol", "").upper() == ticker.upper() for pos in positions
        )

    # -- core scoring (adapted from radon/scripts/scanner.py) ----------------

    @staticmethod
    def _analyze_signal(flow_data: dict) -> dict:
        """Score dark pool flow and return an analysis dict.

        The scoring rubric (preserved from the original scanner):

        - Base score equals aggregate ``flow_strength``.
        - +20 for 2+ consecutive days of same direction, +20 more for 4+.
        - +15 if the most recent day confirms aggregate direction and
          ``recent_strength > 50``.
        - -30 if the most recent day *contradicts* the aggregate direction.
        - -20 for fewer than 50 prints, -10 for fewer than 100.
        - -25 if options flow bias conflicts with dark pool direction.
        """
        if "error" in flow_data:
            return {"score": -1, "signal": "ERROR", "error": flow_data["error"]}

        dp = flow_data.get("dark_pool", {})
        agg = dp.get("aggregate", {})
        daily: list[dict] = dp.get("daily", [])

        direction: str = agg.get("flow_direction", "UNKNOWN")
        strength: float = float(agg.get("flow_strength", 0))
        buy_ratio = agg.get("dp_buy_ratio")
        num_prints: int = int(agg.get("num_prints", 0))

        # Sustained direction (3+ consecutive days with same direction)
        sustained = 0
        if daily:
            current_dir = daily[0].get("flow_direction")
            for day in daily[1:]:
                if day.get("flow_direction") == current_dir and current_dir in {
                    "ACCUMULATION",
                    "DISTRIBUTION",
                }:
                    sustained += 1
                else:
                    break

        recent_dir: str = (
            daily[0].get("flow_direction", "UNKNOWN") if daily else "UNKNOWN"
        )
        recent_strength: float = (
            float(daily[0].get("flow_strength", 0)) if daily else 0.0
        )

        score = strength

        if sustained >= 2:
            score += 20
        if sustained >= 4:
            score += 20

        if recent_dir == direction and recent_strength > 50:
            score += 15

        if recent_dir != direction and recent_dir in {"ACCUMULATION", "DISTRIBUTION"}:
            score -= 30

        if num_prints < 50:
            score -= 20
        elif num_prints < 100:
            score -= 10

        options_conflict = False
        options_flow: dict = flow_data.get("options_flow", {})
        if options_flow:
            combined_bias: str = options_flow.get("combined_bias", "NO_DATA")
            expected_dp = _BIAS_TO_DIRECTION.get(combined_bias)
            if expected_dp and expected_dp != direction:
                options_conflict = True
                score -= 25

        if score >= _STRONG_THRESHOLD and direction in {"ACCUMULATION", "DISTRIBUTION"}:
            signal = "STRONG"
        elif score >= _MODERATE_THRESHOLD and direction in {
            "ACCUMULATION",
            "DISTRIBUTION",
        }:
            signal = "MODERATE"
        elif direction in {"ACCUMULATION", "DISTRIBUTION"}:
            signal = "WEAK"
        else:
            signal = "NONE"

        return {
            "score": round(score, 1),
            "signal": signal,
            "direction": direction,
            "strength": strength,
            "buy_ratio": buy_ratio,
            "options_conflict": options_conflict,
            "num_prints": num_prints,
            "sustained_days": sustained + 1 if sustained > 0 else 0,
            "recent_direction": recent_dir,
            "recent_strength": recent_strength,
        }

    # -- confidence mapping --------------------------------------------------

    @staticmethod
    def _score_to_confidence(score: float) -> float:
        """Map raw score to a 0.0-1.0 confidence value.

        Scores typically range from roughly -50 to +130.  A linear
        mapping over [-20, 120] -> [0.0, 1.0] works well enough for
        the thresholds used in :meth:`_analyze_signal`.
        """
        clamped = max(-20.0, min(120.0, float(score)))
        return round((clamped + 20.0) / 140.0, 4)

    @staticmethod
    def _signal_to_type(signal: str, direction: str) -> str:
        """Convert internal signal/direction to a ``signal_type`` string."""
        if signal == "ERROR":
            return "error"
        if signal == "NONE" or direction == "UNKNOWN":
            return "neutral"
        return _DIRECTION_SIGNAL.get(direction, "neutral")

    # -- public entry point --------------------------------------------------

    def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
        """Run the dark pool flow scan for *ticker*.

        Args:
            ticker: Stock ticker symbol (e.g. ``"AAPL"``).
            **kwargs:
                skip_positions (bool): Skip tickers with open IB positions
                    (default ``True``).
                skip_options_flow (bool): Skip options-flow enrichment
                    (default ``True``).

        Returns:
            A :class:`StrategySignal` with the scan result.
        """
        uw = self._get_uw_client()
        if uw is None or not uw.is_available():
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={"error": "UW client unavailable"},
                source=self.strategy_id,
            )

        skip_positions = bool(kwargs.get("skip_positions", True))
        if skip_positions and self._has_open_position(ticker):
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={"skipped": True, "reason": "open_position"},
                source=self.strategy_id,
            )

        flow_data = self._fetch_darkpool_data(ticker)
        if flow_data is None:
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={"error": "failed to fetch dark pool data"},
                source=self.strategy_id,
            )

        skip_options = bool(kwargs.get("skip_options_flow", True))
        if not skip_options:
            options = self._fetch_options_flow(ticker)
            if options is not None:
                flow_data["options_flow"] = options

        analysis = self._analyze_signal(flow_data)

        if analysis.get("signal") == "ERROR":
            return StrategySignal(
                signal_type="error",
                confidence=0.0,
                data=analysis,
                source=self.strategy_id,
            )

        signal_type = self._signal_to_type(analysis["signal"], analysis["direction"])
        confidence = self._score_to_confidence(analysis["score"])

        return StrategySignal(
            signal_type=signal_type,
            confidence=confidence,
            data=analysis,
            source=self.strategy_id,
        )


# ---------------------------------------------------------------------------
# Module-level registration
# ---------------------------------------------------------------------------

registry = StrategyRegistry()
registry.register(DarkPoolFlowStrategy)
