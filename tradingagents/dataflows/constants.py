"""
Constants for the dataflows module.

This module centralizes all magic numbers and configuration values
used across data vendor implementations for consistency and maintainability.
"""

# =============================================================================
# Cache Configuration
# =============================================================================

#: Years of historical data to cache for stock price data
CACHE_WINDOW_YEARS = 15

# =============================================================================
# API Configuration
# =============================================================================

#: Request timeout in seconds for Alpha Vantage API calls
API_TIMEOUT_SECONDS = 30

# =============================================================================
# Technical Indicator Periods
# =============================================================================

#: 50-day Simple Moving Average period (medium-term trend indicator)
SMA_MEDIUM_PERIOD = 50

#: 200-day Simple Moving Average period (long-term trend benchmark)
SMA_LONG_PERIOD = 200

#: 10-day Exponential Moving Average period (short-term responsive average)
EMA_SHORT_PERIOD = 10

#: Bollinger Bands period (typically 20-day SMA)
BOLLINGER_PERIOD = 20

#: Relative Strength Index default period
RSI_DEFAULT_PERIOD = 14

# =============================================================================
# RSI/MFI Thresholds
# =============================================================================

#: RSI threshold indicating overbought conditions
RSI_OVERBOUGHT_THRESHOLD = 70

#: RSI threshold indicating oversold conditions
RSI_OVERSOLD_THRESHOLD = 30

#: MFI threshold indicating overbought conditions
MFI_OVERBOUGHT_THRESHOLD = 80

#: MFI threshold indicating oversold conditions
MFI_OVERSOLD_THRESHOLD = 20

# =============================================================================
# News Configuration
# =============================================================================

#: Default number of days to look back for news articles
NEWS_DEFAULT_LOOKBACK_DAYS = 7

#: Default maximum number of news articles from Alpha Vantage
NEWS_DEFAULT_LIMIT_ALPHA_VANTAGE = 50

#: Default maximum number of news articles from Yahoo Finance
NEWS_DEFAULT_LIMIT_YFINANCE = 10

#: Number of news articles to fetch from Yahoo Finance (before filtering)
NEWS_FETCH_COUNT_YFINANCE = 20

# =============================================================================
# Data Formatting
# =============================================================================

#: Number of decimal places for price values
PRICE_DECIMAL_PLACES = 2

# =============================================================================
# Output Size Threshold
# =============================================================================

#: Day threshold for choosing compact vs full outputsize in Alpha Vantage API
#: Compact returns latest 100 data points; use full for ranges exceeding this
COMPACT_OUTPUTSIZE_DAY_THRESHOLD = 100
