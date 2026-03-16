"""Ticker classification and normalization utilities.

This module provides utilities for classifying financial tickers as stocks or
cryptocurrencies, and normalizing crypto tickers for use with CCXT library.

Example:
    >>> from tradingagents.agents.utils.ticker_utils import classify_ticker, normalize_crypto_ticker
    >>> classify_ticker("AAPL")
    'stock'
    >>> classify_ticker("BTC-USD")
    'crypto'
    >>> normalize_crypto_ticker("BTC-USD")
    'BTC/USD'
"""

import re
from typing import Literal


def classify_ticker(ticker: str) -> Literal["stock", "crypto"]:
    """Classify a ticker as either 'stock' or 'crypto' based on pattern matching.

    Classification rules (evaluated in order):
        1. Crypto: Ticker contains '/' or '-' (common crypto pair separators)
        2. Crypto: Ticker ends with USDT, USD, BTC, or ETH (case-insensitive)
        3. Stock: Ticker is 1-5 uppercase letters only (matches US stock format)
        4. Default: Returns 'stock' for any unrecognized pattern

    Args:
        ticker: The ticker symbol to classify (e.g., "AAPL", "BTC-USD", "ETH/USDT").

    Returns:
        Either "stock" or "crypto" based on the classification rules.

    Examples:
        >>> classify_ticker("AAPL")
        'stock'
        >>> classify_ticker("MSFT")
        'stock'
        >>> classify_ticker("BTC-USD")
        'crypto'
        >>> classify_ticker("ETH/USDT")
        'crypto'
        >>> classify_ticker("DOGEUSDT")
        'crypto'
        >>> classify_ticker("SOLUSD")
        'crypto'
        >>> classify_ticker("WBTC")
        'crypto'
        >>> classify_ticker("WETH")
        'crypto'
    """
    if "/" in ticker or "-" in ticker:
        return "crypto"

    ticker_upper = ticker.upper()
    crypto_suffixes = ("USDT", "USD", "BTC", "ETH")
    if ticker_upper.endswith(crypto_suffixes):
        return "crypto"

    stock_pattern = re.compile(r"^[A-Z]{1,5}$")
    if stock_pattern.match(ticker):
        return "stock"

    return "stock"


def normalize_crypto_ticker(ticker: str) -> str:
    """Normalize a crypto ticker to CCXT-compatible format.

    CCXT expects crypto pairs in the format "BASE/QUOTE" (e.g., "BTC/USD").
    This function converts common alternative formats to this standard.

    Args:
        ticker: The crypto ticker to normalize (e.g., "BTC-USD", "ETH/USDT").

    Returns:
        The normalized ticker in BASE/QUOTE format.

    Examples:
        >>> normalize_crypto_ticker("BTC-USD")
        'BTC/USD'
        >>> normalize_crypto_ticker("ETH-USDT")
        'ETH/USDT'
        >>> normalize_crypto_ticker("SOL/USD")
        'SOL/USD'
        >>> normalize_crypto_ticker("BTC/USD")
        'BTC/USD'
    """
    return ticker.replace("-", "/")
