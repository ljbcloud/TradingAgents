"""
Alpha Vantage stock price data fetching.

Provides functions to retrieve OHLCV (Open, High, Low, Close, Volume) stock data
from Alpha Vantage TIME_SERIES_DAILY_ADJUSTED endpoint.
"""

from datetime import datetime

from .alpha_vantage_common import _filter_csv_by_date_range, _make_api_request
from .constants import COMPACT_OUTPUTSIZE_DAY_THRESHOLD
from .logging_config import alpha_vantage_logger


def get_stock(symbol: str, start_date: str, end_date: str) -> str:
    """
    Returns raw daily OHLCV values, adjusted close values, and historical split/dividend events
    filtered to the specified date range.

    Args:
        symbol: The name of the equity. For example: symbol=IBM
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format

    Returns:
        CSV string containing the daily adjusted time series data filtered to the date range.
    """
    alpha_vantage_logger.info(
        f"Fetching stock data for {symbol} from {start_date} to {end_date}"
    )

    # Parse dates to determine the range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    today = datetime.now()

    # Choose outputsize based on whether the requested range is within the latest 100 days
    # Compact returns latest 100 data points, so check if start_date is recent enough
    days_from_today_to_start = (today - start_dt).days
    outputsize = (
        "compact"
        if days_from_today_to_start < COMPACT_OUTPUTSIZE_DAY_THRESHOLD
        else "full"
    )

    params = {
        "symbol": symbol,
        "outputsize": outputsize,
        "datatype": "csv",
    }

    alpha_vantage_logger.debug(
        f"Using outputsize={outputsize} for {symbol} ({days_from_today_to_start} days from today)"
    )

    response = _make_api_request("TIME_SERIES_DAILY_ADJUSTED", params)

    return _filter_csv_by_date_range(response, start_date, end_date)
