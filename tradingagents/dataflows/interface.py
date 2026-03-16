"""
Vendor routing interface for dataflows module.

This module provides the primary interface for routing data requests to
appropriate vendors (Alpha Vantage, Yahoo Finance) with automatic fallback
support when a vendor fails or rate limits.

Primary Functions:
    route_to_vendor: Main entry point for data requests with fallback support
    get_vendor: Get the configured vendor for a category or tool
    get_category_for_method: Look up the category for a given method name

Example:
    >>> from tradingagents.dataflows.interface import route_to_vendor
    >>> data = route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-01-31")
"""

from collections.abc import Callable

import requests

from .alpha_vantage import (
    get_balance_sheet as get_alpha_vantage_balance_sheet,
)
from .alpha_vantage import (
    get_cashflow as get_alpha_vantage_cashflow,
)
from .alpha_vantage import (
    get_fundamentals as get_alpha_vantage_fundamentals,
)
from .alpha_vantage import (
    get_global_news as get_alpha_vantage_global_news,
)
from .alpha_vantage import (
    get_income_statement as get_alpha_vantage_income_statement,
)
from .alpha_vantage import (
    get_indicator as get_alpha_vantage_indicator,
)
from .alpha_vantage import (
    get_insider_transactions as get_alpha_vantage_insider_transactions,
)
from .alpha_vantage import (
    get_news as get_alpha_vantage_news,
)
from .alpha_vantage import (
    get_stock as get_alpha_vantage_stock,
)
from .alpha_vantage_common import AlphaVantageRateLimitError
from .ccxt_common import CCXTRateLimitError
from .ccxt_crypto import (
    get_crypto_candles,
    get_crypto_orderbook,
    get_crypto_ticker,
)
from .coingecko import get_crypto_token_info
from .config import get_config
from .defillama import get_crypto_protocol_tvl, get_crypto_protocol_yields
from .y_finance import (
    get_balance_sheet as get_yfinance_balance_sheet,
)
from .y_finance import (
    get_cashflow as get_yfinance_cashflow,
)
from .y_finance import (
    get_fundamentals as get_yfinance_fundamentals,
)
from .y_finance import (
    get_income_statement as get_yfinance_income_statement,
)
from .y_finance import (
    get_insider_transactions as get_yfinance_insider_transactions,
)

# Import from vendor-specific modules
from .y_finance import (
    get_stock_stats_indicators_window,
    get_YFin_data_online,
)
from .yfinance_news import get_global_news_yfinance, get_news_yfinance

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": ["get_stock_data"],
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": ["get_indicators"],
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement",
        ],
    },
    "news_data": {
        "description": "News and insider data",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_transactions",
        ],
    },
    "crypto_apis": {
        "description": "Cryptocurrency market data",
        "tools": [
            "get_crypto_candles",
            "get_crypto_ticker",
            "get_crypto_orderbook",
        ],
    },
    "crypto_fundamentals": {
        "description": "Cryptocurrency fundamentals (tokenomics, TVL, yields)",
        "tools": [
            "get_crypto_token_info",
            "get_crypto_protocol_tvl",
            "get_crypto_protocol_yields",
        ],
    },
}

VENDOR_LIST = [
    "yfinance",
    "alpha_vantage",
    "ccxt",
    "coingecko",
    "defillama",
]

# Mapping of methods to their vendor-specific implementations
VENDOR_METHODS: dict[str, dict[str, Callable[..., dict[str, str] | str]]] = {
    # core_stock_apis
    "get_stock_data": {
        "alpha_vantage": get_alpha_vantage_stock,
        "yfinance": get_YFin_data_online,
    },
    # technical_indicators
    "get_indicators": {
        "alpha_vantage": get_alpha_vantage_indicator,
        "yfinance": get_stock_stats_indicators_window,
    },
    # fundamental_data
    "get_fundamentals": {
        "alpha_vantage": get_alpha_vantage_fundamentals,
        "yfinance": get_yfinance_fundamentals,
    },
    "get_balance_sheet": {
        "alpha_vantage": get_alpha_vantage_balance_sheet,
        "yfinance": get_yfinance_balance_sheet,
    },
    "get_cashflow": {
        "alpha_vantage": get_alpha_vantage_cashflow,
        "yfinance": get_yfinance_cashflow,
    },
    "get_income_statement": {
        "alpha_vantage": get_alpha_vantage_income_statement,
        "yfinance": get_yfinance_income_statement,
    },
    # news_data
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
        "yfinance": get_news_yfinance,
    },
    "get_global_news": {
        "yfinance": get_global_news_yfinance,
        "alpha_vantage": get_alpha_vantage_global_news,
    },
    "get_insider_transactions": {
        "alpha_vantage": get_alpha_vantage_insider_transactions,
        "yfinance": get_yfinance_insider_transactions,
    },
    # crypto_apis
    "get_crypto_candles": {
        "ccxt": get_crypto_candles,
    },
    "get_crypto_ticker": {
        "ccxt": get_crypto_ticker,
    },
    "get_crypto_orderbook": {
        "ccxt": get_crypto_orderbook,
    },
    # crypto_fundamentals
    "get_crypto_token_info": {
        "coingecko": get_crypto_token_info,
    },
    "get_crypto_protocol_tvl": {
        "defillama": get_crypto_protocol_tvl,
    },
    "get_crypto_protocol_yields": {
        "defillama": get_crypto_protocol_yields,
    },
}


def get_category_for_method(method: str) -> str:
    """Look up the data category for a given method name.

    Args:
        method: The method name (e.g., "get_stock_data", "get_indicators")

    Returns:
        Category name (e.g., "core_stock_apis", "technical_indicators")

    Raises:
        ValueError: If the method is not found in any category
    """
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    msg = f"Method '{method}' not found in any category"
    raise ValueError(msg)


def get_vendor(category: str, method: str | None = None) -> str:
    """Get the configured vendor for a data category or specific tool.

    Tool-level configuration takes precedence over category-level settings.

    Args:
        category: Data category name (e.g., "core_stock_apis", "news_data")
        method: Optional method name for tool-level vendor lookup

    Returns:
        Vendor name (e.g., "yfinance", "alpha_vantage", or comma-separated list)
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")


def route_to_vendor(method: str, *args, **kwargs) -> dict[str, str] | str:
    """Route a method call to the appropriate vendor implementation.

    Tries configured vendors first, then falls back to other available vendors
    if rate limits or network errors occur.

    Args:
        method: Method name to route (e.g., "get_stock_data", "get_news")
        *args: Positional arguments passed to the vendor implementation
        **kwargs: Keyword arguments passed to the vendor implementation

    Returns:
        Data from the first successful vendor call

    Raises:
        ValueError: If the method is not supported
        RuntimeError: If no vendor is available for the method
    """
    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)
    primary_vendors = [v.strip() for v in vendor_config.split(",")]

    if method not in VENDOR_METHODS:
        msg = f"Method '{method}' not supported"
        raise ValueError(msg)

    # Build fallback chain: primary vendors first, then remaining available vendors
    all_available_vendors = list(VENDOR_METHODS[method].keys())
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl

        try:
            return impl_func(*args, **kwargs)
        except (
            AlphaVantageRateLimitError,
            CCXTRateLimitError,
            requests.RequestException,
        ):
            # Rate limits and network errors trigger fallback
            continue

    msg = f"No available vendor for '{method}'"
    raise RuntimeError(msg)
