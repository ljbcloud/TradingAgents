from typing import Annotated

from langchain_core.tools import tool

from dataflows.interface import route_to_vendor


@tool
def get_bitcoin_fear_greed_index(
    limit: Annotated[
        int, "Number of historical values to return (default 1 for current only)"
    ] = 1,
) -> str:
    """
    Retrieve the Bitcoin Fear and Greed Index, a sentiment indicator
    measuring market emotion on a scale of 0-100.

    Values are classified as:
    - 0-24: Extreme Fear (potential buying opportunity)
    - 25-49: Fear
    - 50-54: Neutral
    - 55-75: Greed
    - 76-100: Extreme Greed (potential selling opportunity)

    Uses the configured crypto sentiment vendor (default: Alternative.me).

    Args:
        limit (int): Number of results to return. Use 1 for current value only,
                     or higher values for historical trend analysis.

    Returns:
        str: Fear and Greed Index data including current value, classification,
             and optionally historical values with trend analysis.
    """
    return route_to_vendor("get_bitcoin_fear_greed_index", limit)


__all__ = [
    "get_bitcoin_fear_greed_index",
]
