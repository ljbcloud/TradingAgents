"""
Alternative.me Fear and Greed Index API vendor implementation.

Provides functions to retrieve the Bitcoin Fear and Greed Index,
a sentiment indicator measuring market emotion on a scale of 0-100.
No API key required for free tier access.

API Documentation: https://alternative.me/crypto/fear-and-greed-index/
"""

from datetime import UTC, datetime
from typing import Annotated

import requests

from .exceptions import VendorError
from .logging_config import get_logger

logger = get_logger("alternative_me")

ALTERNATIVE_ME_API_BASE = "https://api.alternative.me/fng"


def _classify_value(value: int) -> str:
    """Classify Fear and Greed Index value into sentiment category.

    Classification ranges:
    - 0-24: Extreme Fear
    - 25-49: Fear
    - 50-54: Neutral
    - 55-75: Greed
    - 76-100: Extreme Greed

    Args:
        value: Numeric index value (0-100)

    Returns:
        Sentiment classification string
    """
    if value <= 24:
        return "Extreme Fear"
    if value <= 49:
        return "Fear"
    if value <= 54:
        return "Neutral"
    if value <= 75:
        return "Greed"
    return "Extreme Greed"


def _format_timestamp(timestamp_str: str) -> str:
    """Convert Unix timestamp to human-readable date.

    Args:
        timestamp_str: Unix timestamp as string

    Returns:
        Formatted date string (YYYY-MM-DD)
    """
    try:
        ts = int(timestamp_str)
        return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return "Unknown date"


def get_bitcoin_fear_greed_index(
    limit: Annotated[int, "Number of results to return (default 1 for current)"] = 1,
) -> str:
    """Fetch Bitcoin Fear and Greed Index data.

    Retrieves the Fear and Greed Index, a sentiment indicator that measures
    market emotion on a scale of 0-100. Values are classified as:
    - 0-24: Extreme Fear (potential buying opportunity)
    - 25-49: Fear
    - 50-54: Neutral
    - 55-75: Greed
    - 76-100: Extreme Greed (potential selling opportunity)

    Args:
        limit: Number of results to return (default 1 for current value only)

    Returns:
        Formatted string with Fear and Greed Index data including:
        - Current value and classification
        - Historical values (if limit > 1)
        - Timestamps for each data point

    Raises:
        VendorError: If the API request fails or returns invalid data
    """
    logger.info("Fetching Fear and Greed Index (limit=%d)", limit)

    try:
        response = requests.get(
            ALTERNATIVE_ME_API_BASE,
            params={"limit": limit},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        fng_data = data.get("data", [])

        if not fng_data:
            msg = "No Fear and Greed Index data available"
            logger.warning(msg)
            return msg

        lines = [
            "# Bitcoin Fear and Greed Index",
            "# Source: Alternative.me",
            "",
            "## Classification Guide",
            "- 0-24: Extreme Fear (market panic, potential buying opportunity)",
            "- 25-49: Fear (investors are worried)",
            "- 50-54: Neutral (balanced sentiment)",
            "- 55-75: Greed (investors are optimistic)",
            "- 76-100: Extreme Greed (market euphoria, potential selling opportunity)",
            "",
        ]

        current = fng_data[0]
        value = int(current.get("value", 0))
        classification = current.get("value_classification", _classify_value(value))
        timestamp = _format_timestamp(current.get("timestamp", ""))

        lines.extend([
            "## Current Reading",
            f"Value: {value}",
            f"Classification: {classification}",
            f"Date: {timestamp}",
            "",
        ])

        if len(fng_data) > 1:
            lines.extend([
                "## Historical Readings",
                "| Date | Value | Classification |",
                "|------|-------|----------------|",
            ])
            for entry in fng_data:
                val = entry.get("value", "N/A")
                cls = entry.get("value_classification", "N/A")
                ts = _format_timestamp(entry.get("timestamp", ""))
                lines.append(f"| {ts} | {val} | {cls} |")
            lines.append("")

        if len(fng_data) >= 2:
            try:
                latest = int(fng_data[0].get("value", 0))
                previous = int(fng_data[1].get("value", 0))
                change = latest - previous
                direction = (
                    "increased"
                    if change > 0
                    else "decreased"
                    if change < 0
                    else "unchanged"
                )
                lines.extend([
                    "## Trend Analysis",
                    f"Change from previous: {direction} by {abs(change)} points",
                    "",
                ])
            except (ValueError, TypeError):
                pass

        logger.debug("Retrieved Fear and Greed Index: value=%d", value)
        return "\n".join(lines)

    except requests.exceptions.Timeout:
        error_msg = "Alternative.me API request timed out"
        logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_bitcoin_fear_greed_index",
            vendor="alternative_me",
            params={"limit": limit},
        )
    except requests.exceptions.HTTPError as e:
        error_msg = f"Alternative.me API HTTP error: {e}"
        logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_bitcoin_fear_greed_index",
            vendor="alternative_me",
            params={"limit": limit},
            original_error=e,
        )
    except requests.exceptions.RequestException as e:
        error_msg = f"Alternative.me API request failed: {e}"
        logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_bitcoin_fear_greed_index",
            vendor="alternative_me",
            params={"limit": limit},
            original_error=e,
        )
    except (KeyError, ValueError, TypeError) as e:
        error_msg = f"Failed to parse Alternative.me API response: {e}"
        logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_bitcoin_fear_greed_index",
            vendor="alternative_me",
            params={"limit": limit},
            original_error=e,
        )


__all__ = [
    "get_bitcoin_fear_greed_index",
]
