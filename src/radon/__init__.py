"""Radon evaluation subsystem — lazy imports keep the package loadable
without optional dependencies."""

from __future__ import annotations


def __getattr__(name: str):
    if name == "RadonEvaluator":
        from radon.evaluation.evaluator import RadonEvaluator

        return RadonEvaluator
    if name == "validate_trade":
        from radon.interface import validate_trade

        return validate_trade
    if name == "is_radon_available":
        from radon.interface import is_radon_available

        return is_radon_available
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [  # noqa: F822
    "RadonEvaluator",
    "is_radon_available",
    "validate_trade",
]
