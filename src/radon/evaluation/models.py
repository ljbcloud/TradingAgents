from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TradeDecision(StrEnum):
    TRADE = "TRADE"
    NO_TRADE = "NO_TRADE"
    PENDING = "PENDING"


class ValidationStatus(StrEnum):
    PASS = "PASS"  # nosec B105  # noqa: S105
    FAIL = "FAIL"
    SKIP = "SKIP"
    PENDING = "PENDING"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class MilestoneResult:
    """Outcome of a single evaluation milestone."""

    milestone: str
    passed: bool
    data: dict = field(default_factory=dict)
    reason: str = ""


@dataclass
class EvaluationResult:
    """Aggregated result of a full ticker evaluation."""

    ticker: str
    status: ValidationStatus = field(default=ValidationStatus.PENDING)
    milestones: list[MilestoneResult] = field(default_factory=list)
    gates: dict = field(default_factory=dict)
    decision: TradeDecision = field(default=TradeDecision.PENDING)
    summary: str = ""


__all__ = [
    "EvaluationResult",
    "MilestoneResult",
    "TradeDecision",
    "ValidationStatus",
]
