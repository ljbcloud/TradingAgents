"""
Common utilities for dataflows module.

This module contains shared utility functions used across different data vendors
to reduce code duplication and ensure consistent behavior.

Functions:
    parse_csv_data: Parse CSV string into header and rows
    find_column_index: Find column index in header
    extract_article_data: Normalize article data from news APIs
"""

import contextlib
from datetime import datetime
from typing import Any

_ERR_EMPTY_CSV = "Empty CSV data provided"
_ERR_NO_LINES = "CSV data has no lines"


def parse_csv_data(csv_string: str) -> tuple[list[str], list[list[str]]]:
    """Parse CSV string into header and rows.

    Args:
        csv_string: Raw CSV data as string

    Returns:
        Tuple of (header list, rows list)

    Raises:
        ValidationError: If CSV data is empty or malformed
    """
    from .exceptions import ValidationError

    if not csv_string or not csv_string.strip():
        raise ValidationError(_ERR_EMPTY_CSV, function="parse_csv_data")

    lines = csv_string.strip().split("\n")
    if len(lines) < 1:
        raise ValidationError(_ERR_NO_LINES, function="parse_csv_data")

    header = [col.strip() for col in lines[0].split(",")]
    rows = [
        [val.strip() for val in line.split(",")] for line in lines[1:] if line.strip()
    ]

    return header, rows


def find_column_index(
    header: list[str], column_name: str, *, case_sensitive: bool = False
) -> int:
    """Find the index of a column in a header list.

    Args:
        header: List of column names
        column_name: Column name to find
        case_sensitive: Whether to do case-sensitive matching

    Returns:
        Column index

    Raises:
        ValidationError: If column not found
    """
    from .exceptions import ValidationError

    search_header = header if case_sensitive else [h.lower() for h in header]
    search_name = column_name if case_sensitive else column_name.lower()

    try:
        return search_header.index(search_name)
    except ValueError:
        available = ", ".join(header)
        msg = f"Column '{column_name}' not found. Available columns: {available}"
        raise ValidationError(
            msg,
            function="find_column_index",
            params={"column_name": column_name, "available_columns": header},
        )


def extract_article_data(article: dict[str, Any]) -> dict[str, Any]:
    """Extract article data from news API response (handles nested 'content' structure).

    Handles both yfinance nested structure (with 'content' key) and flat structure.

    Args:
        article: Raw article dict from news API

    Returns:
        Normalized dict with keys: title, summary, publisher, link, pub_date
    """
    # Handle nested content structure (yfinance format)
    if "content" in article:
        content = article["content"]
        title = content.get("title", "No title")
        summary = content.get("summary", "")
        provider = content.get("provider", {})
        publisher = provider.get("displayName", "Unknown")

        # Get URL from canonicalUrl or clickThroughUrl
        url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
        link = url_obj.get("url", "")

        # Get publish date
        pub_date_str = content.get("pubDate", "")
        pub_date: datetime | None = None
        if pub_date_str:
            with contextlib.suppress(ValueError, AttributeError):
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))

        return {
            "title": title,
            "summary": summary,
            "publisher": publisher,
            "link": link,
            "pub_date": pub_date,
        }

    # Fallback for flat structure
    return {
        "title": article.get("title", "No title"),
        "summary": article.get("summary", ""),
        "publisher": article.get("publisher", "Unknown"),
        "link": article.get("link", ""),
        "pub_date": None,
    }
