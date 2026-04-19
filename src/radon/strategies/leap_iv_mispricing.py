"""LEAP IV mispricing strategy — detects underpriced volatility in long-dated options.

Core thesis: when recent realized volatility (HV20/HV60) materially exceeds LEAP
implied volatility, the market is mispricing forward volatility.  Buying long-dated
calls in this regime captures vega alpha even if the underlying trades flat.

Adapted from the standalone ``leap_iv_scanner.py`` script in the Radon project.
All CLI / reporting / argparse code has been stripped; only the analytical core
remains, wrapped in the :class:`LeapIVStrategy` class that satisfies the
:class:`~radon.strategies.base.BaseStrategy` protocol.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from radon.strategies.base import StrategySignal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_YEARS: list[int] = [2027, 2028]
_TARGET_DELTAS: list[float] = [0.50, 0.30, 0.20, 0.10]
_MIN_IV_GAP: float = 15.0
_HV_PERIODS: tuple[int, ...] = (20, 60, 252)
_HISTORICAL_DAYS: int = 800


# ---------------------------------------------------------------------------
# Internal data classes (not exported — data lives in StrategySignal.data)
# ---------------------------------------------------------------------------


@dataclass
class _VolatilityData:
    ticker: str
    current_price: float
    hv_20: float
    hv_60: float
    hv_252: float
    hv_756: float | None = None
    avg_hv: float = 0.0

    def __post_init__(self) -> None:
        hvs = [self.hv_20, self.hv_60, self.hv_252]
        if self.hv_756 is not None:
            hvs.append(self.hv_756)
        self.avg_hv = sum(hvs) / len(hvs)


@dataclass
class _OptionAnalysis:
    expiry: str
    strike: float
    right: str
    delta: float
    iv: float
    bid: float
    ask: float
    mid: float
    vega: float
    theta: float
    hv_20_gap: float = 0.0
    hv_60_gap: float = 0.0
    hv_avg_gap: float = 0.0
    is_mispriced: bool = False
    mispricing_score: float = 0.0


# ---------------------------------------------------------------------------
# Pure helpers — no IB dependency
# ---------------------------------------------------------------------------


def _calculate_historical_volatility(prices: list[float], period: int) -> float:
    """Return annualised historical volatility (log-returns, sqrt-252)."""
    if len(prices) < period + 1:
        return 0.0

    recent = prices[-(period + 1) :]
    returns = [
        math.log(recent[i] / recent[i - 1])
        for i in range(1, len(recent))
        if recent[i - 1] > 0
    ]

    if len(returns) < 2:
        return 0.0

    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
    daily_vol = math.sqrt(variance)
    return round(daily_vol * math.sqrt(252) * 100, 2)


def _find_strikes_by_delta(
    options: list[dict[str, Any]],
    target_deltas: list[float],
) -> dict[float, dict[str, Any]]:
    """Map each target delta to the option closest to it (within 0.15 tolerance)."""
    result: dict[float, dict[str, Any]] = {}
    for target in target_deltas:
        best: dict[str, Any] | None = None
        best_diff = float("inf")
        for opt in options:
            delta = opt.get("delta")
            if delta is None:
                continue
            diff = abs(abs(delta) - target)
            if diff < best_diff:
                best_diff = diff
                best = opt
        if best is not None and best_diff < 0.15:
            result[target] = best
    return result


def _analyze_mispricing(
    option: dict[str, Any],
    vol: _VolatilityData,
    min_gap: float,
) -> _OptionAnalysis:
    """Score a single option's IV-vs-HV gap."""
    iv = option["iv"]
    hv_20_gap = vol.hv_20 - iv
    hv_60_gap = vol.hv_60 - iv
    hv_avg_gap = vol.avg_hv - iv

    is_mispriced = (hv_20_gap >= min_gap or hv_60_gap >= min_gap) and hv_avg_gap > 0

    # Weight recent vol more heavily
    score = hv_20_gap * 0.4 + hv_60_gap * 0.35 + hv_avg_gap * 0.25
    # Boost for high vega (more leverage on IV expansion)
    vega_boost = min(option.get("vega", 0) / 0.30, 1.5)
    score *= vega_boost

    return _OptionAnalysis(
        expiry=option.get("expiry", ""),
        strike=option.get("strike", 0.0),
        right="C",
        delta=option.get("delta", 0.0),
        iv=iv,
        bid=option.get("bid", 0),
        ask=option.get("ask", 0),
        mid=option.get("mid", 0),
        vega=option.get("vega", 0),
        theta=option.get("theta", 0),
        hv_20_gap=round(hv_20_gap, 2),
        hv_60_gap=round(hv_60_gap, 2),
        hv_avg_gap=round(hv_avg_gap, 2),
        is_mispriced=is_mispriced,
        mispricing_score=round(score, 2),
    )


# ---------------------------------------------------------------------------
# IB-dependent helpers (lazy imports)
# ---------------------------------------------------------------------------


def _fetch_historical_data(
    client: Any,
    ticker: str,
    days: int = _HISTORICAL_DAYS,
) -> list[float]:
    """Fetch historical daily closes via *client* for HV calculation."""
    from ib_insync import Stock

    contract = Stock(ticker, "SMART", "USD")
    client.qualify_contracts(contract)

    if days > 365:
        years = max(1, days // 252)
        duration_str = f"{years} Y"
    else:
        duration_str = f"{days} D"

    bars = client.get_historical_data(
        contract,
        duration=duration_str,
        bar_size="1 day",
        what_to_show="TRADES",
        use_rth=True,
    )
    if not bars:
        return []
    return [bar.close for bar in bars]


def _fetch_volatility_data(client: Any, ticker: str) -> _VolatilityData | None:
    """Build a :class:`_VolatilityData` snapshot for *ticker*."""
    prices = _fetch_historical_data(client, ticker)
    if len(prices) < 60:
        return None

    current_price = prices[-1]
    hv_20 = _calculate_historical_volatility(prices, 20)
    hv_60 = _calculate_historical_volatility(prices, 60)
    hv_252 = (
        _calculate_historical_volatility(prices, 252) if len(prices) >= 253 else hv_60
    )
    hv_756 = (
        _calculate_historical_volatility(prices, 756) if len(prices) >= 757 else None
    )

    return _VolatilityData(
        ticker=ticker,
        current_price=current_price,
        hv_20=hv_20,
        hv_60=hv_60,
        hv_252=hv_252,
        hv_756=hv_756,
    )


def _get_leap_expirations(
    client: Any,
    ticker: str,
    target_years: list[int],
) -> list[str]:
    """Return sorted, deduplicated LEAP expirations in *target_years*."""
    from ib_insync import Stock

    contract = Stock(ticker, "SMART", "USD")
    client.qualify_contracts(contract)

    chains = client.ib.reqSecDefOptParams(ticker, "", "STK", contract.conId)
    if not chains:
        return []

    expirations: set[str] = set()
    for chain in chains:
        if chain.exchange == "SMART":
            for exp in chain.expirations:
                if int(exp[:4]) in target_years:
                    expirations.add(exp)
    return sorted(expirations)


def _fetch_option_chain(
    client: Any,
    ticker: str,
    expiry: str,
    current_price: float,
) -> list[dict[str, Any]]:
    """Fetch call options for *expiry* with model greeks."""
    from ib_insync import Option, util

    min_strike = current_price * 0.70
    max_strike = current_price * 1.50

    if current_price > 100:
        interval = 5.0
    elif current_price > 50:
        interval = 2.5
    else:
        interval = 1.0

    strikes: list[float] = []
    strike = math.floor(min_strike / interval) * interval
    while strike <= max_strike:
        strikes.append(strike)
        strike += interval

    contracts = [Option(ticker, expiry, s, "C", "SMART") for s in strikes]

    qualified: list[Any] = []
    try:
        client.qualify_contracts(*contracts)
        qualified = [c for c in contracts if getattr(c, "conId", None)]
    except Exception:
        qualified = [c for c in contracts if getattr(c, "conId", None)]

    if not qualified:
        return []

    tickers: list[tuple[Any, Any]] = []
    for contract in qualified:
        ticker_data = client.get_quote(contract, generic_ticks="106")
        tickers.append((contract, ticker_data))

    client.sleep(3)

    options: list[dict[str, Any]] = []
    for contract, ticker_data in tickers:
        bid = (
            ticker_data.bid
            if (ticker_data.bid and not util.isNan(ticker_data.bid))
            else 0
        )
        ask = (
            ticker_data.ask
            if (ticker_data.ask and not util.isNan(ticker_data.ask))
            else 0
        )

        greeks = ticker_data.modelGreeks
        if greeks:
            iv = greeks.impliedVol * 100 if greeks.impliedVol else 0
            delta = greeks.delta or 0
            vega = greeks.vega or 0
            theta = greeks.theta or 0
        else:
            iv = delta = vega = theta = 0

        if iv == 0 or delta == 0:
            client.cancel_market_data(contract)
            continue

        options.append({
            "strike": contract.strike,
            "expiry": contract.lastTradeDateOrContractMonth,
            "bid": bid,
            "ask": ask,
            "mid": (bid + ask) / 2 if bid and ask else 0,
            "iv": round(iv, 2),
            "delta": round(delta, 4),
            "vega": round(vega, 4),
            "theta": round(theta, 4),
        })
        client.cancel_market_data(contract)

    return options


# ---------------------------------------------------------------------------
# Strategy implementation
# ---------------------------------------------------------------------------


class LeapIVStrategy:
    """Detect LEAP IV mispricing by comparing realised vol to implied vol.

    Scans long-dated call options for a single ticker, computes multi-timeframe
    historical volatility, and flags contracts where HV materially exceeds LEAP
    IV — a signal that forward volatility may be underpriced.
    """

    strategy_id: str = "leap-iv-mispricing"
    strategy_name: str = "LEAP IV Mispricing Scanner"
    required_clients: list[str] = ["ib"]

    # -- availability -------------------------------------------------------

    def is_available(self) -> bool:
        """Return ``True`` when IBClient is importable and connected.

        The check is lightweight: it only verifies that the ``radon``
        IB client module can be imported.  Actual connection status is checked
        at scan time so that the strategy can be instantiated eagerly (e.g.
        for registration) without needing a live IB session.
        """
        try:
            from radon.clients.ib_client import IBClient  # noqa: F401

            return True
        except ImportError:
            return False

    # -- main scan entry point ----------------------------------------------

    def scan(self, ticker: str, **kwargs: Any) -> StrategySignal:
        """Run the LEAP IV mispricing scan for *ticker*.

        Keyword Args:
            client: A connected :class:`IBClient` instance (required).
            target_years: Expiration years to scan (default [2027, 2028]).
            target_deltas: Delta targets (default [0.5, 0.3, 0.2, 0.1]).
            min_gap: Minimum HV-IV spread to flag (default 15).

        Returns:
            A :class:`StrategySignal` whose ``data`` dict contains:
            - ``volatility``: multi-timeframe HV snapshot
            - ``options``: list of analysed option dicts
            - ``mispriced_count``: number of flagged contracts
            - ``best_opportunity``: highest-scoring option (or ``None``)
        """
        client = kwargs.get("client")
        if client is None:
            return self._unavailable_signal(ticker)

        if not client.is_available():
            return self._unavailable_signal(ticker)

        target_years: list[int] = kwargs.get("target_years", _DEFAULT_YEARS)
        target_deltas: list[float] = kwargs.get("target_deltas", _TARGET_DELTAS)
        min_gap: float = kwargs.get("min_gap", _MIN_IV_GAP)

        # 1. Volatility snapshot
        vol = _fetch_volatility_data(client, ticker)
        if vol is None:
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={"ticker": ticker, "error": "insufficient historical data"},
                source=self.strategy_id,
            )

        # 2. LEAP expirations
        expirations = _get_leap_expirations(client, ticker, target_years)

        # 3. Scan each expiration
        all_analyses: list[_OptionAnalysis] = []
        for expiry in expirations:
            chain = _fetch_option_chain(client, ticker, expiry, vol.current_price)
            if not chain:
                continue
            delta_matches = _find_strikes_by_delta(chain, target_deltas)
            all_analyses.extend(
                _analyze_mispricing(opt, vol, min_gap) for opt in delta_matches.values()
            )

        # 4. Compile results
        mispriced = [a for a in all_analyses if a.is_mispriced]
        best: _OptionAnalysis | None = (
            max(all_analyses, key=lambda a: a.mispricing_score)
            if all_analyses
            else None
        )

        confidence = self._compute_confidence(mispriced, best)
        signal_type = "bullish" if mispriced else "neutral"

        vol_dict = {
            "ticker": vol.ticker,
            "current_price": vol.current_price,
            "hv_20": vol.hv_20,
            "hv_60": vol.hv_60,
            "hv_252": vol.hv_252,
            "hv_756": vol.hv_756,
            "avg_hv": vol.avg_hv,
        }

        options_list = [
            {
                "expiry": a.expiry,
                "strike": a.strike,
                "right": a.right,
                "delta": a.delta,
                "iv": a.iv,
                "bid": a.bid,
                "ask": a.ask,
                "mid": a.mid,
                "vega": a.vega,
                "theta": a.theta,
                "hv_20_gap": a.hv_20_gap,
                "hv_60_gap": a.hv_60_gap,
                "hv_avg_gap": a.hv_avg_gap,
                "is_mispriced": a.is_mispriced,
                "mispricing_score": a.mispricing_score,
            }
            for a in all_analyses
        ]

        best_dict: dict[str, Any] | None = None
        if best is not None:
            best_dict = {
                "expiry": best.expiry,
                "strike": best.strike,
                "delta": best.delta,
                "iv": best.iv,
                "hv_20_gap": best.hv_20_gap,
                "mispricing_score": best.mispricing_score,
            }

        return StrategySignal(
            signal_type=signal_type,
            confidence=confidence,
            data={
                "ticker": ticker,
                "volatility": vol_dict,
                "options": options_list,
                "mispriced_count": len(mispriced),
                "best_opportunity": best_dict,
                "target_years": target_years,
                "min_gap": min_gap,
            },
            source=self.strategy_id,
        )

    # -- private helpers ----------------------------------------------------

    @staticmethod
    def _compute_confidence(
        mispriced: list[_OptionAnalysis],
        best: _OptionAnalysis | None,
    ) -> float:
        """Derive a 0-1 confidence score from scan results."""
        if not mispriced or best is None:
            return 0.0
        # More mispriced contracts → higher confidence (cap at 1.0)
        count_factor = min(len(mispriced) / 5.0, 1.0)
        # Higher mispricing score → higher confidence (cap at 1.0)
        score_factor = min(best.mispricing_score / 30.0, 1.0)
        return round(0.5 * count_factor + 0.5 * score_factor, 2)

    @staticmethod
    def _unavailable_signal(ticker: str) -> StrategySignal:
        """Return a neutral signal when IB is unavailable."""
        return StrategySignal(
            signal_type="neutral",
            confidence=0.0,
            data={"ticker": ticker, "error": "IB client unavailable"},
            source="leap-iv-mispricing",
        )


# ---------------------------------------------------------------------------
# Self-registration
# ---------------------------------------------------------------------------

_registry = None
try:
    from radon.strategies.base import StrategyRegistry

    _registry = StrategyRegistry()
    _registry.register(LeapIVStrategy)
except Exception:
    pass
