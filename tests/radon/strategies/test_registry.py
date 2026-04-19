"""Tests for StrategySignal dataclass, BaseStrategy protocol, and StrategyRegistry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from radon.strategies.base import (
    BaseStrategy,
    StrategyRegistry,
    StrategySignal,
    _load_strategies_metadata,
)

# ---------------------------------------------------------------------------
# StrategySignal tests
# ---------------------------------------------------------------------------


class TestStrategySignal:
    """Tests for the StrategySignal dataclass."""

    def test_create_with_required_fields(self) -> None:
        signal = StrategySignal(signal_type="bullish", confidence=0.8)
        assert signal.signal_type == "bullish"
        assert signal.confidence == 0.8

    def test_default_values(self) -> None:
        signal = StrategySignal(signal_type="neutral", confidence=0.0)
        assert signal.data == {}
        assert signal.source == ""

    def test_create_with_all_fields(self) -> None:
        data = {"score": 65.0, "direction": "ACCUMULATION"}
        signal = StrategySignal(
            signal_type="bullish",
            confidence=0.75,
            data=data,
            source="dark-pool-flow",
        )
        assert signal.signal_type == "bullish"
        assert signal.confidence == 0.75
        assert signal.data == data
        assert signal.source == "dark-pool-flow"

    def test_data_dict_is_independent(self) -> None:
        """Each signal gets its own empty dict by default (no shared mutable)."""
        s1 = StrategySignal(signal_type="neutral", confidence=0.0)
        s2 = StrategySignal(signal_type="neutral", confidence=0.0)
        s1.data["key"] = "value"
        assert "key" not in s2.data

    def test_signal_type_variants(self) -> None:
        for stype in ("bullish", "bearish", "neutral", "error", "strong_bearish"):
            signal = StrategySignal(signal_type=stype, confidence=0.5)
            assert signal.signal_type == stype

    def test_confidence_boundary_values(self) -> None:
        StrategySignal(signal_type="neutral", confidence=0.0)
        StrategySignal(signal_type="neutral", confidence=1.0)
        StrategySignal(signal_type="neutral", confidence=0.5)


# ---------------------------------------------------------------------------
# _load_strategies_metadata tests
# ---------------------------------------------------------------------------


class TestLoadStrategiesMetadata:
    """Tests for the _load_strategies_metadata helper."""

    def test_loads_valid_json(self) -> None:
        metadata = _load_strategies_metadata()
        assert isinstance(metadata, dict)
        # strategies.json has 6 entries
        assert len(metadata) == 6

    def test_keys_are_strategy_ids(self) -> None:
        metadata = _load_strategies_metadata()
        expected_ids = {
            "dark-pool-flow",
            "leap-iv-mispricing",
            "garch-convergence",
            "risk-reversal",
            "vcg",
            "cri",
        }
        assert set(metadata.keys()) == expected_ids

    def test_each_entry_has_name_and_status(self) -> None:
        metadata = _load_strategies_metadata()
        for sid, entry in metadata.items():
            assert "name" in entry, f"Missing 'name' in {sid}"
            assert "status" in entry, f"Missing 'status' in {sid}"

    @patch("radon.strategies.base._STRATEGIES_JSON", Path("/nonexistent"))
    def test_returns_empty_on_missing_file(self) -> None:
        result = _load_strategies_metadata()
        assert result == {}

    @patch(
        "builtins.open",
        side_effect=json.JSONDecodeError("err", "doc", 0),
    )
    def test_returns_empty_on_malformed_json(self, mock_open: Any) -> None:
        # Patch the Path.open used in _load_strategies_metadata
        with patch.object(Path, "open", mock_open):
            result = _load_strategies_metadata()
        assert result == {}


# ---------------------------------------------------------------------------
# StrategyRegistry tests
# ---------------------------------------------------------------------------


# Minimal strategy-like classes for testing (not dataclasses due to mutable defaults)
class FakeStrategy:
    strategy_id = "fake-strategy"
    strategy_name = "Fake Strategy"
    required_clients: list[str] = []

    def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
        return StrategySignal(
            signal_type="neutral", confidence=0.0, source=self.strategy_id
        )

    def is_available(self) -> bool:
        return True


class UnavailableStrategy:
    strategy_id = "unavailable-strategy"
    strategy_name = "Unavailable Strategy"
    required_clients = ["nonexistent"]

    def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
        return StrategySignal(
            signal_type="neutral", confidence=0.0, source=self.strategy_id
        )

    def is_available(self) -> bool:
        return False


class BrokenStrategy:
    strategy_id = "broken-strategy"
    strategy_name = "Broken Strategy"
    required_clients: list[str] = []

    def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
        return StrategySignal(
            signal_type="neutral", confidence=0.0, source=self.strategy_id
        )

    def is_available(self) -> bool:
        msg = "boom"
        raise RuntimeError(msg)


class _NoIdStrategy:
    strategy_name = "No ID"
    required_clients: list[str] = []

    def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
        return StrategySignal(signal_type="neutral", confidence=0.0)

    def is_available(self) -> bool:
        return True


class TestStrategyRegistry:
    """Tests for StrategyRegistry."""

    def test_instantiation(self) -> None:
        registry = StrategyRegistry()
        assert registry.all() == {}

    def test_register_adds_strategy(self) -> None:
        registry = StrategyRegistry()
        registry.register(FakeStrategy)
        assert registry.get("fake-strategy") is FakeStrategy

    def test_get_returns_class_for_registered_id(self) -> None:
        registry = StrategyRegistry()
        registry.register(FakeStrategy)
        result = registry.get("fake-strategy")
        assert result is FakeStrategy

    def test_get_returns_none_for_unknown_id(self) -> None:
        registry = StrategyRegistry()
        assert registry.get("nonexistent") is None

    def test_all_returns_copy(self) -> None:
        registry = StrategyRegistry()
        registry.register(FakeStrategy)
        all_strats = registry.all()
        # Mutating the returned dict should not affect the registry
        all_strats["intruder"] = object
        assert registry.get("intruder") is None

    def test_all_returns_all_registered(self) -> None:
        registry = StrategyRegistry()
        registry.register(FakeStrategy)
        registry.register(UnavailableStrategy)
        all_strats = registry.all()
        assert len(all_strats) == 2
        assert "fake-strategy" in all_strats
        assert "unavailable-strategy" in all_strats

    def test_available_returns_only_available(self) -> None:
        registry = StrategyRegistry()
        registry.register(FakeStrategy)
        registry.register(UnavailableStrategy)
        available = registry.available()
        assert len(available) == 1
        assert available[0] is FakeStrategy

    def test_available_handles_broken_strategy(self) -> None:
        """Strategies whose is_available raises are excluded gracefully."""
        registry = StrategyRegistry()
        registry.register(FakeStrategy)
        registry.register(BrokenStrategy)
        available = registry.available()
        assert len(available) == 1
        assert available[0] is FakeStrategy

    def test_available_empty_when_none_available(self) -> None:
        registry = StrategyRegistry()
        registry.register(UnavailableStrategy)
        assert registry.available() == []

    def test_register_raises_for_missing_strategy_id(self) -> None:
        registry = StrategyRegistry()
        with pytest.raises(
            ValueError, match="Cannot register strategy without strategy_id"
        ):
            registry.register(_NoIdStrategy)

    def test_register_raises_for_empty_strategy_id(self) -> None:
        registry = StrategyRegistry()

        class _EmptyId:
            strategy_id: str = ""

        with pytest.raises(
            ValueError, match="Cannot register strategy without strategy_id"
        ):
            registry.register(_EmptyId)

    def test_duplicate_registration_overwrites(self) -> None:
        """Registering the same id twice silently overwrites."""

        class _StratV1:
            strategy_id = "dup"
            strategy_name = "v1"
            required_clients: list[str] = []

            def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
                return StrategySignal(signal_type="neutral", confidence=0.0)

            def is_available(self) -> bool:
                return True

        class _StratV2:
            strategy_id = "dup"
            strategy_name = "v2"
            required_clients: list[str] = []

            def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
                return StrategySignal(signal_type="neutral", confidence=0.0)

            def is_available(self) -> bool:
                return True

        registry = StrategyRegistry()
        registry.register(_StratV1)
        registry.register(_StratV2)
        assert registry.get("dup").strategy_name == "v2"

    def test_metadata_property(self) -> None:
        registry = StrategyRegistry()
        metadata = registry.metadata
        assert isinstance(metadata, dict)
        assert "dark-pool-flow" in metadata

    def test_metadata_loaded_from_json(self) -> None:
        registry = StrategyRegistry()
        metadata = registry.metadata
        dp = metadata.get("dark-pool-flow")
        assert dp is not None
        assert dp["name"] == "Dark Pool Flow"
        assert dp["status"] == "active"


# ---------------------------------------------------------------------------
# BaseStrategy protocol conformance
# ---------------------------------------------------------------------------


class TestBaseStrategyProtocol:
    """Verify that concrete classes satisfy the BaseStrategy protocol."""

    def test_fake_strategy_satisfies_protocol(self) -> None:
        assert isinstance(FakeStrategy(), BaseStrategy)

    def test_unavailable_strategy_satisfies_protocol(self) -> None:
        assert isinstance(UnavailableStrategy(), BaseStrategy)

    def test_scan_returns_strategy_signal(self) -> None:
        strategy = FakeStrategy()
        result = strategy.scan("AAPL")
        assert isinstance(result, StrategySignal)
        assert result.source == "fake-strategy"

    def test_scan_passes_ticker(self) -> None:
        strategy = FakeStrategy()
        result = strategy.scan("MSFT")
        assert isinstance(result, StrategySignal)
