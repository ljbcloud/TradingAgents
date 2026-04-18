"""Kelly criterion calculator for position sizing."""

from __future__ import annotations

from typing import Any

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

__all__ = ["fractional_kelly", "kelly", "kelly_size_batch"]


def kelly(prob_win: float, odds: float, fraction: float = 0.25) -> dict[str, Any]:
    """Calculate fractional Kelly bet size.

    Args:
        prob_win: Probability of winning (0-1).
        odds: Win/loss odds ratio.
        fraction: Kelly fraction to apply (default 0.25 = quarter Kelly).

    Returns:
        Dict with full_kelly_pct, fractional_kelly_pct, fraction_used,
        edge_exists, and recommendation.
    """
    if odds <= 0:
        return {
            "full_kelly_pct": 0.0,
            "fractional_kelly_pct": 0.0,
            "fraction_used": fraction,
            "edge_exists": False,
            "recommendation": "DO NOT BET",
        }

    q = 1 - prob_win
    full_kelly = prob_win - (q / odds)
    frac_kelly = full_kelly * fraction
    return {
        "full_kelly_pct": round(full_kelly * 100, 2),
        "fractional_kelly_pct": round(frac_kelly * 100, 2),
        "fraction_used": fraction,
        "edge_exists": full_kelly > 0,
        "recommendation": (
            "DO NOT BET"
            if full_kelly <= 0
            else "STRONG"
            if full_kelly > 0.10
            else "MARGINAL"
            if full_kelly > 0.025
            else "WEAK"
        ),
    }


def kelly_size_batch(
    prob_wins: Any,
    odds: Any,
    bankroll: float,
    fraction: float = 0.25,
    max_pct: float = 0.025,
) -> Any:
    """Vectorized Kelly sizing for N candidates simultaneously.

    Returns an array of dollar position sizes, one per candidate.
    Guards: odds <= 0 -> 0, full_kelly <= 0 -> 0, hard cap at bankroll * max_pct.

    Requires numpy.
    """
    if not HAS_NUMPY:
        msg = "numpy is required for kelly_size_batch(). Install it with: pip install numpy"
        raise ImportError(msg)

    if len(prob_wins) == 0:
        return np.array([])

    prob_wins = np.asarray(prob_wins, dtype=np.float64)
    odds = np.asarray(odds, dtype=np.float64)

    q = 1.0 - prob_wins

    # full_kelly = prob_win - q / odds, but guard odds <= 0
    with np.errstate(divide="ignore", invalid="ignore"):
        full_kelly = np.where(odds > 0, prob_wins - q / odds, 0.0)

    # No edge -> 0
    full_kelly = np.where(full_kelly > 0, full_kelly, 0.0)

    frac_kelly = full_kelly * fraction
    # Round to 2 decimal places (as percentage) to match scalar kelly() behavior
    frac_kelly_pct = np.round(frac_kelly * 100.0, 2)
    dollar_size = bankroll * frac_kelly_pct / 100.0

    cap = bankroll * max_pct
    return np.minimum(dollar_size, cap)


def fractional_kelly(
    win_prob: float,
    win_amount: float,
    loss_amount: float,
    fraction: float = 0.25,
) -> float:
    """Convenience wrapper: compute fractional Kelly position size.

    Args:
        win_prob: Probability of winning (0-1).
        win_amount: Dollar amount gained on win.
        loss_amount: Dollar amount lost on loss.
        fraction: Kelly fraction (default 0.25 = quarter Kelly).

    Returns:
        Recommended position size as a fraction of bankroll (0-1).
    """
    if loss_amount <= 0:
        return 0.0
    odds = win_amount / loss_amount
    result = kelly(win_prob, odds, fraction)
    return result["fractional_kelly_pct"] / 100.0
