"""GARCH Convergence Spread Scanner strategy.

Scans correlated asset pairs for cross-asset volatility repricing lags.
When a catalyst elevates realized vol in a sector, components reprice IV at
different rates — this strategy identifies the lagger's underpriced options.

Adapted from radon/scripts/garch_convergence.py — all CLI, HTML report
generation, and subprocess code has been removed.  Only the core scan logic
and gate-check machinery are preserved.

Strategy metadata lives in ``tradingagents/radon/data/strategies.json``
under the id ``"garch-convergence"``.
"""

from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from tradingagents.radon.strategies.base import StrategySignal

logger = logging.getLogger(__name__)

PAIR_PRESETS: dict[str, dict[str, Any]] = {
    "semis": {
        "description": "Semiconductors",
        "pairs": [["NVDA", "AMD"], ["TSM", "ASML"], ["AVGO", "QCOM"], ["MU", "AMAT"]],
        "vol_driver": "AI/cloud capex, memory demand, equipment cycle",
    },
    "mega-tech": {
        "description": "Mega-Cap Tech",
        "pairs": [["AAPL", "MSFT"], ["GOOGL", "META"], ["AMZN", "NFLX"]],
        "vol_driver": "Ad spend, cloud growth, consumer tech cycle",
    },
    "energy": {
        "description": "Energy",
        "pairs": [["XOM", "COP"], ["SLB", "HAL"], ["XLE", "OIH"]],
        "vol_driver": "Oil/gas prices, OPEC policy, drilling activity",
    },
    "china-etf": {
        "description": "China / Asia",
        "pairs": [["FXI", "BABA"], ["EWY", "FXI"]],
        "vol_driver": "China policy, trade tariffs, geopolitics",
    },
}

_SIGNAL_CONFIDENCE: dict[str, float] = {
    "STRONG": 0.90,
    "MODERATE": 0.70,
    "WEAK": 0.50,
    "NONE": 0.10,
}

_SIGNAL_TYPE: dict[str, str] = {
    "STRONG": "bullish",
    "MODERATE": "bullish",
    "WEAK": "neutral",
    "NONE": "neutral",
}


@dataclass
class _TickerVol:
    """IV / HV snapshot for a single ticker."""

    ticker: str
    price: float = 0.0
    hv20: float = 0.0
    hv60: float = 0.0
    hv252: float = 0.0
    leap_atm_iv: float = 0.0
    leap_30d_iv: float = 0.0
    iv_rank: float = 0.0
    current_iv: float = 0.0
    leap_count: int = 0
    has_leaps: bool = False
    error: str | None = None

    @property
    def iv_hv60(self) -> float:
        """Ratio of LEAP ATM IV to 60-day HV."""
        return self.leap_atm_iv / self.hv60 if self.hv60 > 0 else 0.0

    @property
    def hv20_minus_iv(self) -> float:
        """Gap between 20-day HV and LEAP ATM IV (positive = IV cheap)."""
        return self.hv20 - self.leap_atm_iv


@dataclass
class _PairAnalysis:
    """GARCH divergence analysis for a correlated pair."""

    ticker_a: str
    ticker_b: str
    vol_a: _TickerVol | None = None
    vol_b: _TickerVol | None = None
    leader: str = ""
    lagger: str = ""
    divergence: float = 0.0
    lagger_hv_iv_gap: float = 0.0
    lagger_iv_rank: float = 0.0
    shared_vol_driver: str = ""
    gate_divergence: bool = False
    gate_hv_gap: bool = False
    gate_vol_driver: bool = True
    gate_iv_rank: bool = False
    gate_liquidity: bool = True
    signal: str = "NONE"
    failing_gates: list[str] = field(default_factory=list)
    expected_iv: float = 0.0
    expected_move: float = 0.0

    @property
    def all_gates_pass(self) -> bool:
        """Return True when every gate check passes."""
        return all([
            self.gate_divergence,
            self.gate_hv_gap,
            self.gate_vol_driver,
            self.gate_iv_rank,
            self.gate_liquidity,
        ])


def _calc_hv(prices: list[float], period: int) -> float:
    """Annualised historical volatility from log returns."""
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
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(var) * math.sqrt(252) * 100


def _fetch_uw_prices(ticker: str, uw_client: Any) -> list[float]:
    """Fetch daily close prices via Unusual Whales OHLC endpoint."""
    try:
        data = uw_client.get_stock_ohlc(ticker, candle_size="1d")
        bars = data.get("data", [])
        if bars:
            return [float(b["close"]) for b in bars if b.get("close") is not None]
    except Exception:
        logger.debug("UW OHLC fetch failed for %s", ticker, exc_info=True)
    return []


def _fetch_uw_iv(ticker: str, client: Any) -> tuple[float, float]:
    """Current IV and IV rank from UW.  Returns ``(iv%, rank%)``."""
    try:
        data = client.get_iv_rank(ticker)
        if data.get("data"):
            latest = data["data"][0]
            iv = float(latest.get("volatility", 0)) * 100
            rank = float(latest.get("iv_rank_1y", 0))
            return iv, rank
    except Exception:
        logger.debug("UW IV rank fetch failed for %s", ticker, exc_info=True)
    return 0.0, 0.0


def _fetch_uw_leaps(
    ticker: str,
    client: Any,
    min_year: int = 2027,
) -> list[dict[str, Any]]:
    """Fetch LEAP call options from UW.

    Returns a list of dicts with keys ``strike``, ``iv``, ``oi``.
    """
    try:
        resp = client.get_option_contracts(ticker)
    except Exception:
        logger.debug("UW option contracts fetch failed for %s", ticker, exc_info=True)
        return []

    results: list[dict[str, Any]] = []
    for c in resp.get("data", []):
        sym = c.get("option_symbol", "")
        try:
            date_start = None
            for i in range(3, len(sym)):
                if sym[i : i + 2].isdigit():
                    date_start = i
                    break
            if date_start is None:
                continue
            year = int("20" + sym[date_start : date_start + 2])
            if year < min_year:
                continue
            right_idx = date_start + 6
            if sym[right_idx] != "C":
                continue
            strike = int(sym[right_idx + 1 :]) / 1000
            iv = float(c.get("implied_volatility", 0)) * 100
            if iv == 0:
                continue
            results.append({
                "strike": strike,
                "iv": iv,
                "oi": int(c.get("open_interest", 0)),
            })
        except (ValueError, IndexError):
            continue
    return results


def _fetch_ticker_vol(ticker: str, uw_client: Any) -> _TickerVol:
    """Fetch all volatility data for one ticker."""
    tv = _TickerVol(ticker=ticker)

    prices = _fetch_uw_prices(ticker, uw_client)
    if len(prices) < 60:
        tv.error = "Insufficient price data"
        return tv

    tv.price = prices[-1]
    tv.hv20 = round(_calc_hv(prices, 20), 2)
    tv.hv60 = round(_calc_hv(prices, 60), 2)
    tv.hv252 = round(_calc_hv(prices, 252), 2)

    tv.current_iv, tv.iv_rank = _fetch_uw_iv(ticker, uw_client)

    leaps = _fetch_uw_leaps(ticker, uw_client)
    tv.leap_count = len(leaps)
    tv.has_leaps = len(leaps) > 0

    if leaps and tv.price > 0:
        atm: list[float] = []
        d30: list[float] = []
        for lp in leaps:
            m = tv.price / lp["strike"]
            if 0.90 <= m <= 1.10:
                atm.append(lp["iv"])
            elif 0.75 <= m < 0.90:
                d30.append(lp["iv"])
        tv.leap_atm_iv = round(sum(atm) / len(atm), 2) if atm else 0.0
        tv.leap_30d_iv = round(sum(d30) / len(d30), 2) if d30 else 0.0
        if tv.leap_atm_iv == 0 and leaps:
            all_ivs = sorted(lp["iv"] for lp in leaps)
            tv.leap_atm_iv = round(all_ivs[len(all_ivs) // 2], 2)

    return tv


def _fetch_all_tickers(
    tickers: list[str],
    uw_client: Any,
    max_workers: int = 8,
) -> dict[str, _TickerVol]:
    """Fetch vol data for all tickers in parallel using a shared UWClient."""
    results: dict[str, _TickerVol] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_ticker_vol, t, uw_client): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                results[ticker] = future.result()
            except Exception as exc:
                results[ticker] = _TickerVol(ticker=ticker, error=str(exc))
    return results


def _analyze_pair(
    a: str,
    b: str,
    vol_data: dict[str, _TickerVol],
    vol_driver: str = "",
) -> _PairAnalysis:
    """Compute GARCH divergence metrics for a pair."""
    pa = _PairAnalysis(ticker_a=a, ticker_b=b, shared_vol_driver=vol_driver)
    va = vol_data.get(a)
    vb = vol_data.get(b)
    pa.vol_a = va
    pa.vol_b = vb

    if not va or not vb:
        pa.failing_gates.append("MISSING_DATA")
        return pa
    if not va.has_leaps:
        pa.failing_gates.append(f"{a}: no LEAPs")
        return pa
    if not vb.has_leaps:
        pa.failing_gates.append(f"{b}: no LEAPs")
        return pa

    if va.iv_hv60 >= vb.iv_hv60:
        pa.leader, pa.lagger = a, b
        leader_vol, lagger_vol = va, vb
    else:
        pa.leader, pa.lagger = b, a
        leader_vol, lagger_vol = vb, va

    pa.divergence = round(leader_vol.iv_hv60 - lagger_vol.iv_hv60, 3)
    pa.lagger_hv_iv_gap = round(lagger_vol.hv20 - lagger_vol.leap_atm_iv, 1)
    pa.lagger_iv_rank = lagger_vol.iv_rank

    if leader_vol.iv_hv60 > 0 and lagger_vol.hv60 > 0:
        pa.expected_iv = round(leader_vol.iv_hv60 * lagger_vol.hv60, 1)
        pa.expected_move = round(pa.expected_iv - lagger_vol.leap_atm_iv, 1)

    pa.gate_divergence = leader_vol.iv_hv60 >= 1.0 and pa.divergence >= 0.15
    if not pa.gate_divergence:
        pa.failing_gates.append(
            f"Divergence {pa.divergence:.2f} (leader IV/HV {leader_vol.iv_hv60:.2f})"
        )

    pa.gate_hv_gap = pa.lagger_hv_iv_gap >= 10.0
    if not pa.gate_hv_gap:
        pa.failing_gates.append(
            f"HV20-IV = {pa.lagger_hv_iv_gap:+.1f} pts (need >=+10)"
        )

    pa.gate_vol_driver = bool(vol_driver)
    if not pa.gate_vol_driver:
        pa.failing_gates.append("No confirmed shared vol driver")

    pa.gate_iv_rank = lagger_vol.iv_rank < 50.0
    if not pa.gate_iv_rank:
        pa.failing_gates.append(f"Lagger IV rank {lagger_vol.iv_rank:.0f}% (need <50%)")

    pa.gate_liquidity = lagger_vol.has_leaps

    if pa.all_gates_pass:
        if (
            pa.divergence >= 0.30
            and pa.lagger_hv_iv_gap >= 20
            and pa.lagger_iv_rank < 30
        ):
            pa.signal = "STRONG"
        elif (
            pa.divergence >= 0.20
            and pa.lagger_hv_iv_gap >= 15
            and pa.lagger_iv_rank < 40
        ):
            pa.signal = "MODERATE"
        else:
            pa.signal = "WEAK"
    else:
        pa.signal = "NONE"

    return pa


def _find_pairs_for_ticker(ticker: str) -> list[tuple[str, str, str]]:
    """Return ``(ticker_a, ticker_b, vol_driver)`` tuples involving *ticker*.

    Searches all built-in presets for pairs containing *ticker*.
    """
    found: list[tuple[str, str, str]] = []
    upper = ticker.upper()
    for preset_data in PAIR_PRESETS.values():
        driver = preset_data.get("vol_driver", "")
        found.extend(
            (pair[0], pair[1], driver)
            for pair in preset_data["pairs"]
            if upper in {pair[0].upper(), pair[1].upper()}
        )
    return found


class GARCHConvergenceStrategy:
    """GARCH Convergence Spread Scanner strategy.

    Detects cross-asset volatility repricing lags between correlated
    asset pairs.  When realized vol is elevated but a correlated ticker's
    LEAP IV hasn't caught up, the lagger's options are underpriced.

    Requires an IB connection (for trade execution) and UW API access
    (for IV / HV / LEAP data).
    """

    strategy_id: str = "garch-convergence"
    strategy_name: str = "GARCH Convergence Spreads"
    required_clients: list[str] = ["ib"]

    def is_available(self) -> bool:
        """Return ``True`` when IB client dependency is present."""
        try:
            from tradingagents.radon.clients.ib_client import HAS_IB

            return HAS_IB
        except ImportError:
            return False

    def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
        """Run the GARCH convergence scan for *ticker*.

        Args:
            ticker: Primary ticker to scan.  Can be a single symbol or a
                comma-separated pair (e.g. ``"NVDA,AMD"``).
            pair: Optional second ticker in the pair (kwarg).
            preset: Optional preset name to scan (kwarg).

        Returns:
            A :class:`StrategySignal` with the scan result.  The ``data``
            dict contains the full analysis for each evaluated pair.
        """
        pair: str | None = kwargs.get("pair")  # type: ignore[assignment]
        preset: str | None = kwargs.get("preset")  # type: ignore[assignment]

        pairs_to_scan = self._resolve_pairs(ticker, pair, preset)

        if not pairs_to_scan:
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={"error": f"No pairs found for {ticker}"},
                source=self.strategy_id,
            )

        unique_tickers: list[str] = []
        seen: set[str] = set()
        for a, b, _ in pairs_to_scan:
            for t in (a, b):
                if t not in seen:
                    unique_tickers.append(t)
                    seen.add(t)

        vol_data = self._fetch_vol_data(unique_tickers)

        analyses: list[_PairAnalysis] = []
        for a, b, driver in pairs_to_scan:
            analyses.append(_analyze_pair(a, b, vol_data, vol_driver=driver))

        best = self._best_signal(analyses)

        confidence = _SIGNAL_CONFIDENCE.get(best.signal, 0.10)
        signal_type = _SIGNAL_TYPE.get(best.signal, "neutral")

        pair_results: list[dict[str, Any]] = [
            {
                "pair": [pa.ticker_a, pa.ticker_b],
                "leader": pa.leader,
                "lagger": pa.lagger,
                "divergence": pa.divergence,
                "lagger_hv_iv_gap": pa.lagger_hv_iv_gap,
                "lagger_iv_rank": pa.lagger_iv_rank,
                "signal": pa.signal,
                "gates_passed": pa.all_gates_pass,
                "failing_gates": pa.failing_gates,
                "expected_iv": pa.expected_iv,
                "expected_move": pa.expected_move,
            }
            for pa in analyses
        ]

        ticker_data: dict[str, dict[str, Any]] = {}
        for t, tv in vol_data.items():
            ticker_data[t] = {
                "price": tv.price,
                "hv20": tv.hv20,
                "hv60": tv.hv60,
                "hv252": tv.hv252,
                "leap_atm_iv": tv.leap_atm_iv,
                "iv_rank": tv.iv_rank,
                "current_iv": tv.current_iv,
                "iv_hv60": round(tv.iv_hv60, 3),
                "hv20_minus_iv": round(tv.hv20_minus_iv, 1),
                "has_leaps": tv.has_leaps,
                "leap_count": tv.leap_count,
            }

        return StrategySignal(
            signal_type=signal_type,
            confidence=confidence,
            data={
                "best_pair": [best.ticker_a, best.ticker_b],
                "best_signal": best.signal,
                "best_divergence": best.divergence,
                "lagger": best.lagger,
                "lagger_hv_iv_gap": best.lagger_hv_iv_gap,
                "expected_move": best.expected_move,
                "pairs": pair_results,
                "tickers": ticker_data,
            },
            source=self.strategy_id,
        )

    def _resolve_pairs(
        self,
        ticker: str,
        pair: str | None,
        preset: str | None,
    ) -> list[tuple[str, str, str]]:
        """Resolve ticker / pair / preset kwargs into scan pairs.

        Returns a list of ``(ticker_a, ticker_b, vol_driver)`` tuples.
        """
        if preset and preset in PAIR_PRESETS:
            pdata = PAIR_PRESETS[preset]
            driver = pdata.get("vol_driver", "")
            return [(p[0], p[1], driver) for p in pdata["pairs"]]

        if "," in ticker:
            parts = [t.strip().upper() for t in ticker.split(",")]
            if len(parts) >= 2:
                return [(parts[0], parts[1], "")]

        if pair:
            return [(ticker.upper(), pair.upper(), "")]

        found = _find_pairs_for_ticker(ticker)
        if found:
            return found

        return []

    def _fetch_vol_data(self, tickers: list[str]) -> dict[str, _TickerVol]:
        """Fetch volatility data for all tickers via UWClient."""
        try:
            from tradingagents.radon.clients.uw_client import UWClient

            with UWClient() as uw:
                if not uw.is_available():
                    return {
                        t: _TickerVol(ticker=t, error="UW client unavailable")
                        for t in tickers
                    }
                return _fetch_all_tickers(tickers, uw)
        except ImportError:
            return {
                t: _TickerVol(ticker=t, error="UW client not installed")
                for t in tickers
            }
        except Exception as exc:
            logger.exception("Vol data fetch failed")
            return {t: _TickerVol(ticker=t, error=str(exc)) for t in tickers}

    @staticmethod
    def _best_signal(analyses: list[_PairAnalysis]) -> _PairAnalysis:
        """Return the analysis with the strongest actionable signal."""
        passing = [pa for pa in analyses if pa.all_gates_pass]
        if passing:
            return max(passing, key=lambda p: p.divergence)
        if analyses:
            return max(analyses, key=lambda p: p.divergence)
        return _PairAnalysis(ticker_a="", ticker_b="")


def _register(registry: Any) -> None:
    """Register this strategy with a :class:`StrategyRegistry`."""
    registry.register(GARCHConvergenceStrategy)


try:
    from tradingagents.radon.strategies.base import StrategyRegistry

    _DEFAULT_REGISTRY = StrategyRegistry()
    _register(_DEFAULT_REGISTRY)
except Exception:
    pass
