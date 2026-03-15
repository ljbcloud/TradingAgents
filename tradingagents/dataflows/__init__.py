"""
TradingAgents Dataflows Module.

This module provides a unified interface for fetching financial data from multiple
vendors (Alpha Vantage, Yahoo Finance) with automatic fallback support.

Primary Interface:
    route_to_vendor: Route method calls to appropriate vendor with fallback

Exception Hierarchy:
    DataFetchError (base)
    ├── VendorError - Vendor-specific errors
    ├── RateLimitError - API rate limit exceeded
    ├── ValidationError - Invalid input/output data
    ├── ConfigurationError - Configuration issues
    └── NetworkError - Network connectivity problems

Utilities:
    parse_csv_data: Parse CSV string into header and rows
    find_column_index: Find column index in header
    extract_article_data: Normalize article data from news APIs

Example Usage:
    >>> from tradingagents.dataflows import route_to_vendor
    >>> data = route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-01-31")
"""

# Vendor implementations (optional direct access)
from .alpha_vantage import (  # noqa: F401
    get_balance_sheet as get_alpha_vantage_balance_sheet,
)
from .alpha_vantage import (  # noqa: F401
    get_cashflow as get_alpha_vantage_cashflow,
)
from .alpha_vantage import (  # noqa: F401
    get_fundamentals as get_alpha_vantage_fundamentals,
)
from .alpha_vantage import (  # noqa: F401
    get_global_news as get_alpha_vantage_global_news,
)
from .alpha_vantage import (  # noqa: F401
    get_income_statement as get_alpha_vantage_income_statement,
)
from .alpha_vantage import (  # noqa: F401
    get_indicator as get_alpha_vantage_indicator,
)
from .alpha_vantage import (  # noqa: F401
    get_insider_transactions as get_alpha_vantage_insider_transactions,
)
from .alpha_vantage import (  # noqa: F401
    get_news as get_alpha_vantage_news,
)
from .alpha_vantage import (  # noqa: F401
    get_stock as get_alpha_vantage_stock,
)

# Common utilities
from .common import extract_article_data, find_column_index, parse_csv_data
from .exceptions import (
    ConfigurationError,
    DataFetchError,
    NetworkError,
    RateLimitError,
    ValidationError,
    VendorError,
)

# Interface
from .interface import route_to_vendor
from .y_finance import (  # noqa: F401
    get_balance_sheet as get_yfinance_balance_sheet,
)
from .y_finance import (  # noqa: F401
    get_cashflow as get_yfinance_cashflow,
)
from .y_finance import (  # noqa: F401
    get_fundamentals as get_yfinance_fundamentals,
)
from .y_finance import (  # noqa: F401
    get_income_statement as get_yfinance_income_statement,
)
from .y_finance import (  # noqa: F401
    get_insider_transactions as get_yfinance_insider_transactions,
)
from .y_finance import (  # noqa: F401
    get_stock_stats_indicators_window,
    get_YFin_data_online,
)
from .yfinance_news import get_global_news_yfinance, get_news_yfinance  # noqa: F401

__all__ = [  # noqa: RUF022
    # Exceptions
    "DataFetchError",
    "VendorError",
    "RateLimitError",
    "ValidationError",
    "ConfigurationError",
    "NetworkError",
    # Interface
    "route_to_vendor",
    # Common utilities
    "parse_csv_data",
    "find_column_index",
    "extract_article_data",
]
