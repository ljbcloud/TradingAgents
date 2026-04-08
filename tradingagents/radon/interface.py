"""Public interface for the Radon evaluation subsystem.

This is the ONLY file that graph / agent code should import from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tradingagents.radon.evaluation.models import EvaluationResult


def is_radon_available() -> bool:
    """Return True when the Radon evaluator can be instantiated."""
    try:
        from tradingagents.radon.evaluation.evaluator import (  # noqa: F401
            RadonEvaluator,
        )
    except ImportError:
        return False
    return True


def _get_validation_status_unavailable() -> str:
    """Resolve the UNAVAILABLE status string safely.

    Tries the models enum first; falls back to a plain string when the
    evaluation models are not yet importable (e.g. parallel build).
    """
    try:
        from tradingagents.radon.evaluation.models import ValidationStatus

        return ValidationStatus.UNAVAILABLE
    except Exception:
        return "UNAVAILABLE"


def validate_trade(state: dict) -> dict:
    """Entry point for a graph node.

    Accepts a LangGraph state dict, runs Radon evaluation when possible,
    and returns the updated state with ``radon_validation_result`` and
    ``radon_validation_details`` keys.
    """
    unavailable = _get_validation_status_unavailable()

    ticker: str = state.get("company_of_interest", "")
    asset_type: str = state.get("asset_type", "stock")
    final_decision: str = state.get("final_trade_decision", "")

    if not is_radon_available():
        return {
            **state,
            "radon_validation_result": unavailable,
            "radon_validation_details": (
                "Radon validation skipped — optional dependencies not installed"
            ),
        }

    try:
        from tradingagents.radon.evaluation.evaluator import RadonEvaluator

        evaluator = RadonEvaluator()
        result: EvaluationResult = evaluator.evaluate(
            ticker=ticker,
            asset_type=asset_type,
            final_decision=final_decision,
        )
        return {
            **state,
            "radon_validation_result": result.status,
            "radon_validation_details": get_validation_summary(result),
        }
    except Exception as exc:
        return {
            **state,
            "radon_validation_result": unavailable,
            "radon_validation_details": f"Radon evaluation failed: {exc}",
        }


def get_validation_summary(result: EvaluationResult) -> str:
    """Format an EvaluationResult into a human-readable summary string."""
    lines: list[str] = [
        f"Ticker: {result.ticker}",
        f"Status: {result.status}",
        f"Decision: {result.decision}",
    ]

    if result.summary:
        lines.append(f"Summary: {result.summary}")

    passed = sum(1 for m in result.milestones if m.passed)
    total = len(result.milestones)
    lines.append(f"Milestones: {passed}/{total} passed")

    for m in result.milestones:
        status_icon = "✓" if m.passed else "✗"
        lines.append(f"  {status_icon} {m.milestone}: {m.reason}")

    return "\n".join(lines)


__all__ = [
    "get_validation_summary",
    "is_radon_available",
    "validate_trade",
]
