"""
Alpha Vantage fundamental data fetching.

Provides functions to retrieve company fundamentals, balance sheets, cash flow
statements, and income statements from Alpha Vantage fundamental data endpoints.
"""

from concurrent.futures import ThreadPoolExecutor

from .alpha_vantage_common import _make_api_request
from .logging_config import alpha_vantage_logger


def get_fundamentals(ticker: str, curr_date: str | None = None) -> str:
    """
    Retrieve comprehensive fundamental data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        curr_date (str): Current date you are trading at, yyyy-mm-dd (not used for Alpha Vantage)

    Returns:
        str: Company overview data including financial ratios and key metrics
    """
    alpha_vantage_logger.info(f"Fetching fundamentals for {ticker}")

    params = {
        "symbol": ticker,
    }

    return _make_api_request("OVERVIEW", params)


def get_balance_sheet(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    """
    Retrieve balance sheet data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly) - not used for Alpha Vantage
        curr_date (str): Current date you are trading at, yyyy-mm-dd (not used for Alpha Vantage)

    Returns:
        str: Balance sheet data with normalized fields
    """
    alpha_vantage_logger.info(f"Fetching balance sheet for {ticker}")

    params = {
        "symbol": ticker,
    }

    return _make_api_request("BALANCE_SHEET", params)


def get_cashflow(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    """
    Retrieve cash flow statement data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly) - not used for Alpha Vantage
        curr_date (str): Current date you are trading at, yyyy-mm-dd (not used for Alpha Vantage)

    Returns:
        str: Cash flow statement data with normalized fields
    """
    alpha_vantage_logger.info(f"Fetching cash flow for {ticker}")

    params = {
        "symbol": ticker,
    }

    return _make_api_request("CASH_FLOW", params)


def get_income_statement(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    """
    Retrieve income statement data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly) - not used for Alpha Vantage
        curr_date (str): Current date you are trading at, yyyy-mm-dd (not used for Alpha Vantage)

    Returns:
        str: Income statement data with normalized fields
    """
    alpha_vantage_logger.info(f"Fetching income statement for {ticker}")

    params = {
        "symbol": ticker,
    }

    return _make_api_request("INCOME_STATEMENT", params)


def get_fundamentals_bulk(ticker: str) -> dict[str, str]:
    """Fetch all fundamental data in parallel.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with keys: overview, balance_sheet, cash_flow, income_statement
    """
    alpha_vantage_logger.info(f"Fetching all fundamentals in parallel for {ticker}")

    def fetch_overview() -> tuple[str, str]:
        try:
            return ("overview", get_fundamentals(ticker))
        except Exception as e:
            return ("overview", f"Error: {e}")

    def fetch_balance_sheet() -> tuple[str, str]:
        try:
            return ("balance_sheet", get_balance_sheet(ticker))
        except Exception as e:
            return ("balance_sheet", f"Error: {e}")

    def fetch_cash_flow() -> tuple[str, str]:
        try:
            return ("cash_flow", get_cashflow(ticker))
        except Exception as e:
            return ("cash_flow", f"Error: {e}")

    def fetch_income_statement() -> tuple[str, str]:
        try:
            return ("income_statement", get_income_statement(ticker))
        except Exception as e:
            return ("income_statement", f"Error: {e}")

    results: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(fetch_overview),
            executor.submit(fetch_balance_sheet),
            executor.submit(fetch_cash_flow),
            executor.submit(fetch_income_statement),
        ]
        for future in futures:
            key, value = future.result()
            results[key] = value

    return results
