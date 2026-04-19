"""Risk reversal scanner strategy for the Radon module.

Scans a ticker's options chain for optimal risk reversal structures
(sell OTM put / buy OTM call for bullish, or inverse for bearish).
Exploits IV skew between puts and calls to find costless or
credit-generating directional exposure.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from radon.strategies.base import StrategyRegistry, StrategySignal

logger = logging.getLogger(__name__)

_DEFAULT_BANKROLL = 1_000_000.0
_DEFAULT_MAX_PCT = 0.025
_DEFAULT_MIN_DTE = 14
_DEFAULT_MAX_DTE = 60
_DEFAULT_IB_PORT = 4001


class RiskReversalStrategy:
    """Risk reversal scanner that exploits IV skew for directional bets.

    Scans a ticker's options chain via Interactive Brokers for optimal risk
    reversal structures. Uses dark pool and options flow data from Unusual
    Whales for directional context and confidence scoring.

    The scan:
      1. Fetches dark pool flow and options flow from UW for context.
      2. Fetches the live option chain with greeks from IB.
      3. Builds a combination matrix of short-leg / long-leg pairs.
      4. Selects the best primary, alternative, and aggressive picks.
      5. Computes a confidence score based on skew, cost, and flow alignment.

    Required clients:
        ib: Interactive Brokers (option chain, greeks, spot price).
        uw: Unusual Whales (dark pool flow, options flow).
    """

    strategy_id: str = "risk-reversal"
    strategy_name: str = "Risk Reversal Scanner"
    required_clients: list[str] = ["ib", "uw"]

    def __init__(self) -> None:
        self._ib_client: Any = None
        self._uw_client: Any = None

    # -- client helpers ------------------------------------------------------

    def _get_ib_client(self) -> Any:
        """Lazily instantiate the IB client."""
        if self._ib_client is None:
            from radon.clients.ib_client import IBClient

            self._ib_client = IBClient()
        return self._ib_client

    def _get_uw_client(self) -> Any:
        """Lazily instantiate the UW client."""
        if self._uw_client is None:
            from radon.clients.uw_client import UWClient

            self._uw_client = UWClient()
        return self._uw_client

    def is_available(self) -> bool:
        """Return True when both IB and UW clients are available."""
        try:
            ib = self._get_ib_client()
            uw = self._get_uw_client()
            return ib.is_available() and uw.is_available()
        except Exception:
            return False

    # -- IB chain fetch ------------------------------------------------------

    def _fetch_chain(
        self,
        ticker: str,
        ib_client: Any,
        min_dte: int = _DEFAULT_MIN_DTE,
        max_dte: int = _DEFAULT_MAX_DTE,
        *,
        bearish: bool = False,
    ) -> dict | None:
        """Fetch live option quotes with greeks from IB.

        Args:
            ticker: Stock symbol.
            ib_client: Connected IBClient instance.
            min_dte: Minimum days to expiry.
            max_dte: Maximum days to expiry.
            bearish: Use bearish direction (sell call / buy put).

        Returns:
            Dict with spot, expirations, options, short_right, long_right,
            or None on failure.
        """
        try:
            from ib_insync import Option, Stock
        except ImportError:
            logger.warning("ib_insync not available for chain fetch")
            return None

        ib = ib_client.ib
        if ib is None:
            return None

        try:
            ib_client.set_market_data_type(1)

            stock = Stock(ticker, "SMART", "USD")
            q_stocks = ib_client.qualify_contracts(stock)
            if not q_stocks:
                logger.warning("Could not qualify stock %s", ticker)
                return None

            spot_tickers = ib.reqTickers(q_stocks[0])
            if not spot_tickers:
                return None
            spot = spot_tickers[0].marketPrice()
            if spot is None or spot <= 0:
                return None

            chains = ib.reqSecDefOptParams(
                q_stocks[0].symbol, "", q_stocks[0].secType, q_stocks[0].conId
            )
            if not chains:
                return None
            chain = next((c for c in chains if c.exchange == "SMART"), chains[0])

            today = datetime.now()
            target_expiries = sorted(
                exp
                for exp in chain.expirations
                if min_dte <= (datetime.strptime(exp, "%Y%m%d") - today).days <= max_dte
            )
            if len(target_expiries) > 5:
                target_expiries = target_expiries[:5]

            if not target_expiries:
                return None

            valid_strikes = sorted(chain.strikes)

            # Bullish: sell OTM put / buy OTM call; Bearish: sell OTM call / buy OTM put
            if bearish:
                short_right, long_right = "C", "P"
                short_strikes = [s for s in valid_strikes if spot <= s <= spot * 1.12]
                long_strikes = [s for s in valid_strikes if spot * 0.88 <= s <= spot]
            else:
                short_right, long_right = "P", "C"
                short_strikes = [s for s in valid_strikes if spot * 0.88 <= s <= spot]
                long_strikes = [s for s in valid_strikes if spot <= s <= spot * 1.12]

            contracts: list[Any] = []
            for exp in target_expiries:
                contracts.extend(
                    Option(ticker, exp, s, short_right, "SMART") for s in short_strikes
                )
                contracts.extend(
                    Option(ticker, exp, s, long_right, "SMART") for s in long_strikes
                )

            if not contracts:
                return None

            qualified = ib_client.qualify_contracts(*contracts) or []
            if not qualified:
                return None

            tickers = ib.reqTickers(*qualified)
            ib_client.sleep(5)

            options: list[dict[str, Any]] = []
            for t in tickers:
                c = t.contract
                bid = t.bid if t.bid and t.bid > 0 else 0.0
                ask = t.ask if t.ask and t.ask > 0 else 0.0
                mid = (bid + ask) / 2 if bid > 0 and ask > 0 else 0.0

                greeks = t.modelGreeks or t.lastGreeks
                delta = gamma = theta = vega = iv = 0.0
                if greeks:
                    delta = greeks.delta or 0.0
                    gamma = greeks.gamma or 0.0
                    theta = greeks.theta or 0.0
                    vega = greeks.vega or 0.0
                    iv = greeks.impliedVol or 0.0

                if mid > 0 and abs(delta) >= 0.15:
                    dte = (
                        datetime.strptime(c.lastTradeDateOrContractMonth, "%Y%m%d")
                        - today
                    ).days
                    options.append({
                        "expiry": c.lastTradeDateOrContractMonth,
                        "dte": dte,
                        "right": c.right,
                        "strike": c.strike,
                        "bid": bid,
                        "ask": ask,
                        "mid": mid,
                        "delta": delta,
                        "gamma": gamma,
                        "theta": theta,
                        "vega": vega,
                        "iv": iv,
                    })

            return {
                "spot": spot,
                "expirations": target_expiries,
                "options": options,
                "short_right": short_right,
                "long_right": long_right,
            }
        except Exception:
            logger.exception("Chain fetch failed for %s", ticker)
            return None

    # -- matrix builder ------------------------------------------------------

    @staticmethod
    def _build_matrix(
        chain_data: dict,
        bankroll: float,
        max_pct: float = _DEFAULT_MAX_PCT,
    ) -> dict:
        """Build the risk reversal combination matrix from chain data.

        Generates all short-leg/long-leg pairs within 25-50 delta,
        computes per-expiry IV skew, and selects the best primary,
        alternative, and aggressive picks.

        Args:
            chain_data: Output from _fetch_chain.
            bankroll: Total bankroll for position sizing.
            max_pct: Max fraction of bankroll for margin.

        Returns:
            Dict with all_combos, costless, primary, alternative,
            aggressive, skew_by_exp, spot, bankroll, max_risk.
        """
        spot = chain_data["spot"]
        options = chain_data["options"]
        short_right = chain_data["short_right"]
        long_right = chain_data["long_right"]
        max_risk = bankroll * max_pct

        by_exp: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for o in options:
            by_exp.setdefault(o["expiry"], {}).setdefault(o["right"], []).append(o)

        all_combos: list[dict[str, Any]] = []
        skew_by_exp: dict[str, list[dict[str, Any]]] = {}

        for exp, sides in sorted(by_exp.items()):
            short_opts = sides.get(short_right, [])
            long_opts = sides.get(long_right, [])

            skew_rows: list[dict[str, Any]] = []
            for delta_target in [0.50, 0.40, 0.35, 0.30, 0.25]:
                s_opt = min(
                    short_opts,
                    key=lambda o, d=delta_target: abs(abs(o["delta"]) - d),
                    default=None,
                )
                l_opt = min(
                    long_opts,
                    key=lambda o, d=delta_target: abs(abs(o["delta"]) - d),
                    default=None,
                )
                if s_opt and l_opt:
                    skew_rows.append({
                        "delta": delta_target,
                        "short_iv": s_opt["iv"] * 100,
                        "long_iv": l_opt["iv"] * 100,
                        "skew": (s_opt["iv"] - l_opt["iv"]) * 100,
                    })
            skew_by_exp[exp] = skew_rows

            short_filtered = [o for o in short_opts if 0.25 <= abs(o["delta"]) <= 0.50]
            long_filtered = [o for o in long_opts if 0.25 <= abs(o["delta"]) <= 0.50]

            for s in short_filtered:
                for lg in long_filtered:
                    premium_received = s["bid"]
                    premium_paid = lg["ask"]
                    net = premium_received - premium_paid

                    margin_per_contract = s["strike"] * 100 * 0.20
                    max_qty = (
                        int(max_risk / margin_per_contract)
                        if margin_per_contract > 0
                        else 0
                    )
                    total_margin = max_qty * margin_per_contract

                    skew = (s["iv"] - lg["iv"]) * 100
                    net_delta = lg["delta"] + s["delta"]

                    all_combos.append({
                        "expiry": exp,
                        "dte": s["dte"],
                        "short_strike": s["strike"],
                        "short_delta": abs(s["delta"]),
                        "short_bid": s["bid"],
                        "short_iv": s["iv"] * 100,
                        "long_strike": lg["strike"],
                        "long_delta": abs(lg["delta"]),
                        "long_ask": lg["ask"],
                        "long_iv": lg["iv"] * 100,
                        "net": net,
                        "skew": skew,
                        "net_delta": net_delta,
                        "max_qty": max_qty,
                        "margin": total_margin,
                        "short_right": short_right,
                        "long_right": long_right,
                    })

        costless = [c for c in all_combos if -0.50 <= c["net"] <= 2.00]

        primary: dict | None = None
        if costless:
            primary_candidates = sorted(
                costless,
                key=lambda c: (
                    abs(c["net"]) < 0.10,
                    c["dte"],
                    -abs(c["short_delta"] - c["long_delta"]),
                    c["skew"],
                ),
                reverse=True,
            )
            primary = primary_candidates[0] if primary_candidates else None

        alternative: dict | None = None
        if primary and costless:
            alt_candidates = [
                c
                for c in costless
                if c["expiry"] != primary["expiry"]
                and abs(c["net"]) < 0.50
                and abs(c["short_delta"] - c["long_delta"]) < 0.10
            ]
            alt_candidates.sort(key=lambda c: (abs(c["net"]), -c["skew"]))
            alternative = alt_candidates[0] if alt_candidates else None

        aggressive: dict | None = None
        credit_combos = sorted(
            [
                c
                for c in all_combos
                if c["net"] >= 1.00
                and (primary is None or c["expiry"] == primary["expiry"])
            ],
            key=lambda c: (-c["net"], abs(c["short_delta"] - c["long_delta"])),
        )
        if credit_combos:
            aggressive = credit_combos[0]

        return {
            "all_combos": all_combos,
            "costless": costless,
            "primary": primary,
            "alternative": alternative,
            "aggressive": aggressive,
            "skew_by_exp": skew_by_exp,
            "spot": spot,
            "bankroll": bankroll,
            "max_risk": max_risk,
        }

    # -- confidence scoring --------------------------------------------------

    @staticmethod
    def _compute_confidence(
        matrix: dict,
        *,
        bearish: bool,
        flow_data: dict | None,
    ) -> float:
        """Compute a confidence score between 0.0 and 1.0.

        Scoring factors:
          - Primary pick found:         +0.30
          - Near-costless or credit:    +0.10 / +0.05
          - Delta balance (<0.05):      +0.10
          - Delta balance (<0.10):      +0.05
          - IV skew > 5%:               +0.10
          - IV skew > 10%:              +0.05
          - Flow direction aligned:     +0.15
          - Flow direction present:     +0.05
          - DP buy ratio > 60%:         +0.05

        Args:
            matrix: Output from _build_matrix.
            bearish: Whether scanning for bearish reversal.
            flow_data: Dark pool flow data from UW (or None).

        Returns:
            Confidence score clamped to [0.0, 0.95].
        """
        score = 0.0
        primary = matrix.get("primary")

        if primary:
            score += 0.30

            if abs(primary["net"]) < 0.10:
                score += 0.10
            elif primary["net"] >= 0:
                score += 0.05

            delta_diff = abs(primary["short_delta"] - primary["long_delta"])
            if delta_diff < 0.05:
                score += 0.10
            elif delta_diff < 0.10:
                score += 0.05

            if primary["skew"] > 5.0:
                score += 0.10
            if primary["skew"] > 10.0:
                score += 0.05

        if flow_data:
            dp = flow_data.get("dark_pool", {})
            agg = dp.get("aggregate", {})
            direction = agg.get("flow_direction", "UNKNOWN")
            dp_buy_ratio = agg.get("dp_buy_ratio", 0)

            aligned = (direction == "ACCUMULATION" and not bearish) or (
                direction == "DISTRIBUTION" and bearish
            )
            if aligned:
                score += 0.15
            elif direction in {"ACCUMULATION", "DISTRIBUTION"}:
                score += 0.05

            if dp_buy_ratio > 0.60:
                score += 0.05

        return min(score, 0.95)

    # -- main scan -----------------------------------------------------------

    def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
        """Scan for risk reversal opportunities on *ticker*.

        Keyword Args:
            bearish: Scan for bearish reversal (sell call / buy put).
                     Default False (bullish: sell put / buy call).
            bankroll: Total bankroll for position sizing. Default 1,000,000.
            max_pct: Max pct of bankroll as margin. Default 0.025.
            min_dte: Minimum days to expiry. Default 14.
            max_dte: Maximum days to expiry. Default 60.
            ib_port: IB Gateway port. Default 4001.

        Returns:
            StrategySignal with scan results and confidence score.
            Returns neutral signal with confidence 0.0 when clients are
            unavailable or no data is found.
        """
        if not self.is_available():
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={"error": "Required clients (IB, UW) not available"},
                source=self.strategy_id,
            )

        bearish = bool(kwargs.get("bearish"))
        bankroll = (
            float(v)
            if isinstance(v := kwargs.get("bankroll"), int | float)
            else _DEFAULT_BANKROLL
        )
        max_pct = (
            float(v)
            if isinstance(v := kwargs.get("max_pct"), int | float)
            else _DEFAULT_MAX_PCT
        )
        min_dte = (
            int(v)
            if isinstance(v := kwargs.get("min_dte"), int | float)
            else _DEFAULT_MIN_DTE
        )
        max_dte = (
            int(v)
            if isinstance(v := kwargs.get("max_dte"), int | float)
            else _DEFAULT_MAX_DTE
        )
        ib_port = (
            int(v)
            if isinstance(v := kwargs.get("ib_port"), int | float)
            else _DEFAULT_IB_PORT
        )

        ib_client = self._get_ib_client()
        uw_client = self._get_uw_client()

        flow_data: dict | None = None
        try:
            flow_data = uw_client.get_darkpool_flow(ticker)
        except Exception:
            logger.warning("Failed to fetch dark pool flow for %s", ticker)

        options_flow: dict | None = None
        try:
            options_flow = uw_client.get_flow_alerts_by_ticker(ticker)
        except Exception:
            logger.warning("Failed to fetch options flow for %s", ticker)

        chain_data: dict | None = None
        try:
            ib_client.connect(port=ib_port, client_id=33)
            chain_data = self._fetch_chain(
                ticker,
                ib_client,
                min_dte=min_dte,
                max_dte=max_dte,
                bearish=bearish,
            )
        except Exception:
            logger.exception("IB chain fetch failed for %s", ticker)
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={"error": f"IB chain fetch failed for {ticker}"},
                source=self.strategy_id,
            )
        finally:
            ib_client.disconnect()

        if chain_data is None or not chain_data["options"]:
            return StrategySignal(
                signal_type="neutral",
                confidence=0.0,
                data={"error": f"No options data found for {ticker}"},
                source=self.strategy_id,
            )

        matrix = self._build_matrix(chain_data, bankroll, max_pct)
        confidence = self._compute_confidence(
            matrix, bearish=bearish, flow_data=flow_data
        )

        primary = matrix.get("primary")
        if not primary:
            signal_type = "neutral"
        elif bearish:
            signal_type = "bearish"
        else:
            signal_type = "bullish"

        return StrategySignal(
            signal_type=signal_type,
            confidence=confidence,
            data={
                "direction": "bearish" if bearish else "bullish",
                "spot": chain_data["spot"],
                "primary": matrix["primary"],
                "alternative": matrix["alternative"],
                "aggressive": matrix["aggressive"],
                "total_combos": len(matrix["all_combos"]),
                "costless_count": len(matrix["costless"]),
                "skew_by_expiry": matrix["skew_by_exp"],
                "flow_data": flow_data,
                "options_flow": options_flow,
            },
            source=self.strategy_id,
        )


def register(registry: StrategyRegistry) -> None:
    """Register the risk-reversal strategy with a StrategyRegistry instance."""
    registry.register(RiskReversalStrategy)
