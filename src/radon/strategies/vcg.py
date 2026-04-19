"""Volatility-Credit Gap (VCG) scanner strategy.

Detects divergence between the volatility complex (VIX/VVIX) and cash
credit (HYG/JNK/LQD) using a rolling 21-day OLS model.  When the
standardised residual exceeds +2 sigma and the High-Divergence-Risk
conditions hold, the scanner fires a Risk-Off signal.

Mathematical specification: docs/VCG_institutional_research_note.md
Strategy spec:              docs/strategies.md (Strategy 5)

Data source: Interactive Brokers (IB).  The IB client is imported lazily
so the module can be loaded without ib_insync installed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np

from radon.strategies.base import StrategyRegistry, StrategySignal

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# ── constants ─────────────────────────────────────────────────────
OLS_WINDOW = 21
Z_WINDOW = 63
MIN_BARS = OLS_WINDOW + Z_WINDOW + 10

VIX_PANIC_LOW = 40.0
VIX_PANIC_HIGH = 48.0

VIX_FLOOR = 28.0
VIX_EDR = 25.0
VCG_TRIGGER = 2.0
VCG_RO_TRIGGER = 2.5
BOUNCE_TRIGGER = -3.5

VVIX_EXTREME = 120.0
VVIX_ELEVATED = 100.0

# ── VCG computation helpers ───────────────────────────────────────


def _log_returns(prices: NDArray[np.floating]) -> NDArray[np.floating]:
    """Compute log returns: ln(P_t / P_{t-1})."""
    return np.log(prices[1:] / prices[:-1])


def _rolling_ols(
    y: NDArray[np.floating],
    x_matrix: NDArray[np.floating],
    window: int = OLS_WINDOW,
) -> tuple[
    NDArray[np.floating],
    NDArray[np.floating],
    NDArray[np.floating],
    NDArray[np.floating],
]:
    """Rolling OLS: y = alpha + beta1*x_matrix[:,0] + beta2*x_matrix[:,1] + eps.

    Returns (alphas, beta1s, beta2s, residuals) arrays.
    """
    n = len(y)
    alphas = np.full(n, np.nan)
    beta1s = np.full(n, np.nan)
    beta2s = np.full(n, np.nan)
    residuals = np.full(n, np.nan)

    for t in range(window - 1, n):
        start = t - window + 1
        y_w = y[start : t + 1]
        x_w = x_matrix[start : t + 1]
        design = np.column_stack([np.ones(window), x_w])
        try:
            coeff, _, _, _ = np.linalg.lstsq(design, y_w, rcond=None)
        except np.linalg.LinAlgError:
            continue
        alphas[t] = coeff[0]
        beta1s[t] = coeff[1]
        beta2s[t] = coeff[2]
        y_hat = design @ coeff
        residuals[t] = y_w[-1] - y_hat[-1]

    return alphas, beta1s, beta2s, residuals


def _standardise_residuals(
    residuals: NDArray[np.floating],
    window: int = Z_WINDOW,
) -> NDArray[np.floating]:
    """Compute z-scores of residuals over a trailing window."""
    n = len(residuals)
    z = np.full(n, np.nan)
    for t in range(window - 1, n):
        start = t - window + 1
        chunk = residuals[start : t + 1]
        valid = chunk[~np.isnan(chunk)]
        if len(valid) < 10:
            continue
        mu = np.mean(valid)
        sigma = np.std(valid, ddof=1)
        if sigma < 1e-12:
            continue
        z[t] = (residuals[t] - mu) / sigma
    return z


def _compute_vcg(
    vix_prices: NDArray[np.floating],
    vvix_prices: NDArray[np.floating],
    credit_prices: NDArray[np.floating],
) -> dict[str, NDArray[np.floating]]:
    """Compute the full VCG model.

    Returns dict of arrays (all length = len(prices) - 1):
        vcg, vcg_div, residuals, alpha, beta1, beta2,
        vix_ret, vvix_ret, credit_ret, vix_levels,
        vvix_levels, credit_levels, pi
    """
    vix_ret = _log_returns(vix_prices)
    vvix_ret = _log_returns(vvix_prices)
    credit_ret = _log_returns(credit_prices)

    predictors = np.column_stack([vvix_ret, vix_ret])
    alphas, beta1s, beta2s, residuals = _rolling_ols(credit_ret, predictors, OLS_WINDOW)
    vcg = _standardise_residuals(residuals, Z_WINDOW)

    vix_levels = vix_prices[1:]
    pi = np.clip(
        (vix_levels - VIX_PANIC_LOW) / (VIX_PANIC_HIGH - VIX_PANIC_LOW),
        0,
        1,
    )
    vcg_div = (1 - pi) * vcg

    return {
        "vcg": vcg,
        "vcg_div": vcg_div,
        "residuals": residuals,
        "alpha": alphas,
        "beta1": beta1s,
        "beta2": beta2s,
        "vix_ret": vix_ret,
        "vvix_ret": vvix_ret,
        "credit_ret": credit_ret,
        "vix_levels": vix_levels,
        "vvix_levels": vvix_prices[1:],
        "credit_levels": credit_prices[1:],
        "pi": pi,
    }


def _evaluate_signal(
    model: dict[str, NDArray[np.floating]],
    vix_floor: float = VIX_FLOOR,
    vcg_trigger: float = VCG_RO_TRIGGER,
) -> dict[str, Any]:
    """Evaluate the VCG signal for the most recent bar."""
    idx = -1
    vcg_val = model["vcg"][idx]
    vcg_div_val = model["vcg_div"][idx]
    beta1 = model["beta1"][idx]
    beta2 = model["beta2"][idx]
    alpha = model["alpha"][idx]
    vix = model["vix_levels"][idx]
    vvix = model["vvix_levels"][idx]
    credit = model["credit_levels"][idx]
    residual = model["residuals"][idx]
    pi_val = model["pi"][idx]

    sign_ok = (beta1 <= 0) and (beta2 <= 0)

    if vvix > VVIX_EXTREME:
        vvix_severity = "extreme"
    elif vvix >= VVIX_ELEVATED:
        vvix_severity = "elevated"
    else:
        vvix_severity = "moderate"

    ro = bool(
        not np.isnan(vcg_val) and vix > vix_floor and vcg_val > vcg_trigger and sign_ok
    )
    edr = bool(
        not np.isnan(vcg_val) and vix > VIX_EDR and vcg_val > VCG_TRIGGER and sign_ok
    )

    tier: int | None = None
    if ro:
        tier = 1 if vix > 30 else 2
    elif edr and not np.isnan(vcg_val) and vcg_val > VCG_TRIGGER:
        tier = 3

    bounce = bool(not np.isnan(vcg_val) and vcg_val < BOUNCE_TRIGGER)

    vvix_component = beta1 * model["vvix_ret"][idx] if not np.isnan(beta1) else 0.0
    vix_component = beta2 * model["vix_ret"][idx] if not np.isnan(beta2) else 0.0
    total_component = abs(vvix_component) + abs(vix_component)
    if total_component < 1e-12:
        total_component = 1.0
    vvix_pct = abs(vvix_component) / total_component * 100
    vix_pct = abs(vix_component) / total_component * 100

    if pi_val >= 1.0:
        regime = "PANIC"
    elif pi_val > 0:
        regime = "TRANSITION"
    else:
        regime = "DIVERGENCE"

    if np.isnan(vcg_val):
        interpretation = "INSUFFICIENT_DATA"
    elif not sign_ok:
        interpretation = "SUPPRESSED"
    elif pi_val >= 1.0:
        interpretation = "PANIC"
    elif ro:
        interpretation = "RISK_OFF"
    elif edr:
        interpretation = "EDR"
    elif bounce:
        interpretation = "BOUNCE"
    elif vcg_val > VCG_TRIGGER:
        interpretation = "WATCH"
    else:
        interpretation = "NORMAL"

    return {
        "vcg": round(float(vcg_val), 4) if not np.isnan(vcg_val) else None,
        "vcg_adj": round(float(vcg_div_val), 4) if not np.isnan(vcg_div_val) else None,
        "residual": round(float(residual), 6) if not np.isnan(residual) else None,
        "beta1_vvix": round(float(beta1), 6) if not np.isnan(beta1) else None,
        "beta2_vix": round(float(beta2), 6) if not np.isnan(beta2) else None,
        "alpha": round(float(alpha), 6) if not np.isnan(alpha) else None,
        "vix": round(float(vix), 2),
        "vvix": round(float(vvix), 2),
        "credit_price": round(float(credit), 2),
        "ro": ro,
        "edr": edr,
        "tier": tier,
        "bounce": bounce,
        "vvix_severity": vvix_severity,
        "sign_ok": sign_ok,
        "pi_panic": round(float(pi_val), 4),
        "regime": regime,
        "interpretation": interpretation,
        "attribution": {
            "vvix_pct": round(vvix_pct, 1),
            "vix_pct": round(vix_pct, 1),
        },
    }


# ── confidence / signal-type mapping ──────────────────────────────

_CONFIDENCE_MAP: dict[str, float] = {
    "RISK_OFF": 0.90,
    "PANIC": 0.85,
    "EDR": 0.60,
    "BOUNCE": 0.55,
    "WATCH": 0.40,
    "SUPPRESSED": 0.0,
    "NORMAL": 0.10,
    "INSUFFICIENT_DATA": 0.0,
}

_SIGNAL_TYPE_MAP: dict[str, str] = {
    "RISK_OFF": "bearish",
    "PANIC": "bearish",
    "EDR": "bearish",
    "BOUNCE": "bullish",
    "WATCH": "neutral",
    "SUPPRESSED": "neutral",
    "NORMAL": "neutral",
    "INSUFFICIENT_DATA": "neutral",
}


# ── IB data fetching (lazy) ───────────────────────────────────────


def _fetch_ib_bars(
    tickers: list[str],
) -> dict[str, list[tuple[str, float]]]:
    """Fetch 1Y daily bars from IB for the given tickers.

    Returns ``{ticker: [(date_str, close), ...]}`` for successful
    fetches.  Returns an empty dict when IB is unavailable.
    """
    try:
        from clients.ib_client import IBClient  # type: ignore[import-untyped]
        from ib_insync import Index, Stock  # type: ignore[import-untyped]
    except ImportError:
        return {}

    results: dict[str, list[tuple[str, float]]] = {}
    client = IBClient()
    try:
        client.connect(client_name="vcg_scanner", timeout=8, max_retries=1)
    except Exception:
        return {}

    try:
        for ticker in tickers:
            if ticker in {"VIX", "VVIX"}:
                contract = Index(ticker, "CBOE")
            else:
                contract = Stock(ticker, "SMART", "USD")
            try:
                client.qualify_contract(contract)
                bars = client.get_historical_data(
                    contract,
                    duration="1 Y",
                    bar_size="1 day",
                    what_to_show="TRADES",
                    use_rth=True,
                )
                if bars:
                    results[ticker] = [(str(b.date), float(b.close)) for b in bars]
            except Exception as exc:
                logger.debug("IB fetch failed for %s: %s", ticker, exc)
    finally:
        client.disconnect()

    return results


def _align_prices(
    raw: dict[str, list[tuple[str, float]]],
    tickers: list[str],
) -> dict[str, NDArray[np.floating]] | None:
    """Align price series by common dates.

    Returns ``{ticker: np.ndarray of closes}`` or ``None`` when data is
    insufficient (missing tickers or too few common dates).
    """
    if len(raw) < len(tickers):
        return None

    date_sets = [{d for d, _ in raw[t]} for t in tickers]
    common_dates = sorted(set.intersection(*date_sets))
    if len(common_dates) < MIN_BARS:
        return None

    aligned: dict[str, NDArray[np.floating]] = {}
    for t in tickers:
        lookup = dict(raw[t])
        aligned[t] = np.array([lookup[d] for d in common_dates], dtype=np.float64)

    return aligned


# ── strategy class ────────────────────────────────────────────────


class VCGStrategy:
    """Volatility-Credit Gap scanner strategy.

    Detects divergence between the volatility complex (VIX/VVIX) and
    cash credit (HYG/JNK/LQD) using a rolling 21-day OLS model.
    """

    strategy_id: str = "vcg"
    strategy_name: str = "Volatility-Credit Gap"
    required_clients: list[str] = ["ib"]

    def is_available(self) -> bool:
        """Return True when IB client and ib_insync are importable."""
        try:
            from clients.ib_client import (
                IBClient,  # type: ignore[import-untyped]  # noqa: F401
            )
            from ib_insync import (  # type: ignore[import-untyped]  # noqa: F401
                Index,
                Stock,
            )
        except ImportError:
            return False
        return True

    def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
        """Run the VCG scan.

        Args:
            ticker: Credit proxy ticker (e.g. ``"HYG"``, ``"JNK"``).
            **kwargs:
                vix_floor (float): VIX floor for RO trigger.
                    Defaults to :data:`VIX_FLOOR`.
                vcg_trigger (float): VCG z-score threshold for RO.
                    Defaults to :data:`VCG_RO_TRIGGER`.

        Returns:
            A :class:`StrategySignal` with the scan result.  When data
            cannot be fetched (IB unavailable), returns a neutral signal
            with confidence 0.0.
        """
        credit_proxy = ticker.upper()
        vix_floor = float(kwargs.get("vix_floor", VIX_FLOOR))
        vcg_trigger = float(kwargs.get("vcg_trigger", VCG_RO_TRIGGER))

        tickers = ["VIX", "VVIX", credit_proxy]
        raw = _fetch_ib_bars(tickers)
        aligned = _align_prices(raw, tickers)

        if aligned is None:
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={
                    "interpretation": "INSUFFICIENT_DATA",
                    "credit_proxy": credit_proxy,
                },
                source=self.strategy_id,
            )

        model = _compute_vcg(
            aligned["VIX"],
            aligned["VVIX"],
            aligned[credit_proxy],
        )
        signal = _evaluate_signal(model, vix_floor=vix_floor, vcg_trigger=vcg_trigger)

        interpretation = signal["interpretation"]
        confidence = _CONFIDENCE_MAP.get(interpretation, 0.0)
        signal_type = _SIGNAL_TYPE_MAP.get(interpretation, "neutral")

        if interpretation == "RISK_OFF" and signal["tier"] == 1:
            confidence = 0.95
        elif interpretation == "RISK_OFF" and signal["tier"] == 2:
            confidence = 0.80

        signal["credit_proxy"] = credit_proxy

        return StrategySignal(
            signal_type=signal_type,
            confidence=confidence,
            data=signal,
            source=self.strategy_id,
        )


# ── registration ──────────────────────────────────────────────────

registry = StrategyRegistry()
registry.register(VCGStrategy)
