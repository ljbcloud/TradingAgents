"""Crash Risk Index (CRI) strategy — detects CTA deleveraging cascades.

Scores four components to produce a composite crash risk score (0-100):

1. **VIX** — level and 5-day rate-of-change
2. **VVIX** — level and VVIX/VIX ratio (convexity demand)
3. **COR1M** — CBOE 1-month implied correlation level and 5-day change
4. **Momentum** — SPX distance from 100-day moving average

When the composite score is HIGH/CRITICAL and all three crash-trigger
conditions fire simultaneously (SPX < 100d MA, realized vol > 25%,
COR1M > 60), systematic CTA funds (~$400B AUM) are forced to
deleverage — creating predictable selling cascades over 3-5 days.

Data sources:
    - Interactive Brokers — historical daily bars for VIX, VVIX, COR1M, SPY
    - MenthorQ — institutional CTA positioning overlay (Playwright-based)

Adapted from the Radon project's ``scripts/cri_scan.py``.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from tradingagents.radon.clients.base import check_optional_dependency
from tradingagents.radon.strategies.base import StrategySignal

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════

ALL_TICKERS = ["VIX", "VVIX", "SPY", "COR1M"]

MA_WINDOW = 100  # SPX moving average window
VOL_WINDOW = 20  # Realized vol window (annualized)
MIN_BARS = MA_WINDOW + 20  # Minimum price history required

# CTA model parameters
CTA_VOL_TARGET = 10.0  # 10% target volatility
CTA_MAX_EXPOSURE = 200.0  # Max 200% exposure (leverage)
CTA_AUM_BN = 400.0  # Estimated CTA AUM in billions

# IB client IDs (dedicated pool for CRI to avoid conflicts)
CRI_IB_CLIENT_ID = 55

# Dependency availability flags — checked once at import time
HAS_IB: bool = check_optional_dependency("ib_insync")
HAS_PLAYWRIGHT: bool = check_optional_dependency("playwright")


# ══════════════════════════════════════════════════════════════════════
# Pure Computation Functions
# ══════════════════════════════════════════════════════════════════════


def compute_realized_vol(prices: np.ndarray, window: int = VOL_WINDOW) -> float:
    """Compute annualized realized volatility from the trailing window.

    Returns vol in percentage points (e.g. 25.0 for 25%).
    """
    if len(prices) < window + 1:
        return float("nan")
    log_returns = np.log(prices[-window:] / prices[-window - 1 : -1])
    return float(np.std(log_returns, ddof=1) * np.sqrt(252) * 100)


def score_vix_component(vix: float, vix_5d_roc: float) -> float:
    """Score VIX component (0-25).

    Args:
        vix: Current VIX level.
        vix_5d_roc: 5-day rate of change in percent.
    """
    if math.isnan(vix) or math.isnan(vix_5d_roc):
        return 0.0

    level_score = np.clip((vix - 15.0) / (40.0 - 15.0) * 15.0, 0.0, 15.0)
    roc_score = np.clip(max(vix_5d_roc, 0.0) / 60.0 * 10.0, 0.0, 10.0)

    return float(np.clip(level_score + roc_score, 0.0, 25.0))


def score_vvix_component(vvix: float, vvix_vix_ratio: float) -> float:
    """Score VVIX component (0-25).

    Args:
        vvix: Current VVIX level.
        vvix_vix_ratio: VVIX / VIX ratio.
    """
    if math.isnan(vvix) or math.isnan(vvix_vix_ratio):
        return 0.0

    level_score = np.clip((vvix - 90.0) / (140.0 - 90.0) * 17.0, 0.0, 17.0)
    ratio_score = np.clip((vvix_vix_ratio - 5.0) / (8.0 - 5.0) * 8.0, 0.0, 8.0)

    return float(np.clip(level_score + ratio_score, 0.0, 25.0))


def score_correlation_component(corr: float, corr_5d_change: float) -> float:
    """Score correlation component (0-25).

    Args:
        corr: Current COR1M level (percentage points).
        corr_5d_change: 5-session change in COR1M (percentage points).
    """
    if math.isnan(corr):
        return 0.0
    if math.isnan(corr_5d_change):
        corr_5d_change = 0.0

    level_score = np.clip((corr - 25.0) / (70.0 - 25.0) * 17.0, 0.0, 17.0)
    spike_score = np.clip(max(corr_5d_change, 0.0) / 20.0 * 8.0, 0.0, 8.0)

    return float(np.clip(level_score + spike_score, 0.0, 25.0))


def score_momentum_component(spx_distance_pct: float) -> float:
    """Score momentum component (0-25).

    Args:
        spx_distance_pct: SPX distance from 100d MA in percent (negative = below).
    """
    if math.isnan(spx_distance_pct):
        return 0.0
    if spx_distance_pct >= 0:
        return 0.0
    return float(np.clip(abs(spx_distance_pct) / 10.0 * 25.0, 0.0, 25.0))


def cri_level(score: float) -> str:
    """Classify CRI score into signal level."""
    if score < 25:
        return "LOW"
    if score < 50:
        return "ELEVATED"
    if score < 75:
        return "HIGH"
    return "CRITICAL"


def compute_cri(
    vix: float,
    vix_5d_roc: float,
    vvix: float,
    vvix_vix_ratio: float,
    corr: float,
    corr_5d_change: float,
    spx_distance_pct: float,
) -> dict[str, Any]:
    """Compute the CRI composite score (0-100) from four components."""
    vix_score = score_vix_component(vix, vix_5d_roc)
    vvix_score = score_vvix_component(vvix, vvix_vix_ratio)
    corr_score = score_correlation_component(corr, corr_5d_change)
    momentum_score = score_momentum_component(spx_distance_pct)

    total = vix_score + vvix_score + corr_score + momentum_score
    total = float(np.clip(total, 0.0, 100.0))

    return {
        "score": round(total, 1),
        "level": cri_level(total),
        "components": {
            "vix": round(vix_score, 1),
            "vvix": round(vvix_score, 1),
            "correlation": round(corr_score, 1),
            "momentum": round(momentum_score, 1),
        },
    }


def cta_exposure_model(
    realized_vol: float,
    vol_target: float = CTA_VOL_TARGET,
    aum_bn: float = CTA_AUM_BN,
) -> dict[str, Any]:
    """Model CTA exposure based on vol-targeting.

    Exposure = vol_target / realized_vol.
    Forced_reduction = max(0, 1 - Exposure).
    """
    if math.isnan(realized_vol) or realized_vol <= 0:
        return {
            "realized_vol": realized_vol if not math.isnan(realized_vol) else 0.0,
            "exposure_pct": CTA_MAX_EXPOSURE,
            "forced_reduction_pct": 0.0,
            "est_selling_bn": 0.0,
        }

    exposure = min(vol_target / realized_vol * 100.0, CTA_MAX_EXPOSURE)
    reduction = max(0.0, 1.0 - exposure / 100.0)
    est_selling = reduction * aum_bn

    return {
        "realized_vol": round(realized_vol, 2),
        "exposure_pct": round(exposure, 1),
        "forced_reduction_pct": round(reduction * 100.0, 1),
        "est_selling_bn": round(est_selling, 1),
    }


def crash_trigger(
    *,
    spx_below_ma: bool,
    realized_vol: float,
    cor1m: float,
) -> dict[str, Any]:
    """Evaluate the three crash-trigger conditions.

    All three must fire simultaneously:
      1. SPX < 100-day MA
      2. 20d realized vol > 25% annualized
      3. COR1M implied correlation > 60
    """
    vol_ok = (not math.isnan(realized_vol)) and realized_vol > 25.0
    corr_ok = (not math.isnan(cor1m)) and cor1m > 60.0
    triggered = spx_below_ma and vol_ok and corr_ok

    return {
        "triggered": triggered,
        "conditions": {
            "spx_below_100d_ma": spx_below_ma,
            "realized_vol_gt_25": vol_ok,
            "cor1m_gt_60": corr_ok,
        },
        "values": {
            "realized_vol": round(realized_vol, 2)
            if not math.isnan(realized_vol)
            else None,
            "cor1m": round(cor1m, 2) if not math.isnan(cor1m) else None,
        },
    }


def cor1m_level_and_change(
    cor1m_values: np.ndarray,
    current_override: float | None = None,
) -> tuple[float, float]:
    """Return current COR1M level and 5-session change.

    COR1M is already quoted as a percentage index (e.g. 31.1 = 31.1%),
    so no scaling is applied.
    """
    if cor1m_values is None or len(cor1m_values) == 0:
        return float("nan"), float("nan")
    if np.all(np.isnan(cor1m_values)):
        return float("nan"), float("nan")

    current = (
        current_override if current_override is not None else float(cor1m_values[-1])
    )
    if math.isnan(current):
        return float("nan"), float("nan")

    if len(cor1m_values) >= 6:
        prev = float(cor1m_values[-6])
        change = current - prev if not math.isnan(prev) else float("nan")
    else:
        change = float("nan")

    return current, change


def _cri_score_to_confidence(score: float) -> float:
    """Map CRI score (0-100) to a confidence value (0.0-1.0)."""
    return round(min(score / 100.0, 1.0), 3)


def _cri_level_to_signal_type(level: str, *, triggered: bool) -> str:
    """Map CRI level and crash-trigger state to signal type."""
    if triggered:
        return "strong_bearish"
    if level == "CRITICAL":
        return "strong_bearish"
    if level == "HIGH":
        return "bearish"
    if level == "ELEVATED":
        return "cautious"
    return "neutral"


# ══════════════════════════════════════════════════════════════════════
# Data Fetching Helpers
# ══════════════════════════════════════════════════════════════════════


def _fetch_ib_historical(
    ib_client: Any,
    tickers: list[str],
) -> dict[str, list[tuple[str, float]]]:
    """Fetch 1Y daily bars from IB for the given tickers.

    Uses the TradingAgents IBClient wrapper. Returns
    ``{ticker: [(date_str, close), ...]}`` for successful fetches.
    """
    if not HAS_IB or not ib_client.is_available():
        return {}

    try:
        from ib_insync import Index, Stock
    except ImportError:
        return {}

    results: dict[str, list[tuple[str, float]]] = {}

    for ticker in tickers:
        try:
            if ticker in {"VIX", "VVIX", "COR1M"}:
                contract = Index(ticker, "CBOE")
            else:
                contract = Stock(ticker, "SMART", "USD")

            qualified = ib_client.qualify_contracts(contract)
            if not qualified:
                logger.warning("CRI: IB could not qualify contract for %s", ticker)
                continue

            bars = ib_client.get_historical_data(
                qualified[0],
                duration="1 Y",
                bar_size="1 day",
                what_to_show="TRADES",
                use_rth=True,
            )
            if bars:
                results[ticker] = [(str(b.date), float(b.close)) for b in bars]
                logger.debug("CRI: IB %s — %d bars", ticker, len(bars))
            else:
                logger.warning("CRI: IB %s — no bars returned", ticker)
        except Exception as exc:
            logger.warning("CRI: IB %s failed — %s", ticker, exc)

    return results


def _fetch_ib_current_quote(ib_client: Any, ticker: str) -> float | None:
    """Fetch a current quote from IB for a single ticker.

    Returns the last price, mid-quote, or None on failure.
    """
    if not HAS_IB or not ib_client.is_available():
        return None

    try:
        from ib_insync import Index, Stock
    except ImportError:
        return None

    try:
        if ticker == "SPY":
            contract = Stock(ticker, "SMART", "USD")
        else:
            contract = Index(ticker, "CBOE")

        qualified = ib_client.qualify_contracts(contract)
        if not qualified:
            return None

        contract = qualified[0]

        for data_type in (1, 3, 4):
            try:
                ib_client.set_market_data_type(data_type)
                snapshot = ib_client.get_quote(contract, snapshot=True)
                if snapshot is None:
                    continue

                last = _valid_quote_value(getattr(snapshot, "last", None))
                if last is not None:
                    return last

                bid = _valid_quote_value(getattr(snapshot, "bid", None))
                ask = _valid_quote_value(getattr(snapshot, "ask", None))
                if bid is not None and ask is not None:
                    return (bid + ask) / 2.0
                if bid is not None:
                    return bid
                if ask is not None:
                    return ask
            except Exception:
                logger.debug("CRI: IB market data type %d failed", data_type)
                continue

        return None
    except Exception as exc:
        logger.warning("CRI: IB quote for %s failed — %s", ticker, exc)
        return None


def _valid_quote_value(value: Any) -> float | None:
    """Return a positive finite quote value, else None."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric) or numeric <= 0:
        return None
    return numeric


def _fetch_menthorq_cta(menthorq_client: Any, date: str) -> dict[str, Any] | None:
    """Fetch CTA positioning data from MenthorQ.

    Returns the CTA tables dict or None if unavailable.
    """
    if menthorq_client is None or not menthorq_client.is_available():
        return None

    try:
        tables = menthorq_client.get_cta(date)
        if tables:
            return {"tables": tables, "date": date}
    except Exception as exc:
        logger.warning("CRI: MenthorQ CTA unavailable — %s", exc)

    return None


def _align_price_data(
    raw: dict[str, list[tuple[str, float]]],
    tickers: list[str],
) -> tuple[dict[str, np.ndarray], list[str]]:
    """Align price data by common dates across all tickers.

    Returns (aligned_arrays, common_dates) or raises ValueError
    if insufficient data.
    """
    date_sets = [{d for d, _ in bars} for bars in raw.values()]
    common_dates = sorted(set.intersection(*date_sets))

    if len(common_dates) < MIN_BARS:
        msg = f"Only {len(common_dates)} common dates (need {MIN_BARS})"
        raise ValueError(msg)

    aligned: dict[str, np.ndarray] = {}
    for t in tickers:
        lookup = dict(raw[t])
        aligned[t] = np.array([lookup[d] for d in common_dates])

    return aligned, common_dates


def _current_session_date_et() -> str:
    """Return today's session date in Eastern Time as YYYY-MM-DD."""
    try:
        import zoneinfo

        return datetime.now(zoneinfo.ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    except Exception:
        now_et = datetime.now(timezone.utc) + timedelta(hours=-5)
        return now_et.strftime("%Y-%m-%d")


# ══════════════════════════════════════════════════════════════════════
# Core Analysis
# ══════════════════════════════════════════════════════════════════════


def run_cri_analysis(
    aligned: dict[str, np.ndarray],
    common_dates: list[str],
    current_quotes: dict[str, float] | None = None,
    menthorq_cta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run full CRI analysis on aligned price data.

    Args:
        aligned: ``{ticker: np.array of closes}`` for VIX, VVIX, SPY, COR1M.
        common_dates: Sorted list of date strings for the aligned data.
        current_quotes: Optional override quotes for live/COR1M data.
        menthorq_cta: Optional MenthorQ CTA positioning overlay.

    Returns:
        Dict with CRI score, components, CTA model, crash trigger, and history.
    """
    current_quotes = current_quotes or {}

    vix = aligned["VIX"]
    vvix = aligned["VVIX"]
    spy = aligned["SPY"]
    cor1m_values = aligned["COR1M"]

    vix_now = float(vix[-1])
    vvix_now = float(vvix[-1])
    spy_now = float(spy[-1])

    # VIX 5-day rate of change
    vix_5d_roc = (vix[-1] / vix[-6] - 1) * 100 if len(vix) >= 6 and vix[-6] > 0 else 0.0

    # VVIX / VIX ratio
    vvix_vix_ratio = vvix_now / vix_now if vix_now > 0 else float("nan")

    # SPX vs 100-day moving average
    if len(spy) >= MA_WINDOW:
        ma_100 = float(np.mean(spy[-MA_WINDOW:]))
        spx_distance_pct = (spy_now / ma_100 - 1) * 100
        spx_below_ma = spy_now < ma_100
    else:
        ma_100 = float("nan")
        spx_distance_pct = 0.0
        spx_below_ma = False

    # COR1M implied correlation
    cor1m_now, cor1m_5d_change = cor1m_level_and_change(
        cor1m_values,
        current_override=current_quotes.get("COR1M"),
    )

    # Realized vol (SPY, 20d annualized)
    realized_vol = compute_realized_vol(spy, VOL_WINDOW)

    # Composite CRI score
    cri = compute_cri(
        vix=vix_now,
        vix_5d_roc=float(vix_5d_roc),
        vvix=vvix_now,
        vvix_vix_ratio=float(vvix_vix_ratio),
        corr=cor1m_now,
        corr_5d_change=cor1m_5d_change,
        spx_distance_pct=float(spx_distance_pct),
    )

    # CTA exposure model
    cta = cta_exposure_model(realized_vol)

    # Crash trigger
    trigger = crash_trigger(
        spx_below_ma=spx_below_ma,
        realized_vol=realized_vol,
        cor1m=cor1m_now,
    )

    # Rolling 20-day history
    history: list[dict[str, Any]] = []
    n = len(vix)
    for i in range(max(0, n - 20), n):
        v = float(vix[i])
        vv = float(vvix[i])
        s = float(spy[i])

        if i >= MA_WINDOW - 1:
            day_ma = float(np.mean(spy[i - MA_WINDOW + 1 : i + 1]))
            day_dist = (s / day_ma - 1) * 100
        else:
            day_ma = float("nan")
            day_dist = 0.0

        if i >= 5 and vix[i - 5] > 0:
            day_vix_roc = (vix[i] / vix[i - 5] - 1) * 100
        else:
            day_vix_roc = 0.0

        if i >= VOL_WINDOW:
            day_rvol = compute_realized_vol(spy[: i + 1], VOL_WINDOW)
        else:
            day_rvol = float("nan")

        history.append({
            "date": common_dates[i],
            "vix": round(v, 2),
            "vvix": round(vv, 2),
            "spy": round(s, 2),
            "cor1m": round(float(cor1m_values[i]), 2),
            "realized_vol": round(day_rvol, 2) if not math.isnan(day_rvol) else None,
            "spx_vs_ma_pct": round(float(day_dist), 2),
            "vix_5d_roc": round(float(day_vix_roc), 1),
        })

    return {
        "date": common_dates[-1],
        "vix": round(vix_now, 2),
        "vvix": round(vvix_now, 2),
        "spy": round(spy_now, 2),
        "vix_5d_roc": round(float(vix_5d_roc), 1),
        "vvix_vix_ratio": round(float(vvix_vix_ratio), 2)
        if not math.isnan(vvix_vix_ratio)
        else None,
        "spx_100d_ma": round(ma_100, 2) if not math.isnan(ma_100) else None,
        "spx_distance_pct": round(float(spx_distance_pct), 2),
        "cor1m": round(cor1m_now, 2) if not math.isnan(cor1m_now) else None,
        "cor1m_5d_change": round(cor1m_5d_change, 2)
        if not math.isnan(cor1m_5d_change)
        else None,
        "realized_vol": round(realized_vol, 2)
        if not math.isnan(realized_vol)
        else None,
        "cri": cri,
        "cta": cta,
        "menthorq_cta": menthorq_cta,
        "crash_trigger": trigger,
        "history": history,
        "spy_closes": [round(float(p), 4) for p in spy[-(VOL_WINDOW * 2) :]],
    }


# ══════════════════════════════════════════════════════════════════════
# CRIStrategy
# ══════════════════════════════════════════════════════════════════════


class CRIStrategy:
    """Crash Risk Index strategy — detects systematic CTA deleveraging risk.

    Requires both IB (ib_insync) and MenthorQ (Playwright) clients.
    When MenthorQ is unavailable (Playwright not installed), the entire
    strategy reports as unavailable — this is the key degradation case.
    """

    strategy_id: str = "cri"
    strategy_name: str = "Crash Risk Index (CRI)"
    required_clients: list[str] = ["ib", "menthorq"]

    def __init__(self) -> None:
        self._ib_client: Any = None
        self._menthorq_client: Any = None

    def _get_ib_client(self) -> Any:
        """Lazily create and return an IBClient instance."""
        if self._ib_client is None and HAS_IB:
            try:
                from tradingagents.radon.clients.ib_client import IBClient

                self._ib_client = IBClient()
            except Exception as exc:
                logger.warning("CRI: Failed to create IBClient — %s", exc)
        return self._ib_client

    def _get_menthorq_client(self) -> Any:
        """Lazily create and return a MenthorQClient instance."""
        if self._menthorq_client is None and HAS_PLAYWRIGHT:
            try:
                from tradingagents.radon.clients.menthorq_client import MenthorQClient

                self._menthorq_client = MenthorQClient()
            except Exception as exc:
                logger.warning("CRI: Failed to create MenthorQClient — %s", exc)
        return self._menthorq_client

    def is_available(self) -> bool:
        """Return True when all required clients/dependencies are present.

        MenthorQ (Playwright) is the heaviest optional dependency. When it
        is not installed, this strategy is unavailable — the CTA positioning
        overlay is a critical component of the CRI analysis.
        """
        if not HAS_IB:
            return False
        if not HAS_PLAYWRIGHT:
            return False

        ib = self._get_ib_client()
        if ib is None:
            return False

        menthorq = self._get_menthorq_client()
        return menthorq is not None

    def scan(self, ticker: str = "SPY", **kwargs: object) -> StrategySignal:
        """Run the CRI scan and return a strategy signal.

        The CRI is a market-wide indicator so the *ticker* parameter is
        accepted for interface compatibility but is not used — the scan
        always analyses VIX, VVIX, COR1M, and SPY.

        Args:
            ticker: Ignored (CRI is market-wide). Defaults to "SPY".
            **kwargs: Optional overrides:
                - ``ib_client``: Pre-connected IBClient instance.
                - ``menthorq_client``: Pre-connected MenthorQClient instance.
                - ``aligned_data``: Pre-fetched aligned price data dict.
                - ``common_dates``: Pre-fetched common date list.

        Returns:
            StrategySignal with CRI score, crash-trigger state, and
            full analysis payload.
        """
        # Allow callers to inject pre-connected clients
        ib_client = kwargs.get("ib_client") or self._get_ib_client()
        menthorq_client = kwargs.get("menthorq_client") or self._get_menthorq_client()

        # Allow pre-fetched data injection (for testing / batch mode)
        aligned = kwargs.get("aligned_data")
        common_dates = kwargs.get("common_dates")

        if aligned is None or common_dates is None:
            # Fetch from IB
            if ib_client is None or not (
                hasattr(ib_client, "is_available") and ib_client.is_available()
            ):
                return StrategySignal(
                    signal_type="neutral",
                    confidence=0.0,
                    data={"error": "IB client unavailable — cannot fetch CRI data"},
                    source=self.strategy_id,
                )

            try:
                self._connect_ib(ib_client)
                raw = _fetch_ib_historical(ib_client, ALL_TICKERS)
            except Exception as exc:
                return StrategySignal(
                    signal_type="neutral",
                    confidence=0.0,
                    data={"error": f"IB data fetch failed: {exc}"},
                    source=self.strategy_id,
                )
            finally:
                self._disconnect_ib(ib_client)

            if len(raw) < len(ALL_TICKERS):
                missing = set(ALL_TICKERS) - set(raw.keys())
                return StrategySignal(
                    signal_type="neutral",
                    confidence=0.0,
                    data={"error": f"Missing data for: {missing}"},
                    source=self.strategy_id,
                )

            try:
                aligned_typed: dict[str, np.ndarray] = {}
                common_dates_typed: list[str] = []
                aligned_typed, common_dates_typed = _align_price_data(raw, ALL_TICKERS)
                aligned = aligned_typed
                common_dates = common_dates_typed
            except ValueError as exc:
                return StrategySignal(
                    signal_type="neutral",
                    confidence=0.0,
                    data={"error": str(exc)},
                    source=self.strategy_id,
                )

        if not isinstance(aligned, dict) or not isinstance(common_dates, list):
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={"error": "Internal error: aligned data has wrong type"},
                source=self.strategy_id,
            )

        # Fetch MenthorQ CTA overlay (optional enhancement)
        session_date = _current_session_date_et()
        menthorq_cta: dict[str, Any] | None = None
        if menthorq_client is not None and hasattr(menthorq_client, "is_available"):
            menthorq_cta = _fetch_menthorq_cta(menthorq_client, session_date)

        # Run analysis
        result = run_cri_analysis(
            aligned=aligned,
            common_dates=common_dates,
            current_quotes={},
            menthorq_cta=menthorq_cta,
        )

        # Build signal
        cri_data = result["cri"]
        trigger_data = result["crash_trigger"]
        score = cri_data["score"]
        level = cri_data["level"]
        triggered = trigger_data["triggered"]

        return StrategySignal(
            signal_type=_cri_level_to_signal_type(level, triggered=triggered),
            confidence=_cri_score_to_confidence(score),
            data=result,
            source=self.strategy_id,
        )

    @staticmethod
    def _connect_ib(ib_client: Any) -> None:
        """Connect IB client with retry, handling connection errors."""
        if hasattr(ib_client, "connect"):
            try:
                ib_client.connect(
                    client_id=CRI_IB_CLIENT_ID,
                    timeout=8,
                    max_retries=1,
                )
            except Exception as exc:
                logger.warning("CRI: IB connection failed — %s", exc)

    @staticmethod
    def _disconnect_ib(ib_client: Any) -> None:
        """Disconnect IB client safely."""
        if hasattr(ib_client, "disconnect"):
            with __import__("contextlib").suppress(Exception):
                ib_client.disconnect()


# ══════════════════════════════════════════════════════════════════════
# Registry Registration
# ══════════════════════════════════════════════════════════════════════


def register(registry: Any) -> None:
    """Register this strategy with a StrategyRegistry instance."""
    registry.register(CRIStrategy)
