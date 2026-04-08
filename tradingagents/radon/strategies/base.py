"""Strategy base protocol, signal dataclass, and registry for the radon module.

This module defines the contract for all trading strategies and provides a
simple dict-based registry (following the VENDOR_METHODS pattern from
dataflows/interface.py). Strategies register themselves; the registry does
not auto-discover implementations.

Primary Components:
    StrategySignal: Dataclass representing a strategy scan result.
    BaseStrategy: Protocol defining the strategy interface.
    StrategyRegistry: Dict-based registry keyed by strategy_id.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

# Path to strategy metadata JSON
_STRATEGIES_JSON = Path(__file__).resolve().parent.parent / "data" / "strategies.json"


@dataclass
class StrategySignal:
    """Result of a strategy scan for a single ticker.

    Attributes:
        signal_type: Signal category, e.g. 'bullish', 'bearish', 'neutral'.
        confidence: Signal confidence between 0.0 and 1.0.
        data: Arbitrary strategy-specific payload.
        source: Identifier of the strategy that produced this signal.
    """

    signal_type: str
    confidence: float
    data: dict = field(default_factory=dict)
    source: str = ""


@runtime_checkable
class BaseStrategy(Protocol):
    """Protocol defining the interface every radon strategy must implement.

    Class attributes:
        strategy_id: Unique identifier matching an entry in strategies.json.
        strategy_name: Human-readable name.
        required_clients: List of client identifiers this strategy needs.
    """

    strategy_id: str
    strategy_name: str
    required_clients: list[str]

    def scan(self, ticker: str, **kwargs: object) -> StrategySignal:
        """Run the strategy scan for *ticker* and return a signal.

        Args:
            ticker: Stock ticker symbol, e.g. 'AAPL'.
            **kwargs: Strategy-specific parameters.

        Returns:
            A StrategySignal with the scan result.
        """
        ...

    def is_available(self) -> bool:
        """Return True when all required clients/dependencies are present."""
        ...


def _load_strategies_metadata() -> dict[str, dict]:
    """Load strategy metadata from strategies.json.

    Returns:
        Dict keyed by strategy id, each value being the full metadata record.
        Returns an empty dict if the file is missing or malformed.
    """
    try:
        with _STRATEGIES_JSON.open() as f:
            entries: list[dict] = json.load(f)
        return {entry["id"]: entry for entry in entries}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {}


class StrategyRegistry:
    """Dict-based registry for strategy classes, keyed by strategy_id.

    Follows the simple dict-routing pattern used in
    tradingagents/dataflows/interface.py (VENDOR_METHODS).  Strategies
    register themselves explicitly; there is no metaclass auto-registration.

    Usage::

        registry = StrategyRegistry()
        registry.register(MyStrategy)
        cls = registry.get("my-strategy")
        available = registry.available()
    """

    def __init__(self) -> None:
        self._strategies: dict[str, type] = {}
        self._metadata: dict[str, dict] = _load_strategies_metadata()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, strategy_class: type) -> None:
        """Register a strategy class by its ``strategy_id``.

        Args:
            strategy_class: A class that satisfies the BaseStrategy protocol.

        Raises:
            ValueError: If strategy_id is missing or empty.
        """
        sid: str = getattr(strategy_class, "strategy_id", "")
        if not sid:
            msg = f"Cannot register strategy without strategy_id: {strategy_class}"
            raise ValueError(msg)
        self._strategies[sid] = strategy_class

    def get(self, strategy_id: str) -> type | None:
        """Look up a registered strategy class by id.

        Args:
            strategy_id: The unique strategy identifier.

        Returns:
            The strategy class, or None if not registered.
        """
        return self._strategies.get(strategy_id)

    def all(self) -> dict[str, type]:
        """Return a shallow copy of all registered strategy classes."""
        return dict(self._strategies)

    @staticmethod
    def _check_available(strategy_cls: type) -> bool:
        """Instantiate *strategy_cls* and return its ``is_available()`` result.

        Returns False if instantiation or the check itself raises.
        """
        try:
            return strategy_cls().is_available()
        except Exception:
            return False

    def available(self) -> list[type]:
        """Return only strategies whose ``is_available()`` returns True.

        Instantiates each registered strategy temporarily to check
        availability.  Strategies with no required clients default to
        available.
        """
        return [cls for cls in self._strategies.values() if self._check_available(cls)]

    @property
    def metadata(self) -> dict[str, dict]:
        """Return the loaded strategies.json metadata."""
        return self._metadata
