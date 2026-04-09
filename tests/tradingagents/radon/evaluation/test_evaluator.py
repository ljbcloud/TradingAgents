"""Tests for RadonEvaluator — 11-milestone evaluation pipeline.

Covers instantiation, crypto passthrough, client unavailability, parallel
milestone execution, early-exit logic, determine_edge() gates, Kelly sizing,
and partial client availability.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tradingagents.radon.evaluation.evaluator import RadonEvaluator
from tradingagents.radon.evaluation.models import (
    EvaluationResult,
    MilestoneResult,
    TradeDecision,
    ValidationStatus,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def evaluator() -> RadonEvaluator:
    """Return a default RadonEvaluator instance."""
    return RadonEvaluator()


@pytest.fixture
def evaluator_custom() -> RadonEvaluator:
    """Return a RadonEvaluator with custom config."""
    return RadonEvaluator(
        config={
            "skip_ib": True,
            "flow_days": 3,
            "bankroll": 500_000,
            "min_flow_strength": 40.0,
            "min_sustained_days": 2,
            "min_risk_reward": 1.5,
            "kelly_fraction": 0.15,
        }
    )


def _make_passing_milestone(
    milestone: str, reason: str = "ok", data: dict | None = None
) -> MilestoneResult:
    """Helper to build a passing MilestoneResult."""
    return MilestoneResult(
        milestone=milestone, passed=True, reason=reason, data=data or {}
    )


def _make_failing_milestone(milestone: str, reason: str = "failed") -> MilestoneResult:
    """Helper to build a failing MilestoneResult."""
    return MilestoneResult(milestone=milestone, passed=False, reason=reason)


def _edge_passing_flow(
    direction: str = "ACCUMULATION",
    strength: float = 60.0,
    daily: list[dict] | None = None,
) -> dict:
    """Build a flow dict that passes determine_edge() by default."""
    if daily is None:
        daily = [
            {"flow_direction": direction, "flow_strength": strength} for _ in range(5)
        ]
    return {
        "dark_pool": {
            "aggregate": {
                "flow_direction": direction,
                "flow_strength": strength,
                "dp_buy_ratio": 0.8,
                "num_prints": 100,
            },
            "daily": daily,
        }
    }


# ---------------------------------------------------------------------------
# 1. Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    """Verify RadonEvaluator() creation and default attributes."""

    def test_creates_instance(self, evaluator: RadonEvaluator) -> None:
        assert isinstance(evaluator, RadonEvaluator)

    def test_milestone_names_length(self, evaluator: RadonEvaluator) -> None:
        names = evaluator.milestone_names
        assert len(names) == 11

    def test_milestone_names_order(self, evaluator: RadonEvaluator) -> None:
        expected = [
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
        assert evaluator.milestone_names == expected

    def test_default_config_values(self, evaluator: RadonEvaluator) -> None:
        assert evaluator.skip_ib is False
        assert evaluator.flow_days == 5
        assert evaluator.bankroll == 1_200_000
        assert evaluator.min_flow_strength == pytest.approx(50.0)
        assert evaluator.min_sustained_days == 3
        assert evaluator.min_risk_reward == pytest.approx(2.0)
        assert evaluator.kelly_fraction == pytest.approx(0.25)

    def test_custom_config_values(self, evaluator_custom: RadonEvaluator) -> None:
        assert evaluator_custom.skip_ib is True
        assert evaluator_custom.flow_days == 3
        assert evaluator_custom.bankroll == 500_000
        assert evaluator_custom.min_flow_strength == pytest.approx(40.0)
        assert evaluator_custom.min_sustained_days == 2
        assert evaluator_custom.min_risk_reward == pytest.approx(1.5)
        assert evaluator_custom.kelly_fraction == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# 2. Crypto passthrough
# ---------------------------------------------------------------------------


class TestCryptoPassthrough:
    """Crypto assets should skip Radon validation entirely."""

    def test_crypto_returns_skip_status(self, evaluator: RadonEvaluator) -> None:
        result = evaluator.evaluate("BTC", "crypto", "BUY")
        assert result.status == ValidationStatus.SKIP

    def test_crypto_returns_pending_decision(self, evaluator: RadonEvaluator) -> None:
        result = evaluator.evaluate("BTC", "crypto", "BUY")
        assert result.decision == TradeDecision.PENDING

    def test_crypto_ticker_uppercased(self, evaluator: RadonEvaluator) -> None:
        result = evaluator.evaluate("eth", "crypto", "SELL")
        assert result.ticker == "ETH"

    def test_crypto_summary(self, evaluator: RadonEvaluator) -> None:
        result = evaluator.evaluate("BTC", "crypto", "BUY")
        assert "Crypto" in result.summary

    def test_crypto_empty_milestones(self, evaluator: RadonEvaluator) -> None:
        result = evaluator.evaluate("BTC", "crypto", "BUY")
        assert result.milestones == []


# ---------------------------------------------------------------------------
# 3. All clients unavailable
# ---------------------------------------------------------------------------


class TestAllClientsUnavailable:
    """When no data clients are reachable, milestones degrade gracefully.

    M1 still passes (ticker accepted with limited verification), so the
    pipeline continues through all milestones.
    """

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m6_kelly_sizing"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m7_final_decision"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_all_clients_unavailable(
        self,
        mock_parallel: MagicMock,
        mock_m7: MagicMock,
        mock_m6: MagicMock,
        mock_m5: MagicMock,
        mock_m4: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        """All data fetches return empty, but M1 still passes (limited verification)."""
        mock_parallel.return_value = {
            "M1": _make_passing_milestone(
                "M1", reason="Ticker accepted (limited verification)"
            ),
            "M1B": _make_passing_milestone(
                "M1B", reason="Seasonality data unavailable"
            ),
            "M1C": _make_passing_milestone("M1C", reason="Analyst ratings unavailable"),
            "M1D": _make_passing_milestone("M1D", reason="News data unavailable"),
            "M2": _make_passing_milestone(
                "M2", reason="Dark pool flow data unavailable"
            ),
            "M3": _make_passing_milestone("M3", reason="Options flow data unavailable"),
            "M3B": _make_passing_milestone("M3B", reason="OI change data unavailable"),
        }

        # M4 determines no edge due to empty flow data → fails
        mock_m4.return_value = _make_failing_milestone(
            "M4", "Aggregate flow direction is NEUTRAL (buy ratio 50.0%)"
        )
        mock_m5.return_value = _make_passing_milestone("M5")
        mock_m6.return_value = _make_passing_milestone("M6")
        mock_m7.return_value = _make_passing_milestone("M7")

        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert result.status == ValidationStatus.FAIL
        assert result.decision == TradeDecision.NO_TRADE


# ---------------------------------------------------------------------------
# 4. Milestone ordering — parallel vs sequential
# ---------------------------------------------------------------------------


class TestMilestoneOrdering:
    """Verify M1-M3B run in parallel and M4-M7 run sequentially."""

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m7_final_decision"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m6_kelly_sizing"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_parallel_milestones_called(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        mock_m5: MagicMock,
        mock_m6: MagicMock,
        mock_m7: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        """_run_parallel_milestones is called exactly once."""
        mock_parallel.return_value = {
            "M1": _make_passing_milestone("M1"),
            "M2": _make_passing_milestone("M2"),
            "M3": _make_passing_milestone("M3"),
        }
        mock_m4.return_value = _make_passing_milestone("M4")
        mock_m5.return_value = _make_passing_milestone("M5")
        mock_m6.return_value = _make_passing_milestone("M6")
        mock_m7.return_value = _make_passing_milestone("M7")

        evaluator.evaluate("AAPL", "stock", "BUY")
        mock_parallel.assert_called_once()

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m7_final_decision"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m6_kelly_sizing"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_sequential_milestones_called_in_order(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        mock_m5: MagicMock,
        mock_m6: MagicMock,
        mock_m7: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        """M4-M7 are each called exactly once and in order."""
        mock_parallel.return_value = {
            "M1": _make_passing_milestone("M1"),
            "M1B": _make_passing_milestone("M1B"),
            "M1C": _make_passing_milestone("M1C"),
            "M1D": _make_passing_milestone("M1D"),
            "M2": _make_passing_milestone("M2"),
            "M3": _make_passing_milestone("M3"),
            "M3B": _make_passing_milestone("M3B"),
        }
        mock_m4.return_value = _make_passing_milestone("M4")
        mock_m5.return_value = _make_passing_milestone("M5")
        mock_m6.return_value = _make_passing_milestone("M6")
        mock_m7.return_value = _make_passing_milestone("M7")

        evaluator.evaluate("AAPL", "stock", "BUY")

        mock_m4.assert_called_once()
        mock_m5.assert_called_once()
        mock_m6.assert_called_once()
        mock_m7.assert_called_once()

    def test_parallel_results_include_all_seven_keys(
        self,
        evaluator: RadonEvaluator,
    ) -> None:
        """All 7 parallel milestone keys are present in results."""
        all_parallel = {
            k: _make_passing_milestone(k)
            for k in ("M1", "M1B", "M1C", "M1D", "M2", "M3", "M3B")
        }

        with (
            patch.object(
                evaluator, "_run_parallel_milestones", return_value=all_parallel
            ),
            patch.object(
                evaluator,
                "_milestone_m4_edge_determination",
                return_value=_make_failing_milestone("M4", "no edge"),
            ),
        ):
            result = evaluator.evaluate("AAPL", "stock", "BUY")

        milestone_ids = {ms.milestone for ms in result.milestones}
        assert "M1" in milestone_ids
        assert "M1B" in milestone_ids
        assert "M1C" in milestone_ids
        assert "M1D" in milestone_ids
        assert "M2" in milestone_ids
        assert "M3" in milestone_ids
        assert "M3B" in milestone_ids
        assert "M4" in milestone_ids


# ---------------------------------------------------------------------------
# 5. Early exit on M1 fail
# ---------------------------------------------------------------------------


class TestEarlyExitM1:
    """When M1 fails, subsequent milestones should not execute."""

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m1_fail_returns_fail_status(
        self, mock_parallel: MagicMock, evaluator: RadonEvaluator
    ) -> None:
        mock_parallel.return_value = {
            "M1": _make_failing_milestone("M1", "Invalid ticker"),
        }
        result = evaluator.evaluate("ZZZZ", "stock", "BUY")
        assert result.status == ValidationStatus.FAIL

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m1_fail_returns_no_trade(
        self, mock_parallel: MagicMock, evaluator: RadonEvaluator
    ) -> None:
        mock_parallel.return_value = {
            "M1": _make_failing_milestone("M1", "Invalid ticker"),
        }
        result = evaluator.evaluate("ZZZZ", "stock", "BUY")
        assert result.decision == TradeDecision.NO_TRADE

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m1_fail_summary_contains_reason(
        self, mock_parallel: MagicMock, evaluator: RadonEvaluator
    ) -> None:
        mock_parallel.return_value = {
            "M1": _make_failing_milestone("M1", "Invalid ticker"),
        }
        result = evaluator.evaluate("ZZZZ", "stock", "BUY")
        assert "M1" in result.summary
        assert "Invalid ticker" in result.summary

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m1_fail_skips_m4(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        """M4 must not be called when M1 fails."""
        mock_parallel.return_value = {
            "M1": _make_failing_milestone("M1", "Invalid ticker"),
        }
        evaluator.evaluate("ZZZZ", "stock", "BUY")
        mock_m4.assert_not_called()

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m1_missing_result_fails(
        self, mock_parallel: MagicMock, evaluator: RadonEvaluator
    ) -> None:
        """If M1 key is missing from parallel results, evaluation fails."""
        mock_parallel.return_value = {}
        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert result.status == ValidationStatus.FAIL
        assert result.decision == TradeDecision.NO_TRADE
        assert "M1" in result.summary

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m1_fail_only_m1_in_milestones(
        self, mock_parallel: MagicMock, evaluator: RadonEvaluator
    ) -> None:
        """When M1 fails, only M1 is in the returned milestones list."""
        mock_parallel.return_value = {
            "M1": _make_failing_milestone("M1", "bad"),
            "M1B": _make_passing_milestone("M1B"),
            "M2": _make_passing_milestone("M2"),
        }
        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert len(result.milestones) == 1
        assert result.milestones[0].milestone == "M1"


# ---------------------------------------------------------------------------
# 6. Early exit on M4 fail
# ---------------------------------------------------------------------------


class TestEarlyExitM4:
    """When M4 fails, M5-M7 should not execute."""

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m4_fail_returns_fail(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        mock_m5: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        mock_parallel.return_value = {
            "M1": _make_passing_milestone("M1"),
        }
        mock_m4.return_value = _make_failing_milestone("M4", "No edge found")
        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert result.status == ValidationStatus.FAIL

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m4_fail_returns_no_trade(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        mock_m5: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        mock_parallel.return_value = {
            "M1": _make_passing_milestone("M1"),
        }
        mock_m4.return_value = _make_failing_milestone("M4", "No edge found")
        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert result.decision == TradeDecision.NO_TRADE

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m4_fail_skips_m5(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        mock_m5: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        """M5 must not be called when M4 fails."""
        mock_parallel.return_value = {"M1": _make_passing_milestone("M1")}
        mock_m4.return_value = _make_failing_milestone("M4", "no edge")
        evaluator.evaluate("AAPL", "stock", "BUY")
        mock_m5.assert_not_called()

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_m4_fail_summary(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        mock_m5: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        mock_parallel.return_value = {"M1": _make_passing_milestone("M1")}
        mock_m4.return_value = _make_failing_milestone("M4", "Weak signal")
        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert "M4" in result.summary
        assert "Weak signal" in result.summary


# ---------------------------------------------------------------------------
# 7. determine_edge() gate logic
# ---------------------------------------------------------------------------


class TestDetermineEdge:
    """Test all gate conditions in determine_edge()."""

    def test_neutral_direction_fails(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow(direction="NEUTRAL")
        result = evaluator.determine_edge(flow=flow)
        assert result["passed"] is False
        assert "NEUTRAL" in result["reason"]

    def test_low_flow_strength_fails(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow(strength=10.0)
        result = evaluator.determine_edge(flow=flow)
        assert result["passed"] is False
        assert "below threshold" in result["reason"]

    def test_signal_priced_in_accumulation(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=60.0)
        price_history = [
            {"close": 100.0},
            {"close": 110.0},  # +10% move
        ]
        result = evaluator.determine_edge(flow=flow, price_history=price_history)
        assert result["passed"] is False
        assert result["signal_priced_in"] is True
        assert "reflected in price" in result["reason"]

    def test_signal_priced_in_distribution(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow(direction="DISTRIBUTION", strength=60.0)
        price_history = [
            {"close": 110.0},
            {"close": 100.0},  # -9% move
        ]
        result = evaluator.determine_edge(flow=flow, price_history=price_history)
        assert result["passed"] is False
        assert result["signal_priced_in"] is True

    def test_signal_not_priced_in_below_threshold(
        self, evaluator: RadonEvaluator
    ) -> None:
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=60.0)
        price_history = [
            {"close": 100.0},
            {"close": 103.0},  # +3% — under 5% threshold
        ]
        result = evaluator.determine_edge(flow=flow, price_history=price_history)
        assert result["signal_priced_in"] is False

    def test_insufficient_sustained_days_fails(self, evaluator: RadonEvaluator) -> None:
        daily = [
            {"flow_direction": "ACCUMULATION", "flow_strength": 55.0},
        ]
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=55.0, daily=daily)
        result = evaluator.determine_edge(flow=flow)
        # sustained=1 < 3 and recent_strength=55 < 70
        assert result["passed"] is False
        assert "Sustained" in result["reason"] or "Signal fading" in result["reason"]

    def test_sustained_days_passes(self, evaluator: RadonEvaluator) -> None:
        daily = [
            {"flow_direction": "ACCUMULATION", "flow_strength": 55.0} for _ in range(4)
        ]
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=55.0, daily=daily)
        result = evaluator.determine_edge(flow=flow)
        assert result["passed"] is True
        assert "consecutive days" in result["reason"]

    def test_alt_recent_strength_passes(self, evaluator: RadonEvaluator) -> None:
        """Alternative: single recent day with strength > alt_recent_strength."""
        daily = [
            {"flow_direction": "ACCUMULATION", "flow_strength": 75.0},
            {"flow_direction": "DISTRIBUTION", "flow_strength": 30.0},
        ]
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=55.0, daily=daily)
        result = evaluator.determine_edge(flow=flow)
        assert result["passed"] is True
        assert "alternative criterion" in result["reason"]

    def test_options_conflict_detected(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=60.0)
        options = {
            "analysis": {
                "combined_bias": "BEARISH",
            }
        }
        result = evaluator.determine_edge(flow=flow, options=options)
        assert result["options_conflict"] is True
        # But it still passes — options_conflict alone doesn't block
        assert result["passed"] is True

    def test_options_no_conflict(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=60.0)
        options = {
            "analysis": {
                "combined_bias": "BULLISH",
            }
        }
        result = evaluator.determine_edge(flow=flow, options=options)
        assert result["options_conflict"] is False

    def test_options_no_data_no_conflict(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=60.0)
        options = {"analysis": {"combined_bias": "NO_DATA"}}
        result = evaluator.determine_edge(flow=flow, options=options)
        assert result["options_conflict"] is False

    def test_no_options_no_conflict(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=60.0)
        result = evaluator.determine_edge(flow=flow, options=None)
        assert result["options_conflict"] is False

    def test_empty_price_history_no_priced_in(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=60.0)
        result = evaluator.determine_edge(flow=flow, price_history=[])
        assert result["signal_priced_in"] is False

    def test_result_contains_all_keys(self, evaluator: RadonEvaluator) -> None:
        flow = _edge_passing_flow()
        result = evaluator.determine_edge(flow=flow)
        expected_keys = {
            "passed",
            "reason",
            "sustained_days",
            "flow_strength",
            "recent_strength",
            "agg_direction",
            "agg_buy_ratio",
            "options_conflict",
            "signal_priced_in",
            "news_sentiment",
            "news_material_count",
        }
        assert set(result.keys()) == expected_keys

    def test_lean_bullish_options_conflict_with_distribution(
        self, evaluator: RadonEvaluator
    ) -> None:
        flow = _edge_passing_flow(direction="DISTRIBUTION", strength=60.0)
        options = {"analysis": {"combined_bias": "LEAN_BULLISH"}}
        result = evaluator.determine_edge(flow=flow, options=options)
        assert result["options_conflict"] is True

    def test_lean_bearish_options_conflict_with_accumulation(
        self, evaluator: RadonEvaluator
    ) -> None:
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=60.0)
        options = {"analysis": {"combined_bias": "LEAN_BEARISH"}}
        result = evaluator.determine_edge(flow=flow, options=options)
        assert result["options_conflict"] is True

    def test_custom_min_flow_strength(self) -> None:
        ev = RadonEvaluator(config={"min_flow_strength": 80.0})
        flow = _edge_passing_flow(strength=60.0)
        result = ev.determine_edge(flow=flow)
        assert result["passed"] is False
        assert "below threshold" in result["reason"]

    def test_custom_min_sustained_days(self) -> None:
        ev = RadonEvaluator(config={"min_sustained_days": 5})
        daily = [
            {"flow_direction": "ACCUMULATION", "flow_strength": 55.0}
            for _ in range(4)  # 4 < 5
        ]
        flow = _edge_passing_flow(direction="ACCUMULATION", strength=55.0, daily=daily)
        result = ev.determine_edge(flow=flow)
        assert result["passed"] is False


# ---------------------------------------------------------------------------
# 8. EvaluationResult structure
# ---------------------------------------------------------------------------


class TestEvaluationResultStructure:
    """Verify returned EvaluationResult has correct fields."""

    def test_full_pass_result_fields(
        self,
        evaluator: RadonEvaluator,
    ) -> None:
        all_parallel = {
            k: _make_passing_milestone(k)
            for k in ("M1", "M1B", "M1C", "M1D", "M2", "M3", "M3B")
        }
        with (
            patch.object(
                evaluator, "_run_parallel_milestones", return_value=all_parallel
            ),
            patch.object(
                evaluator,
                "_milestone_m4_edge_determination",
                return_value=_make_passing_milestone("M4"),
            ),
            patch.object(
                evaluator,
                "_milestone_m5_structure_proposal",
                return_value=_make_passing_milestone("M5"),
            ),
            patch.object(
                evaluator,
                "_milestone_m6_kelly_sizing",
                return_value=_make_passing_milestone("M6"),
            ),
            patch.object(
                evaluator,
                "_milestone_m7_final_decision",
                return_value=_make_passing_milestone("M7"),
            ),
        ):
            result = evaluator.evaluate("AAPL", "stock", "BUY")

        assert isinstance(result, EvaluationResult)
        assert result.ticker == "AAPL"
        assert result.status == ValidationStatus.PASS
        assert result.decision == TradeDecision.TRADE
        assert result.summary == "All milestones passed"
        assert isinstance(result.milestones, list)
        assert len(result.milestones) == 11
        assert isinstance(result.gates, dict)

    def test_crypto_result_fields(self, evaluator: RadonEvaluator) -> None:
        result = evaluator.evaluate("BTC", "crypto", "BUY")
        assert isinstance(result, EvaluationResult)
        assert result.ticker == "BTC"
        assert result.status == ValidationStatus.SKIP
        assert result.decision == TradeDecision.PENDING
        assert result.milestones == []
        assert result.gates == {}


# ---------------------------------------------------------------------------
# 9. MilestoneResult structure
# ---------------------------------------------------------------------------


class TestMilestoneResultStructure:
    """Each milestone returns a MilestoneResult with expected fields."""

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_milestone_result_fields(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        m1 = MilestoneResult(
            milestone="M1",
            passed=True,
            data={"ticker": "AAPL", "verified": True},
            reason="Ticker verified",
        )
        mock_parallel.return_value = {"M1": m1}
        mock_m4.return_value = _make_failing_milestone("M4", "no edge")

        result = evaluator.evaluate("AAPL", "stock", "BUY")

        ms = result.milestones[0]
        assert isinstance(ms, MilestoneResult)
        assert ms.milestone == "M1"
        assert ms.passed is True
        assert isinstance(ms.data, dict)
        assert ms.reason == "Ticker verified"

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_failed_milestone_result_fields(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        mock_parallel.return_value = {
            "M1": _make_failing_milestone("M1", "bad ticker"),
        }
        result = evaluator.evaluate("BAD", "stock", "BUY")

        ms = result.milestones[0]
        assert ms.milestone == "M1"
        assert ms.passed is False
        assert ms.reason == "bad ticker"


# ---------------------------------------------------------------------------
# 10. Gate aggregation
# ---------------------------------------------------------------------------


class TestGateAggregation:
    """Verify gates dict is returned (even if empty by default)."""

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m7_final_decision"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m6_kelly_sizing"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_gates_dict_exists_on_pass(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        mock_m5: MagicMock,
        mock_m6: MagicMock,
        mock_m7: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        mock_parallel.return_value = {
            "M1": _make_passing_milestone("M1"),
        }
        mock_m4.return_value = _make_passing_milestone("M4")
        mock_m5.return_value = _make_passing_milestone("M5")
        mock_m6.return_value = _make_passing_milestone("M6")
        mock_m7.return_value = _make_passing_milestone("M7")

        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert isinstance(result.gates, dict)

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_gates_dict_exists_on_fail(
        self, mock_parallel: MagicMock, evaluator: RadonEvaluator
    ) -> None:
        mock_parallel.return_value = {
            "M1": _make_failing_milestone("M1"),
        }
        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert isinstance(result.gates, dict)


# ---------------------------------------------------------------------------
# 11. Kelly sizing in M6
# ---------------------------------------------------------------------------


class TestKellySizing:
    """Verify M6 calls fractional_kelly with correct parameters."""

    @patch("tradingagents.radon.utils.kelly.fractional_kelly")
    def test_kelly_called_with_correct_params(self, mock_kelly: MagicMock) -> None:
        """fractional_kelly is called with win_prob, win_amount, loss_amount, fraction."""
        mock_kelly.return_value = 0.05

        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "flow_strength": 60.0,
                "agg_direction": "ACCUMULATION",
            }
        }
        milestones = {
            "M4": _make_passing_milestone("M4", data=m4_data),
            "M5": _make_passing_milestone("M5", data={"estimated_risk_reward": 2.5}),
        }

        evaluator._milestone_m6_kelly_sizing("AAPL", milestones)

        mock_kelly.assert_called_once()
        call_kwargs = mock_kelly.call_args
        assert call_kwargs[1]["win_prob"] == pytest.approx(0.60)
        assert call_kwargs[1]["loss_amount"] == pytest.approx(1.0)
        assert call_kwargs[1]["win_amount"] == pytest.approx(2.5)
        assert call_kwargs[1]["fraction"] == pytest.approx(0.25)

    @patch("tradingagents.radon.utils.kelly.fractional_kelly")
    def test_kelly_high_strength_win_prob(self, mock_kelly: MagicMock) -> None:
        """flow_strength >= 80 → win_prob = 0.65."""
        mock_kelly.return_value = 0.08
        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "flow_strength": 85.0,
                "agg_direction": "ACCUMULATION",
            }
        }
        milestones = {
            "M4": _make_passing_milestone("M4", data=m4_data),
            "M5": _make_passing_milestone("M5", data={"estimated_risk_reward": 3.0}),
        }

        evaluator._milestone_m6_kelly_sizing("AAPL", milestones)

        call_kwargs = mock_kelly.call_args
        assert call_kwargs[1]["win_prob"] == pytest.approx(0.65)

    @patch("tradingagents.radon.utils.kelly.fractional_kelly")
    def test_kelly_custom_fraction(self, mock_kelly: MagicMock) -> None:
        """Custom kelly_fraction config is forwarded."""
        mock_kelly.return_value = 0.03
        evaluator = RadonEvaluator(config={"skip_ib": True, "kelly_fraction": 0.15})
        m4_data = {
            "edge_details": {
                "flow_strength": 55.0,
                "agg_direction": "ACCUMULATION",
            }
        }
        milestones = {
            "M4": _make_passing_milestone("M4", data=m4_data),
            "M5": _make_passing_milestone("M5", data={"estimated_risk_reward": 2.0}),
        }

        evaluator._milestone_m6_kelly_sizing("AAPL", milestones)

        call_kwargs = mock_kelly.call_args
        assert call_kwargs[1]["fraction"] == pytest.approx(0.15)

    @patch("tradingagents.radon.utils.kelly.fractional_kelly")
    def test_kelly_zero_returns_do_not_bet(self, mock_kelly: MagicMock) -> None:
        """When Kelly returns 0, recommendation is DO NOT BET."""
        mock_kelly.return_value = 0.0
        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "flow_strength": 55.0,
                "agg_direction": "ACCUMULATION",
            }
        }
        milestones = {
            "M4": _make_passing_milestone("M4", data=m4_data),
            "M5": _make_passing_milestone("M5", data={"estimated_risk_reward": 2.0}),
        }

        m6 = evaluator._milestone_m6_kelly_sizing("AAPL", milestones)
        assert m6.passed is False
        assert m6.data["recommendation"] == "DO NOT BET"

    @patch("tradingagents.radon.utils.kelly.fractional_kelly")
    def test_kelly_positive_returns_trade(self, mock_kelly: MagicMock) -> None:
        """When Kelly returns > 0, recommendation is TRADE."""
        mock_kelly.return_value = 0.05
        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "flow_strength": 60.0,
                "agg_direction": "ACCUMULATION",
            }
        }
        milestones = {
            "M4": _make_passing_milestone("M4", data=m4_data),
            "M5": _make_passing_milestone("M5", data={"estimated_risk_reward": 2.5}),
        }

        m6 = evaluator._milestone_m6_kelly_sizing("AAPL", milestones)
        assert m6.passed is True
        assert m6.data["recommendation"] == "TRADE"

    @patch("tradingagents.radon.utils.kelly.fractional_kelly")
    def test_kelly_suggested_size_calculation(self, mock_kelly: MagicMock) -> None:
        """suggested_size = bankroll * kelly_fraction."""
        mock_kelly.return_value = 0.04
        evaluator = RadonEvaluator(config={"skip_ib": True, "bankroll": 1_000_000})
        m4_data = {
            "edge_details": {
                "flow_strength": 60.0,
                "agg_direction": "ACCUMULATION",
            }
        }
        milestones = {
            "M4": _make_passing_milestone("M4", data=m4_data),
            "M5": _make_passing_milestone("M5", data={"estimated_risk_reward": 2.5}),
        }

        m6 = evaluator._milestone_m6_kelly_sizing("AAPL", milestones)
        assert m6.data["suggested_size"] == pytest.approx(40_000.0)

    @patch("tradingagents.radon.utils.kelly.fractional_kelly")
    def test_kelly_neutral_direction_fails(self, mock_kelly: MagicMock) -> None:
        """NEUTRAL direction means no edge → M6 fails."""
        mock_kelly.return_value = 0.05
        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "flow_strength": 60.0,
                "agg_direction": "NEUTRAL",
            }
        }
        milestones = {
            "M4": _make_passing_milestone("M4", data=m4_data),
            "M5": _make_passing_milestone("M5", data={"estimated_risk_reward": 2.5}),
        }

        m6 = evaluator._milestone_m6_kelly_sizing("AAPL", milestones)
        assert m6.passed is False

    @patch(
        "tradingagents.radon.utils.kelly.fractional_kelly",
        side_effect=Exception("calc error"),
    )
    def test_kelly_exception_returns_do_not_bet(self, mock_kelly: MagicMock) -> None:
        """When fractional_kelly raises, M6 degrades gracefully."""
        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "flow_strength": 60.0,
                "agg_direction": "ACCUMULATION",
            }
        }
        milestones = {
            "M4": _make_passing_milestone("M4", data=m4_data),
            "M5": _make_passing_milestone("M5", data={"estimated_risk_reward": 2.5}),
        }

        m6 = evaluator._milestone_m6_kelly_sizing("AAPL", milestones)
        assert m6.passed is False
        assert m6.data["recommendation"] == "DO NOT BET"
        assert m6.data["kelly_fraction"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 12. Partial client availability
# ---------------------------------------------------------------------------


class TestPartialClientAvailability:
    """Test with only some clients available."""

    @patch("tradingagents.radon.clients.uw_client.UWClient")
    def test_uw_available_ib_unavailable_m1(self, mock_uw_cls: MagicMock) -> None:
        """M1 verifies ticker via UW when UW is available."""
        mock_uw = MagicMock()
        mock_uw.__enter__ = MagicMock(return_value=mock_uw)
        mock_uw.__exit__ = MagicMock(return_value=False)
        mock_uw.is_available.return_value = True
        mock_uw.get_stock_info.return_value = {
            "data": {"name": "Apple Inc.", "sector": "Tech"}
        }
        mock_uw.get_option_contracts.return_value = {"data": [{"id": 1}]}
        mock_uw_cls.return_value = mock_uw

        evaluator = RadonEvaluator(config={"skip_ib": True})
        result = evaluator._milestone_m1_ticker_validation("AAPL")

        assert result.passed is True
        assert result.data["verified"] is True
        assert result.data["options_available"] is True
        assert result.data["company_name"] == "Apple Inc."

    @patch("tradingagents.radon.clients.uw_client.UWClient")
    def test_uw_unavailable_m1b_still_passes(self, mock_uw_cls: MagicMock) -> None:
        """M1B passes even when UW client raises."""
        mock_uw = MagicMock()
        mock_uw.__enter__ = MagicMock(return_value=mock_uw)
        mock_uw.__exit__ = MagicMock(return_value=False)
        mock_uw.is_available.return_value = False
        mock_uw_cls.return_value = mock_uw

        evaluator = RadonEvaluator()
        result = evaluator._milestone_m1b_seasonality("AAPL")
        assert result.passed is True
        assert result.milestone == "M1B"

    @patch("tradingagents.radon.clients.uw_client.UWClient")
    def test_uw_unavailable_m1c_still_passes(self, mock_uw_cls: MagicMock) -> None:
        """M1C passes even when UW raises."""
        mock_uw = MagicMock()
        mock_uw.__enter__ = MagicMock(return_value=mock_uw)
        mock_uw.__exit__ = MagicMock(return_value=False)
        mock_uw.is_available.side_effect = Exception("connection refused")
        mock_uw_cls.return_value = mock_uw

        evaluator = RadonEvaluator()
        result = evaluator._milestone_m1c_analyst_ratings("AAPL")
        assert result.passed is True
        assert result.milestone == "M1C"

    @patch("tradingagents.radon.clients.uw_client.UWClient")
    def test_uw_unavailable_m1d_still_passes(self, mock_uw_cls: MagicMock) -> None:
        """M1D passes even when UW raises."""
        mock_uw = MagicMock()
        mock_uw.__enter__ = MagicMock(return_value=mock_uw)
        mock_uw.__exit__ = MagicMock(return_value=False)
        mock_uw.is_available.side_effect = Exception("timeout")
        mock_uw_cls.return_value = mock_uw

        evaluator = RadonEvaluator()
        result = evaluator._milestone_m1d_news_catalysts("AAPL")
        assert result.passed is True
        assert result.milestone == "M1D"

    @patch("tradingagents.radon.strategies.dark_pool_flow.DarkPoolFlowStrategy")
    def test_m2_dark_pool_strategy_unavailable(
        self, mock_strategy_cls: MagicMock
    ) -> None:
        """M2 passes even when DarkPoolFlowStrategy raises."""
        mock_strategy = MagicMock()
        mock_strategy.scan.side_effect = Exception("no data")
        mock_strategy_cls.return_value = mock_strategy

        evaluator = RadonEvaluator()
        result = evaluator._milestone_m2_dark_pool_flow("AAPL")
        assert result.passed is True
        assert "unavailable" in result.reason.lower()

    @patch("tradingagents.radon.clients.uw_client.UWClient")
    def test_m3_uw_unavailable_still_passes(self, mock_uw_cls: MagicMock) -> None:
        """M3 passes even when UW raises."""
        mock_uw = MagicMock()
        mock_uw.__enter__ = MagicMock(return_value=mock_uw)
        mock_uw.__exit__ = MagicMock(return_value=False)
        mock_uw.is_available.side_effect = Exception("fail")
        mock_uw_cls.return_value = mock_uw

        evaluator = RadonEvaluator(config={"skip_ib": True})
        result = evaluator._milestone_m3_options_flow("AAPL")
        assert result.passed is True

    @patch("tradingagents.radon.clients.uw_client.UWClient")
    def test_m3b_uw_unavailable_still_passes(self, mock_uw_cls: MagicMock) -> None:
        """M3B passes even when UW raises."""
        mock_uw = MagicMock()
        mock_uw.__enter__ = MagicMock(return_value=mock_uw)
        mock_uw.__exit__ = MagicMock(return_value=False)
        mock_uw.is_available.side_effect = Exception("fail")
        mock_uw_cls.return_value = mock_uw

        evaluator = RadonEvaluator()
        result = evaluator._milestone_m3b_oi_changes("AAPL")
        assert result.passed is True


# ---------------------------------------------------------------------------
# Bonus: _compute_sustained_days helper
# ---------------------------------------------------------------------------


class TestComputeSustainedDays:
    """Test the static _compute_sustained_days helper."""

    def test_empty_daily(self, evaluator: RadonEvaluator) -> None:
        assert evaluator._compute_sustained_days([], "ACCUMULATION") == 0

    def test_all_matching(self, evaluator: RadonEvaluator) -> None:
        daily = [
            {"flow_direction": "ACCUMULATION"},
            {"flow_direction": "ACCUMULATION"},
            {"flow_direction": "ACCUMULATION"},
        ]
        assert evaluator._compute_sustained_days(daily, "ACCUMULATION") == 3

    def test_breaks_on_mismatch(self, evaluator: RadonEvaluator) -> None:
        daily = [
            {"flow_direction": "ACCUMULATION"},
            {"flow_direction": "DISTRIBUTION"},
            {"flow_direction": "ACCUMULATION"},
        ]
        assert evaluator._compute_sustained_days(daily, "ACCUMULATION") == 1

    def test_no_match(self, evaluator: RadonEvaluator) -> None:
        daily = [
            {"flow_direction": "DISTRIBUTION"},
            {"flow_direction": "DISTRIBUTION"},
        ]
        assert evaluator._compute_sustained_days(daily, "ACCUMULATION") == 0


# ---------------------------------------------------------------------------
# Bonus: M5 Structure Proposal edge cases
# ---------------------------------------------------------------------------


class TestM5StructureProposal:
    """Test M5 structure proposal risk/reward logic."""

    def test_neutral_direction_fails(self) -> None:
        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "agg_direction": "NEUTRAL",
                "flow_strength": 80.0,
                "options_conflict": False,
            }
        }
        milestones = {"M4": _make_passing_milestone("M4", data=m4_data)}
        m5 = evaluator._milestone_m5_structure_proposal("AAPL", milestones)
        assert m5.passed is False
        assert "No clear direction" in m5.reason

    def test_low_flow_strength_fails_risk_reward(self) -> None:
        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "agg_direction": "ACCUMULATION",
                "flow_strength": 30.0,
                "options_conflict": False,
            }
        }
        milestones = {"M4": _make_passing_milestone("M4", data=m4_data)}
        m5 = evaluator._milestone_m5_structure_proposal("AAPL", milestones)
        assert m5.passed is False
        assert m5.data["estimated_risk_reward"] < 2.0

    def test_high_flow_strength_meets_risk_reward(self) -> None:
        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "agg_direction": "ACCUMULATION",
                "flow_strength": 90.0,
                "options_conflict": False,
            }
        }
        milestones = {"M4": _make_passing_milestone("M4", data=m4_data)}
        m5 = evaluator._milestone_m5_structure_proposal("AAPL", milestones)
        assert m5.passed is True
        assert m5.data["estimated_risk_reward"] >= 2.0

    def test_options_conflict_reduces_risk_reward(self) -> None:
        evaluator = RadonEvaluator(config={"skip_ib": True})
        m4_data = {
            "edge_details": {
                "agg_direction": "ACCUMULATION",
                "flow_strength": 50.0,
                "options_conflict": True,
            }
        }
        milestones = {"M4": _make_passing_milestone("M4", data=m4_data)}
        m5 = evaluator._milestone_m5_structure_proposal("AAPL", milestones)
        # flow 50 → base 2.0, conflict → 1.5 → below default 2.0
        assert m5.data["estimated_risk_reward"] == pytest.approx(1.5)
        assert m5.passed is False

    def test_no_m4_data_defaults(self) -> None:
        evaluator = RadonEvaluator(config={"skip_ib": True})
        milestones = {}
        m5 = evaluator._milestone_m5_structure_proposal("AAPL", milestones)
        # No M4 → NEUTRAL direction → fails
        assert m5.passed is False


# ---------------------------------------------------------------------------
# Bonus: M7 Final Decision
# ---------------------------------------------------------------------------


class TestM7FinalDecision:
    """Test M7 final decision synthesis."""

    def test_all_passed(self) -> None:
        evaluator = RadonEvaluator(config={"skip_ib": True})
        milestones = {
            "M1": _make_passing_milestone("M1"),
            "M4": _make_passing_milestone("M4"),
        }
        m7 = evaluator._milestone_m7_final_decision("AAPL", "BUY", milestones)
        assert m7.passed is True
        assert "All 2 milestones passed" in m7.reason
        assert m7.data["trade_decision"] == "BUY"

    def test_some_failed(self) -> None:
        evaluator = RadonEvaluator(config={"skip_ib": True})
        milestones = {
            "M1": _make_passing_milestone("M1"),
            "M4": _make_failing_milestone("M4", "no edge"),
        }
        m7 = evaluator._milestone_m7_final_decision("AAPL", "BUY", milestones)
        assert m7.passed is False
        assert "1/2 milestones passed" in m7.reason


# ---------------------------------------------------------------------------
# Gate population in evaluate()
# ---------------------------------------------------------------------------


class TestGatePopulation:
    """Verify result.gates is populated in every return path of evaluate()."""

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m7_final_decision"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m6_kelly_sizing"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_gates_populated_on_full_pass(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        mock_m5: MagicMock,
        mock_m6: MagicMock,
        mock_m7: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        """All 4 gates True when every milestone passes."""
        mock_parallel.return_value = {
            "M1": _make_passing_milestone("M1"),
        }
        mock_m4.return_value = _make_passing_milestone("M4")
        mock_m5.return_value = _make_passing_milestone(
            "M5", data={"estimated_risk_reward": 2.5}
        )
        mock_m6.return_value = _make_passing_milestone("M6")
        mock_m7.return_value = _make_passing_milestone("M7")

        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert result.gates == {
            "convexity": True,
            "edge": True,
            "risk_management": True,
            "no_naked_shorts": True,
        }

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_gates_on_m4_fail(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        """M4 fail → edge=False, convexity/risk_management from milestone state."""
        mock_parallel.return_value = {
            "M1": _make_passing_milestone("M1"),
        }
        mock_m4.return_value = _make_failing_milestone("M4", "no edge")

        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert result.gates["edge"] is False
        assert result.gates["convexity"] is False
        assert result.gates["risk_management"] is False
        assert result.gates["no_naked_shorts"] is False

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m5_structure_proposal"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._milestone_m4_edge_determination"
    )
    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_gates_on_m5_fail(
        self,
        mock_parallel: MagicMock,
        mock_m4: MagicMock,
        mock_m5: MagicMock,
        evaluator: RadonEvaluator,
    ) -> None:
        """M5 fail → convexity=False, edge from M4, no_naked_shorts checked."""
        mock_parallel.return_value = {
            "M1": _make_passing_milestone("M1"),
        }
        mock_m4.return_value = _make_passing_milestone("M4")
        mock_m5.return_value = _make_failing_milestone("M5", "bad structure")

        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert result.gates["convexity"] is False
        assert result.gates["edge"] is True
        assert result.gates["no_naked_shorts"] is True

    @patch(
        "tradingagents.radon.evaluation.evaluator.RadonEvaluator._run_parallel_milestones"
    )
    def test_gates_on_m1_fail(
        self, mock_parallel: MagicMock, evaluator: RadonEvaluator
    ) -> None:
        """M1 fail → all gates False."""
        mock_parallel.return_value = {
            "M1": _make_failing_milestone("M1", "invalid"),
        }
        result = evaluator.evaluate("AAPL", "stock", "BUY")
        assert result.gates == {
            "convexity": False,
            "edge": False,
            "risk_management": False,
            "no_naked_shorts": False,
        }

    def test_no_naked_shorts_buy_always_passes(self) -> None:
        """BUY decisions can never be naked shorts."""
        result = RadonEvaluator._check_no_naked_shorts("BUY", {})
        assert result is True

    def test_no_naked_shorts_sell_without_m5(self) -> None:
        """SELL without M5 in milestones → fails naked shorts check."""
        result = RadonEvaluator._check_no_naked_shorts("SELL", {})
        assert result is False

    def test_no_naked_shorts_sell_with_m5_pass(self) -> None:
        """SELL with M5 passed and estimated_risk_reward data → passes."""
        milestones = {
            "M5": _make_passing_milestone("M5", data={"estimated_risk_reward": 2.5}),
        }
        result = RadonEvaluator._check_no_naked_shorts("SELL", milestones)
        assert result is True

    def test_crypto_passthrough_empty_gates(self) -> None:
        """Crypto evaluate returns gates={} (default)."""
        evaluator = RadonEvaluator()
        result = evaluator.evaluate("BTC", "crypto", "BUY")
        assert result.gates == {}
