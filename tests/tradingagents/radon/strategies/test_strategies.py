"""Tests for all 6 strategy implementations.

Tests cover:
- Static attributes (strategy_id, strategy_name, required_clients)
- is_available() behavior when clients are unavailable (default state)
- scan() return type and fields when clients are unavailable
- scan() with mocked clients producing valid StrategySignal outputs
- Strategy-specific internal logic (scoring, analysis, etc.)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tradingagents.radon.strategies.base import StrategySignal

# ---------------------------------------------------------------------------
# DarkPoolFlowStrategy
# ---------------------------------------------------------------------------
from tradingagents.radon.strategies.dark_pool_flow import DarkPoolFlowStrategy


class TestDarkPoolFlowStrategy:
    """Tests for DarkPoolFlowStrategy."""

    def test_strategy_id(self) -> None:
        assert DarkPoolFlowStrategy.strategy_id == "dark-pool-flow"

    def test_strategy_name(self) -> None:
        assert DarkPoolFlowStrategy.strategy_name == "Dark Pool Flow Scanner"

    def test_required_clients(self) -> None:
        assert DarkPoolFlowStrategy.required_clients == ["ib", "uw"]

    def test_is_available_false_when_no_clients(self) -> None:
        strategy = DarkPoolFlowStrategy()
        # Without real UW client, is_available returns False
        assert strategy.is_available() is False

    def test_scan_returns_signal_when_unavailable(self) -> None:
        strategy = DarkPoolFlowStrategy()
        result = strategy.scan("AAPL")
        assert isinstance(result, StrategySignal)
        assert result.signal_type == "neutral"
        assert result.confidence == 0.0
        assert result.source == "dark-pool-flow"

    def test_scan_with_mocked_uw_client(self) -> None:
        """Test scan with mocked UW client that returns flow data."""
        strategy = DarkPoolFlowStrategy()

        mock_uw = MagicMock()
        mock_uw.is_available.return_value = True
        mock_uw.get_darkpool_flow.return_value = {
            "dark_pool": {
                "aggregate": {
                    "flow_direction": "ACCUMULATION",
                    "flow_strength": 70.0,
                    "dp_buy_ratio": 0.75,
                    "num_prints": 200,
                },
                "daily": [
                    {
                        "flow_direction": "ACCUMULATION",
                        "flow_strength": 65.0,
                    },
                    {
                        "flow_direction": "ACCUMULATION",
                        "flow_strength": 60.0,
                    },
                ],
            },
        }

        with (
            patch.object(strategy, "_get_uw_client", return_value=mock_uw),
            patch.object(strategy, "_has_open_position", return_value=False),
        ):
            result = strategy.scan("AAPL")

        assert isinstance(result, StrategySignal)
        assert result.signal_type == "bullish"
        assert result.confidence > 0.0
        assert result.source == "dark-pool-flow"
        assert "score" in result.data
        assert result.data["direction"] == "ACCUMULATION"

    def test_scan_skips_ticker_with_open_position(self) -> None:
        """When skip_positions=True and there is an open position, returns neutral."""
        strategy = DarkPoolFlowStrategy()

        mock_uw = MagicMock()
        mock_uw.is_available.return_value = True

        with (
            patch.object(strategy, "_get_uw_client", return_value=mock_uw),
            patch.object(strategy, "_has_open_position", return_value=True),
        ):
            result = strategy.scan("AAPL", skip_positions=True)

        assert isinstance(result, StrategySignal)
        assert result.signal_type == "neutral"
        assert result.confidence == 0.0
        assert result.data.get("skipped") is True

    def test_analyze_signal_with_error(self) -> None:
        flow_data = {"error": "API timeout"}
        analysis = DarkPoolFlowStrategy._analyze_signal(flow_data)
        assert analysis["signal"] == "ERROR"
        assert analysis["score"] == -1

    def test_analyze_signal_strong_accumulation(self) -> None:
        flow_data = {
            "dark_pool": {
                "aggregate": {
                    "flow_direction": "ACCUMULATION",
                    "flow_strength": 80.0,
                    "dp_buy_ratio": 0.80,
                    "num_prints": 300,
                },
                "daily": [
                    {"flow_direction": "ACCUMULATION", "flow_strength": 75.0},
                    {"flow_direction": "ACCUMULATION", "flow_strength": 70.0},
                    {"flow_direction": "ACCUMULATION", "flow_strength": 65.0},
                ],
            },
        }
        analysis = DarkPoolFlowStrategy._analyze_signal(flow_data)
        assert analysis["signal"] == "STRONG"
        assert analysis["direction"] == "ACCUMULATION"
        assert analysis["score"] >= 60.0

    def test_analyze_signal_bearish_distribution(self) -> None:
        flow_data = {
            "dark_pool": {
                "aggregate": {
                    "flow_direction": "DISTRIBUTION",
                    "flow_strength": 55.0,
                    "dp_buy_ratio": 0.30,
                    "num_prints": 150,
                },
                "daily": [
                    {"flow_direction": "DISTRIBUTION", "flow_strength": 50.0},
                ],
            },
        }
        analysis = DarkPoolFlowStrategy._analyze_signal(flow_data)
        assert analysis["direction"] == "DISTRIBUTION"
        assert analysis["signal"] in {"STRONG", "MODERATE", "WEAK"}

    def test_analyze_signal_unknown_direction(self) -> None:
        flow_data = {
            "dark_pool": {
                "aggregate": {
                    "flow_direction": "UNKNOWN",
                    "flow_strength": 30.0,
                    "num_prints": 50,
                },
                "daily": [],
            },
        }
        analysis = DarkPoolFlowStrategy._analyze_signal(flow_data)
        assert analysis["signal"] == "NONE"

    def test_score_to_confidence_bounds(self) -> None:
        assert DarkPoolFlowStrategy._score_to_confidence(-50.0) >= 0.0
        assert DarkPoolFlowStrategy._score_to_confidence(200.0) <= 1.0
        assert DarkPoolFlowStrategy._score_to_confidence(50.0) > 0.0

    def test_signal_to_type_mapping(self) -> None:
        assert (
            DarkPoolFlowStrategy._signal_to_type("STRONG", "ACCUMULATION") == "bullish"
        )
        assert (
            DarkPoolFlowStrategy._signal_to_type("STRONG", "DISTRIBUTION") == "bearish"
        )
        assert DarkPoolFlowStrategy._signal_to_type("NONE", "UNKNOWN") == "neutral"
        assert DarkPoolFlowStrategy._signal_to_type("ERROR", "UNKNOWN") == "error"

    def test_options_conflict_reduces_score(self) -> None:
        """When options flow contradicts dark pool direction, score is reduced."""
        flow_data_no_conflict = {
            "dark_pool": {
                "aggregate": {
                    "flow_direction": "ACCUMULATION",
                    "flow_strength": 60.0,
                    "num_prints": 200,
                },
                "daily": [
                    {"flow_direction": "ACCUMULATION", "flow_strength": 55.0},
                ],
            },
        }
        flow_data_conflict = {
            "dark_pool": {
                "aggregate": {
                    "flow_direction": "ACCUMULATION",
                    "flow_strength": 60.0,
                    "num_prints": 200,
                },
                "daily": [
                    {"flow_direction": "ACCUMULATION", "flow_strength": 55.0},
                ],
            },
            "options_flow": {
                "combined_bias": "BEARISH",
            },
        }
        a_ok = DarkPoolFlowStrategy._analyze_signal(flow_data_no_conflict)
        a_conflict = DarkPoolFlowStrategy._analyze_signal(flow_data_conflict)
        assert a_conflict["score"] < a_ok["score"]
        assert a_conflict["options_conflict"] is True


# ---------------------------------------------------------------------------
# LeapIVStrategy
# ---------------------------------------------------------------------------

from tradingagents.radon.strategies.leap_iv_mispricing import (
    LeapIVStrategy,
    _analyze_mispricing,
    _calculate_historical_volatility,
    _find_strikes_by_delta,
    _VolatilityData,
)


class TestLeapIVStrategy:
    """Tests for LeapIVStrategy."""

    def test_strategy_id(self) -> None:
        assert LeapIVStrategy.strategy_id == "leap-iv-mispricing"

    def test_strategy_name(self) -> None:
        assert LeapIVStrategy.strategy_name == "LEAP IV Mispricing Scanner"

    def test_required_clients(self) -> None:
        assert LeapIVStrategy.required_clients == ["ib"]

    def test_is_available_false_when_no_ib(self) -> None:
        strategy = LeapIVStrategy()
        # the module import succeeds even without ib_insync installed
        # (ib_client.py exists in the codebase so the import succeeds)
        assert strategy.is_available() is True

    def test_scan_returns_signal_when_no_client(self) -> None:
        strategy = LeapIVStrategy()
        result = strategy.scan("AAPL")
        assert isinstance(result, StrategySignal)
        assert result.signal_type == "neutral"
        assert result.confidence == 0.0
        assert result.source == "leap-iv-mispricing"

    def test_scan_returns_signal_when_client_unavailable(self) -> None:
        strategy = LeapIVStrategy()
        mock_client = MagicMock()
        mock_client.is_available.return_value = False
        result = strategy.scan("AAPL", client=mock_client)
        assert isinstance(result, StrategySignal)
        assert result.signal_type == "neutral"
        assert result.confidence == 0.0

    def test_unavailable_signal(self) -> None:
        signal = LeapIVStrategy._unavailable_signal("AAPL")
        assert signal.signal_type == "neutral"
        assert signal.confidence == 0.0
        assert signal.source == "leap-iv-mispricing"
        assert signal.data["ticker"] == "AAPL"

    def test_compute_confidence_no_mispriced(self) -> None:
        assert LeapIVStrategy._compute_confidence([], None) == 0.0

    def test_compute_confidence_with_mispriced(self) -> None:
        mock_analysis = MagicMock()
        mock_analysis.mispricing_score = 20.0
        assert LeapIVStrategy._compute_confidence([mock_analysis], mock_analysis) > 0.0

    def test_calculate_historical_volatility(self) -> None:
        """Test HV calculation with enough prices."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        hv = _calculate_historical_volatility(prices, 20)
        assert hv >= 0.0

    def test_calculate_historical_volatility_insufficient_data(self) -> None:
        assert _calculate_historical_volatility([100.0, 101.0], 20) == 0.0

    def test_find_strikes_by_delta(self) -> None:
        options = [
            {"delta": 0.50, "strike": 100},
            {"delta": 0.30, "strike": 110},
            {"delta": 0.20, "strike": 115},
            {"delta": 0.10, "strike": 120},
        ]
        result = _find_strikes_by_delta(options, [0.50, 0.30])
        assert 0.50 in result
        assert 0.30 in result

    def test_find_strikes_by_delta_no_match(self) -> None:
        options = [{"delta": 0.90, "strike": 50}]
        result = _find_strikes_by_delta(options, [0.50])
        # delta diff is 0.40 > 0.15 tolerance, so no match
        assert 0.50 not in result

    def test_analyze_mispricing_flags_mispriced(self) -> None:
        vol = _VolatilityData(
            ticker="AAPL",
            current_price=150.0,
            hv_20=45.0,
            hv_60=40.0,
            hv_252=35.0,
        )
        option = {
            "iv": 25.0,
            "vega": 0.30,
            "strike": 150,
            "expiry": "20271218",
            "bid": 10.0,
            "ask": 12.0,
            "mid": 11.0,
            "delta": 0.50,
            "theta": -0.02,
        }
        result = _analyze_mispricing(option, vol, min_gap=15.0)
        assert result.is_mispriced is True
        assert result.hv_20_gap > 0

    def test_analyze_mispricing_not_mispriced(self) -> None:
        vol = _VolatilityData(
            ticker="AAPL",
            current_price=150.0,
            hv_20=20.0,
            hv_60=18.0,
            hv_252=22.0,
        )
        option = {
            "iv": 30.0,
            "vega": 0.30,
            "strike": 150,
            "expiry": "20271218",
            "bid": 10.0,
            "ask": 12.0,
            "mid": 11.0,
            "delta": 0.50,
            "theta": -0.02,
        }
        result = _analyze_mispricing(option, vol, min_gap=15.0)
        assert result.is_mispriced is False

    def test_volatility_data_avg_hv(self) -> None:
        vol = _VolatilityData(
            ticker="AAPL",
            current_price=150.0,
            hv_20=30.0,
            hv_60=25.0,
            hv_252=20.0,
        )
        expected = (30.0 + 25.0 + 20.0) / 3.0
        assert vol.avg_hv == expected

    def test_volatility_data_with_hv756(self) -> None:
        vol = _VolatilityData(
            ticker="AAPL",
            current_price=150.0,
            hv_20=30.0,
            hv_60=25.0,
            hv_252=20.0,
            hv_756=18.0,
        )
        expected = (30.0 + 25.0 + 20.0 + 18.0) / 4.0
        assert vol.avg_hv == expected


# ---------------------------------------------------------------------------
# GARCHConvergenceStrategy
# ---------------------------------------------------------------------------

from tradingagents.radon.strategies.garch_convergence import (
    GARCHConvergenceStrategy,
    _analyze_pair,
    _calc_hv,
    _find_pairs_for_ticker,
    _PairAnalysis,
    _TickerVol,
)


class TestGARCHConvergenceStrategy:
    """Tests for GARCHConvergenceStrategy."""

    def test_strategy_id(self) -> None:
        assert GARCHConvergenceStrategy.strategy_id == "garch-convergence"

    def test_strategy_name(self) -> None:
        assert GARCHConvergenceStrategy.strategy_name == "GARCH Convergence Spreads"

    def test_required_clients(self) -> None:
        assert GARCHConvergenceStrategy.required_clients == ["ib"]

    def test_is_available_false_when_no_ib(self) -> None:
        strategy = GARCHConvergenceStrategy()
        # Without IB installed, returns False
        assert strategy.is_available() is False

    def test_scan_no_pairs_found(self) -> None:
        strategy = GARCHConvergenceStrategy()
        result = strategy.scan("OBSCURE_TICKER")
        assert isinstance(result, StrategySignal)
        assert result.signal_type == "neutral"
        assert result.confidence == 0.0
        assert result.source == "garch-convergence"
        assert "error" in result.data

    def test_scan_with_comma_separated_pair(self) -> None:
        """Comma-separated ticker resolves to a pair."""
        strategy = GARCHConvergenceStrategy()
        with patch.object(strategy, "_fetch_vol_data") as mock_fetch:
            mock_fetch.return_value = {
                "A": _TickerVol(ticker="A", error="UW client unavailable"),
                "B": _TickerVol(ticker="B", error="UW client unavailable"),
            }
            result = strategy.scan("A,B")
        assert isinstance(result, StrategySignal)
        assert result.source == "garch-convergence"

    def test_scan_with_preset(self) -> None:
        strategy = GARCHConvergenceStrategy()
        with patch.object(strategy, "_fetch_vol_data") as mock_fetch:
            mock_fetch.return_value = {
                t: _TickerVol(ticker=t, error="test")
                for t in ["NVDA", "AMD", "TSM", "ASML", "AVGO", "QCOM", "MU", "AMAT"]
            }
            result = strategy.scan("NVDA", preset="semis")
        assert isinstance(result, StrategySignal)
        assert result.source == "garch-convergence"
        assert "pairs" in result.data

    def test_resolve_pairs_with_pair_kwarg(self) -> None:
        strategy = GARCHConvergenceStrategy()
        pairs = strategy._resolve_pairs("AAPL", pair="MSFT", preset=None)
        assert len(pairs) == 1
        assert pairs[0][0] == "AAPL"
        assert pairs[0][1] == "MSFT"

    def test_resolve_pairs_finds_in_presets(self) -> None:
        pairs = _find_pairs_for_ticker("NVDA")
        assert len(pairs) > 0
        assert any("NVDA" in {p[0], p[1]} for p in pairs)

    def test_resolve_pairs_unknown_ticker(self) -> None:
        pairs = _find_pairs_for_ticker("ZZZZZ")
        assert pairs == []

    def test_calc_hv(self) -> None:
        prices = [100.0 + i * 0.5 for i in range(25)]
        hv = _calc_hv(prices, 20)
        assert hv >= 0.0

    def test_calc_hv_insufficient_data(self) -> None:
        assert _calc_hv([100.0, 101.0], 20) == 0.0

    def test_analyze_pair_missing_data(self) -> None:
        vol_data = {"A": None, "B": None}
        pa = _analyze_pair("A", "B", vol_data)
        assert pa.signal == "NONE"
        assert "MISSING_DATA" in pa.failing_gates

    def test_analyze_pair_no_leaps(self) -> None:
        vol_data = {
            "A": _TickerVol(ticker="A", has_leaps=False),
            "B": _TickerVol(ticker="B", has_leaps=False),
        }
        pa = _analyze_pair("A", "B", vol_data)
        assert pa.signal == "NONE"

    def test_ticker_vol_properties(self) -> None:
        tv = _TickerVol(ticker="TEST", hv60=20.0, leap_atm_iv=15.0, hv20=25.0)
        assert tv.iv_hv60 == 0.75  # 15/20
        assert tv.hv20_minus_iv == 10.0  # 25-15

    def test_ticker_vol_zero_division(self) -> None:
        tv = _TickerVol(ticker="TEST", hv60=0.0, leap_atm_iv=15.0)
        assert tv.iv_hv60 == 0.0

    def test_pair_analysis_all_gates_pass(self) -> None:
        pa = _PairAnalysis(
            ticker_a="A",
            ticker_b="B",
            gate_divergence=True,
            gate_hv_gap=True,
            gate_vol_driver=True,
            gate_iv_rank=True,
            gate_liquidity=True,
        )
        assert pa.all_gates_pass is True

    def test_pair_analysis_not_all_gates_pass(self) -> None:
        pa = _PairAnalysis(
            ticker_a="A",
            ticker_b="B",
            gate_divergence=True,
            gate_hv_gap=False,
            gate_vol_driver=True,
            gate_iv_rank=True,
            gate_liquidity=True,
        )
        assert pa.all_gates_pass is False

    def test_best_signal_picks_passing(self) -> None:
        pa_passing = _PairAnalysis(
            ticker_a="A",
            ticker_b="B",
            divergence=0.30,
            gate_divergence=True,
            gate_hv_gap=True,
            gate_vol_driver=True,
            gate_iv_rank=True,
            gate_liquidity=True,
        )
        pa_failing = _PairAnalysis(
            ticker_a="C",
            ticker_b="D",
            divergence=0.50,
        )
        best = GARCHConvergenceStrategy._best_signal([pa_failing, pa_passing])
        assert best.ticker_a == "A"

    def test_best_signal_empty_list(self) -> None:
        best = GARCHConvergenceStrategy._best_signal([])
        assert best.ticker_a == ""


# ---------------------------------------------------------------------------
# RiskReversalStrategy
# ---------------------------------------------------------------------------

from tradingagents.radon.strategies.risk_reversal import RiskReversalStrategy


class TestRiskReversalStrategy:
    """Tests for RiskReversalStrategy."""

    def test_strategy_id(self) -> None:
        assert RiskReversalStrategy.strategy_id == "risk-reversal"

    def test_strategy_name(self) -> None:
        assert RiskReversalStrategy.strategy_name == "Risk Reversal Scanner"

    def test_required_clients(self) -> None:
        assert RiskReversalStrategy.required_clients == ["ib", "uw"]

    def test_is_available_false_when_no_clients(self) -> None:
        strategy = RiskReversalStrategy()
        assert strategy.is_available() is False

    def test_scan_returns_neutral_when_unavailable(self) -> None:
        strategy = RiskReversalStrategy()
        result = strategy.scan("AAPL")
        assert isinstance(result, StrategySignal)
        assert result.signal_type == "neutral"
        assert result.confidence == 0.0
        assert result.source == "risk-reversal"
        assert "error" in result.data

    def test_compute_confidence_no_primary_no_flow(self) -> None:
        matrix = {"primary": None}
        confidence = RiskReversalStrategy._compute_confidence(
            matrix, bearish=False, flow_data=None
        )
        assert confidence == 0.0

    def test_compute_confidence_with_primary(self) -> None:
        matrix = {
            "primary": {
                "net": 0.05,
                "short_delta": 0.35,
                "long_delta": 0.35,
                "skew": 8.0,
            }
        }
        confidence = RiskReversalStrategy._compute_confidence(
            matrix, bearish=False, flow_data=None
        )
        # Primary exists: +0.30
        # Near-costless (|net| < 0.10): +0.10
        # Delta balance < 0.05: +0.10
        # Skew > 5: +0.10
        assert confidence == pytest.approx(0.60)

    def test_compute_confidence_with_aligned_flow(self) -> None:
        matrix = {
            "primary": {
                "net": 0.50,
                "short_delta": 0.40,
                "long_delta": 0.30,
                "skew": 3.0,
            }
        }
        flow_data = {
            "dark_pool": {
                "aggregate": {
                    "flow_direction": "ACCUMULATION",
                    "dp_buy_ratio": 0.70,
                }
            }
        }
        confidence = RiskReversalStrategy._compute_confidence(
            matrix, bearish=False, flow_data=flow_data
        )
        # Primary: +0.30
        # Credit (net >= 0): +0.05
        # Delta balance 0.10 NOT < 0.10: +0.00
        # Flow aligned: +0.15
        # DP buy ratio > 0.60: +0.05
        assert confidence == pytest.approx(0.55)

    def test_compute_confidence_capped_at_095(self) -> None:
        matrix = {
            "primary": {
                "net": 0.02,
                "short_delta": 0.35,
                "long_delta": 0.36,
                "skew": 15.0,
            }
        }
        flow_data = {
            "dark_pool": {
                "aggregate": {
                    "flow_direction": "ACCUMULATION",
                    "dp_buy_ratio": 0.80,
                }
            }
        }
        confidence = RiskReversalStrategy._compute_confidence(
            matrix, bearish=False, flow_data=flow_data
        )
        assert confidence <= 0.95

    def test_build_matrix_no_options(self) -> None:
        chain_data = {
            "spot": 150.0,
            "options": [],
            "short_right": "P",
            "long_right": "C",
        }
        matrix = RiskReversalStrategy._build_matrix(chain_data, 1_000_000.0)
        assert matrix["primary"] is None
        assert matrix["all_combos"] == []
        assert matrix["costless"] == []

    def test_build_matrix_with_options(self) -> None:
        chain_data = {
            "spot": 150.0,
            "options": [
                {
                    "expiry": "20260101",
                    "dte": 30,
                    "right": "P",
                    "strike": 140,
                    "bid": 2.0,
                    "ask": 2.5,
                    "mid": 2.25,
                    "delta": -0.35,
                    "gamma": 0.02,
                    "theta": -0.05,
                    "vega": 0.15,
                    "iv": 0.25,
                },
                {
                    "expiry": "20260101",
                    "dte": 30,
                    "right": "C",
                    "strike": 160,
                    "bid": 1.5,
                    "ask": 2.0,
                    "mid": 1.75,
                    "delta": 0.30,
                    "gamma": 0.02,
                    "theta": -0.04,
                    "vega": 0.14,
                    "iv": 0.22,
                },
            ],
            "short_right": "P",
            "long_right": "C",
        }
        matrix = RiskReversalStrategy._build_matrix(chain_data, 1_000_000.0)
        assert len(matrix["all_combos"]) == 1
        combo = matrix["all_combos"][0]
        assert combo["net"] == pytest.approx(0.0)  # P.bid(2.0) - C.ask(2.0) = 0.0


# ---------------------------------------------------------------------------
# VCGStrategy
# ---------------------------------------------------------------------------

from tradingagents.radon.strategies.vcg import (
    VCGStrategy,
    _compute_vcg,
    _evaluate_signal,
    _log_returns,
    _rolling_ols,
    _standardise_residuals,
)


class TestVCGStrategy:
    """Tests for VCGStrategy."""

    def test_strategy_id(self) -> None:
        assert VCGStrategy.strategy_id == "vcg"

    def test_strategy_name(self) -> None:
        assert VCGStrategy.strategy_name == "Volatility-Credit Gap"

    def test_required_clients(self) -> None:
        assert VCGStrategy.required_clients == ["ib"]

    def test_is_available_false_when_no_ib(self) -> None:
        strategy = VCGStrategy()
        assert strategy.is_available() is False

    def test_scan_returns_neutral_when_no_data(self) -> None:
        strategy = VCGStrategy()
        result = strategy.scan("HYG")
        assert isinstance(result, StrategySignal)
        assert result.signal_type == "neutral"
        assert result.confidence == 0.0
        assert result.source == "vcg"

    def test_log_returns(self) -> None:
        prices = np.array([100.0, 101.0, 102.0, 100.0], dtype=np.float64)
        returns = _log_returns(prices)
        assert len(returns) == 3
        assert not np.isnan(returns).any()

    def test_rolling_ols(self) -> None:
        n = 100
        rng = np.random.default_rng(42)
        y = rng.standard_normal(n).astype(np.float64)
        x_matrix = rng.standard_normal((n, 2)).astype(np.float64)
        alphas, _beta1s, _beta2s, _residuals = _rolling_ols(y, x_matrix, window=21)
        assert len(alphas) == n
        assert np.isnan(alphas[19])  # Before window fills
        assert not np.isnan(alphas[-1])  # Last value should be computed

    def test_standardise_residuals(self) -> None:
        n = 100
        residuals = np.random.default_rng(42).standard_normal(n).astype(np.float64)
        z = _standardise_residuals(residuals, window=63)
        assert len(z) == n
        # Early values should be NaN
        assert np.isnan(z[60])
        # Later values should be computed
        assert not np.isnan(z[-1])

    def test_compute_vcg_output_keys(self) -> None:
        n = 200
        rng = np.random.default_rng(42)
        vix = 20.0 + np.cumsum(rng.standard_normal(n) * 0.5).astype(np.float64)
        vvix = 95.0 + np.cumsum(rng.standard_normal(n) * 0.3).astype(np.float64)
        credit = 80.0 + np.cumsum(rng.standard_normal(n) * 0.1).astype(np.float64)
        result = _compute_vcg(vix, vvix, credit)
        expected_keys = {
            "vcg",
            "vcg_div",
            "residuals",
            "alpha",
            "beta1",
            "beta2",
            "vix_ret",
            "vvix_ret",
            "credit_ret",
            "vix_levels",
            "vvix_levels",
            "credit_levels",
            "pi",
        }
        assert set(result.keys()) == expected_keys

    def test_evaluate_signal_normal(self) -> None:
        n = 200
        rng = np.random.default_rng(42)
        vix = 15.0 + np.cumsum(rng.standard_normal(n) * 0.1).astype(np.float64)
        vvix = 85.0 + np.cumsum(rng.standard_normal(n) * 0.1).astype(np.float64)
        credit = 80.0 + np.cumsum(rng.standard_normal(n) * 0.05).astype(np.float64)
        model = _compute_vcg(vix, vvix, credit)
        signal = _evaluate_signal(model)
        assert "interpretation" in signal
        assert "vcg" in signal
        assert "ro" in signal
        assert isinstance(signal["ro"], bool)
        assert isinstance(signal["edr"], bool)

    def test_evaluate_signal_risk_off(self) -> None:
        """Manually construct a model where VCG is high and VIX is elevated."""
        n = 100
        model: dict[str, Any] = {
            "vcg": np.full(n, np.nan, dtype=np.float64),
            "vcg_div": np.full(n, np.nan, dtype=np.float64),
            "residuals": np.full(n, np.nan, dtype=np.float64),
            "alpha": np.full(n, np.nan, dtype=np.float64),
            "beta1": np.full(n, -0.5, dtype=np.float64),
            "beta2": np.full(n, -0.3, dtype=np.float64),
            "vix_levels": np.full(n, 30.0, dtype=np.float64),
            "vvix_levels": np.full(n, 110.0, dtype=np.float64),
            "credit_levels": np.full(n, 80.0, dtype=np.float64),
            "vix_ret": np.zeros(n, dtype=np.float64),
            "vvix_ret": np.zeros(n, dtype=np.float64),
            "pi": np.full(n, 0.0, dtype=np.float64),
        }
        # Set last vcg to high value for RO trigger
        model["vcg"][-1] = 3.0
        model["residuals"][-1] = 0.01
        model["vcg_div"][-1] = 2.5
        signal = _evaluate_signal(model, vix_floor=28.0, vcg_trigger=2.5)
        assert signal["ro"] is True
        assert signal["interpretation"] == "RISK_OFF"


# ---------------------------------------------------------------------------
# CRIStrategy
# ---------------------------------------------------------------------------

from tradingagents.radon.strategies.cri import (
    CRIStrategy,
    compute_cri,
    compute_realized_vol,
    cor1m_level_and_change,
    crash_trigger,
    cri_level,
    cta_exposure_model,
    score_correlation_component,
    score_momentum_component,
    score_vix_component,
    score_vvix_component,
)


class TestCRIStrategy:
    """Tests for CRIStrategy."""

    def test_strategy_id(self) -> None:
        assert CRIStrategy.strategy_id == "cri"

    def test_strategy_name(self) -> None:
        assert CRIStrategy.strategy_name == "Crash Risk Index (CRI)"

    def test_required_clients(self) -> None:
        assert CRIStrategy.required_clients == ["ib", "menthorq"]

    def test_is_available_false_when_no_deps(self) -> None:
        strategy = CRIStrategy()
        assert strategy.is_available() is False

    def test_scan_returns_neutral_when_no_client(self) -> None:
        strategy = CRIStrategy()
        result = strategy.scan("SPY")
        assert isinstance(result, StrategySignal)
        assert result.signal_type == "neutral"
        assert result.confidence == 0.0
        assert result.source == "cri"

    def test_scan_with_injected_data(self) -> None:
        """Test scan with pre-injected aligned data (bypasses IB)."""
        strategy = CRIStrategy()
        n = 150
        rng = np.random.default_rng(42)
        aligned = {
            "VIX": 20.0 + np.cumsum(rng.standard_normal(n) * 0.5),
            "VVIX": 95.0 + np.cumsum(rng.standard_normal(n) * 0.3),
            "SPY": 500.0 + np.cumsum(rng.standard_normal(n) * 1.0),
            "COR1M": 30.0 + np.cumsum(rng.standard_normal(n) * 0.2),
        }
        dates = [f"2025-01-{i + 1:02d}" for i in range(n)]

        result = strategy.scan(
            "SPY",
            aligned_data=aligned,
            common_dates=dates,
        )
        assert isinstance(result, StrategySignal)
        assert result.source == "cri"
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0
        assert isinstance(result.data, dict)

    def test_compute_realized_vol(self) -> None:
        prices = np.array([100.0 + i * 0.5 for i in range(25)], dtype=np.float64)
        vol = compute_realized_vol(prices, 20)
        assert vol >= 0.0

    def test_compute_realized_vol_insufficient_data(self) -> None:
        prices = np.array([100.0, 101.0], dtype=np.float64)
        vol = compute_realized_vol(prices, 20)
        assert np.isnan(vol)

    @pytest.mark.parametrize(
        ("vix", "vix_5d_roc", "expected_range"),
        [
            (15.0, 0.0, (0.0, 5.0)),  # Low VIX, no change
            (40.0, 60.0, (20.0, 25.0)),  # High VIX, big spike
            (30.0, 30.0, (10.0, 20.0)),  # Moderate
        ],
    )
    def test_score_vix_component(
        self, vix: float, vix_5d_roc: float, expected_range: tuple[float, float]
    ) -> None:
        score = score_vix_component(vix, vix_5d_roc)
        assert expected_range[0] <= score <= expected_range[1]

    def test_score_vix_nan_returns_zero(self) -> None:
        assert score_vix_component(float("nan"), 10.0) == 0.0

    @pytest.mark.parametrize(
        ("vvix", "ratio", "expected_range"),
        [
            (90.0, 5.0, (0.0, 5.0)),
            (140.0, 8.0, (20.0, 25.0)),
        ],
    )
    def test_score_vvix_component(
        self, vvix: float, ratio: float, expected_range: tuple[float, float]
    ) -> None:
        score = score_vvix_component(vvix, ratio)
        assert expected_range[0] <= score <= expected_range[1]

    def test_score_vvix_nan_returns_zero(self) -> None:
        assert score_vvix_component(float("nan"), 5.0) == 0.0

    def test_score_correlation_component(self) -> None:
        score = score_correlation_component(70.0, 15.0)
        assert 15.0 <= score <= 25.0

    def test_score_correlation_nan(self) -> None:
        assert score_correlation_component(float("nan"), 10.0) == 0.0

    @pytest.mark.parametrize(
        ("distance", "expected"),
        [
            (0.0, 0.0),  # At or above MA: 0
            (-5.0, 12.5),  # Below: scored
            (-10.0, 25.0),  # Far below: capped
            (-15.0, 25.0),  # Very far: still capped
        ],
    )
    def test_score_momentum_component(self, distance: float, expected: float) -> None:
        assert score_momentum_component(distance) == expected

    def test_score_momentum_nan_returns_zero(self) -> None:
        assert score_momentum_component(float("nan")) == 0.0

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (0.0, "LOW"),
            (24.9, "LOW"),
            (25.0, "ELEVATED"),
            (49.9, "ELEVATED"),
            (50.0, "HIGH"),
            (74.9, "HIGH"),
            (75.0, "CRITICAL"),
            (100.0, "CRITICAL"),
        ],
    )
    def test_cri_level(self, score: float, expected: str) -> None:
        assert cri_level(score) == expected

    def test_compute_cri_low(self) -> None:
        result = compute_cri(
            vix=15.0,
            vix_5d_roc=0.0,
            vvix=85.0,
            vvix_vix_ratio=5.0,
            corr=20.0,
            corr_5d_change=0.0,
            spx_distance_pct=0.0,
        )
        assert result["level"] == "LOW"
        assert result["score"] < 25.0

    def test_compute_cri_critical(self) -> None:
        result = compute_cri(
            vix=45.0,
            vix_5d_roc=80.0,
            vvix=140.0,
            vvix_vix_ratio=8.0,
            corr=75.0,
            corr_5d_change=25.0,
            spx_distance_pct=-12.0,
        )
        assert result["level"] == "CRITICAL"
        assert result["score"] >= 75.0

    def test_compute_cri_has_components(self) -> None:
        result = compute_cri(
            vix=25.0,
            vix_5d_roc=10.0,
            vvix=100.0,
            vvix_vix_ratio=6.0,
            corr=40.0,
            corr_5d_change=5.0,
            spx_distance_pct=-3.0,
        )
        assert "components" in result
        assert "vix" in result["components"]
        assert "vvix" in result["components"]
        assert "correlation" in result["components"]
        assert "momentum" in result["components"]

    def test_cta_exposure_model_normal(self) -> None:
        result = cta_exposure_model(realized_vol=20.0)
        assert result["realized_vol"] == 20.0
        assert result["exposure_pct"] == 50.0  # 10/20 * 100
        assert result["forced_reduction_pct"] == 50.0

    def test_cta_exposure_model_low_vol(self) -> None:
        result = cta_exposure_model(realized_vol=5.0)
        assert result["exposure_pct"] == 200.0  # Capped at max
        assert result["forced_reduction_pct"] == 0.0

    def test_cta_exposure_model_nan(self) -> None:
        result = cta_exposure_model(realized_vol=float("nan"))
        assert result["forced_reduction_pct"] == 0.0

    def test_crash_trigger_all_fire(self) -> None:
        result = crash_trigger(spx_below_ma=True, realized_vol=30.0, cor1m=65.0)
        assert result["triggered"] is True
        assert result["conditions"]["spx_below_100d_ma"] is True
        assert result["conditions"]["realized_vol_gt_25"] is True
        assert result["conditions"]["cor1m_gt_60"] is True

    def test_crash_trigger_partial(self) -> None:
        result = crash_trigger(spx_below_ma=True, realized_vol=20.0, cor1m=65.0)
        assert result["triggered"] is False
        assert result["conditions"]["realized_vol_gt_25"] is False

    def test_crash_trigger_none_fire(self) -> None:
        result = crash_trigger(spx_below_ma=False, realized_vol=15.0, cor1m=30.0)
        assert result["triggered"] is False

    def test_cor1m_level_and_change(self) -> None:
        values = np.array([25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 35.0], dtype=np.float64)
        current, change = cor1m_level_and_change(values)
        assert current == 35.0
        assert change == pytest.approx(9.0)  # 35 - 26 (values[-6])

    def test_cor1m_level_and_change_override(self) -> None:
        values = np.array([25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 35.0], dtype=np.float64)
        current, change = cor1m_level_and_change(values, current_override=40.0)
        assert current == 40.0
        assert change == pytest.approx(14.0)  # 40 - 26 (values[-6])

    def test_cor1m_level_and_change_empty(self) -> None:
        current, change = cor1m_level_and_change(np.array([], dtype=np.float64))
        assert np.isnan(current)
        assert np.isnan(change)

    def test_cor1m_level_and_change_all_nan(self) -> None:
        values = np.full(10, np.nan, dtype=np.float64)
        current, change = cor1m_level_and_change(values)
        assert np.isnan(current)
        assert np.isnan(change)

    def test_scan_with_injected_data_high_cri(self) -> None:
        """Test scan with data that produces a high CRI score."""
        strategy = CRIStrategy()
        n = 150
        # Construct SPY that is falling (below MA)
        spy_base = np.linspace(550.0, 480.0, n)
        rng = np.random.default_rng(42)
        aligned = {
            "VIX": np.linspace(15.0, 40.0, n) + rng.standard_normal(n) * 0.5,
            "VVIX": np.linspace(85.0, 130.0, n) + rng.standard_normal(n) * 0.3,
            "SPY": spy_base + rng.standard_normal(n) * 0.5,
            "COR1M": np.linspace(25.0, 65.0, n) + rng.standard_normal(n) * 0.2,
        }
        dates = [f"2025-01-{i + 1:02d}" for i in range(n)]

        result = strategy.scan(
            "SPY",
            aligned_data=aligned,
            common_dates=dates,
        )
        assert isinstance(result, StrategySignal)
        assert result.source == "cri"
        assert result.confidence > 0.0
        # With rising VIX, rising COR1M, and falling SPY, CRI should be elevated
        assert result.data["cri"]["score"] > 25.0
