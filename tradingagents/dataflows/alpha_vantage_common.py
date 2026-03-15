import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import StringIO
from typing import Any

import pandas as pd
import requests

from .constants import API_TIMEOUT_SECONDS
from .logging_config import alpha_vantage_logger

API_BASE_URL = "https://www.alphavantage.co/query"


def get_api_key() -> str:
    """Retrieve the API key for Alpha Vantage from environment variables."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        msg = "ALPHA_VANTAGE_API_KEY environment variable is not set."
        alpha_vantage_logger.error(msg)
        raise ValueError(msg)
    return api_key


def format_datetime_for_api(date_input: str | datetime) -> str:
    """Convert various date formats to YYYYMMDDTHHMM format required by Alpha Vantage API."""
    if isinstance(date_input, str):
        # If already in correct format, return as-is
        if len(date_input) == 13 and "T" in date_input:
            return date_input
        # Try to parse common date formats
        try:
            dt = datetime.strptime(date_input, "%Y-%m-%d")
            return dt.strftime("%Y%m%dT0000")
        except ValueError:
            try:
                dt = datetime.strptime(date_input, "%Y-%m-%d %H:%M")
                return dt.strftime("%Y%m%dT%H%M")
            except ValueError:
                msg = f"Unsupported date format: {date_input}"
                raise ValueError(msg)
    elif isinstance(date_input, datetime):
        return date_input.strftime("%Y%m%dT%H%M")
    else:
        msg = f"Date must be string or datetime object, got {type(date_input)}"
        raise ValueError(msg)


class AlphaVantageRateLimitError(Exception):
    """Exception raised when Alpha Vantage API rate limit is exceeded."""


def _make_api_request(function_name: str, params: dict) -> dict | str:
    """Helper function to make API requests and handle responses.

    Raises:
        AlphaVantageRateLimitError: When API rate limit is exceeded
    """
    alpha_vantage_logger.info(f"Making API request to Alpha Vantage: {function_name}")

    # Create a copy of params to avoid modifying the original
    api_params = params.copy()
    api_params.update({
        "function": function_name,
        "apikey": get_api_key(),
        "source": "trading_agents",
    })

    # Handle entitlement parameter if present in params or global variable
    current_entitlement = globals().get("_current_entitlement")
    entitlement = api_params.get("entitlement") or current_entitlement

    if entitlement:
        api_params["entitlement"] = entitlement
    elif "entitlement" in api_params:
        # Remove entitlement if it's None or empty
        api_params.pop("entitlement", None)

    try:
        response = requests.get(
            API_BASE_URL, params=api_params, timeout=API_TIMEOUT_SECONDS
        )
        response.raise_for_status()

        response_text = response.text

        # Check if response is JSON (error responses are typically JSON)
        try:
            response_json = json.loads(response_text)
            # Check for rate limit error
            if "Information" in response_json:
                info_message = response_json["Information"]
                if (
                    "rate limit" in info_message.lower()
                    or "api key" in info_message.lower()
                ):
                    msg = f"Alpha Vantage rate limit exceeded: {info_message}"
                    alpha_vantage_logger.warning(msg)
                    raise AlphaVantageRateLimitError(msg)
        except json.JSONDecodeError:
            # Response is not JSON (likely CSV data), which is normal
            pass

        alpha_vantage_logger.debug(f"API request successful: {function_name}")
        return response_text

    except requests.RequestException as e:
        alpha_vantage_logger.error(f"API request failed for {function_name}: {e}")
        raise


def _filter_csv_by_date_range(csv_data: str, start_date: str, end_date: str) -> str:
    """
    Filter CSV data to include only rows within the specified date range.

    Args:
        csv_data: CSV string from Alpha Vantage API
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format

    Returns:
        Filtered CSV string
    """
    if not csv_data or csv_data.strip() == "":
        alpha_vantage_logger.warning("Empty CSV data provided to filter")
        return csv_data

    try:
        # Parse CSV data
        df = pd.read_csv(StringIO(csv_data))

        # Assume the first column is the date column (timestamp)
        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col])

        # Filter by date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        filtered_df = df[(df[date_col] >= start_dt) & (df[date_col] <= end_dt)]
        alpha_vantage_logger.debug(
            f"Filtered CSV from {start_date} to {end_date}: {len(df)} rows -> {len(filtered_df)} rows"
        )

        # Convert back to CSV string
        return filtered_df.to_csv(index=False)

    except Exception as e:
        alpha_vantage_logger.warning(f"Failed to filter CSV data by date range: {e}")
        return csv_data


MAX_PARALLEL_REQUESTS = 3  # Conservative for Alpha Vantage rate limits


def _make_batch_api_requests(
    requests: list[dict[str, Any]],
) -> list[dict[str, Any] | str]:
    """Make multiple API requests in parallel with rate limiting.

    Args:
        requests: List of dicts with 'function' and 'params' keys

    Returns:
        List of responses in same order as requests
    """
    results: list[dict[str, Any] | str] = [None] * len(requests)  # type: ignore[assignment]

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as executor:
        future_to_idx = {
            executor.submit(_make_api_request, r["function"], r.get("params", {})): i
            for i, r in enumerate(requests)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()  # type: ignore[assignment]
            except Exception as e:
                results[idx] = str(e)

    return results
