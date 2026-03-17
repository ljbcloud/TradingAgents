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

# Known cryptocurrency symbols (top by market cap)
KNOWN_CRYPTO_SYMBOLS = {
    "BTC",
    "ETH",
    "BNB",
    "XRP",
    "SOL",
    "ADA",
    "DOGE",
    "AVAX",
    "DOT",
    "LINK",
    "MATIC",
    "UNI",
    "ATOM",
    "LTC",
    "ETC",
    "XLM",
    "ALGO",
    "VET",
    "FIL",
    "NEAR",
    "APT",
    "ARB",
    "OP",
    "INJ",
    "SUI",
    "SEI",
    "TIA",
    "WLD",
    "PEPE",
    "SHIB",
    "BONK",
    "FLOKI",
    "RENDER",
    "GRT",
    "AAVE",
    "MKR",
    "SNX",
    "CRV",
    "COMP",
    "SUSHI",
    "YFI",
    "1INCH",
    "ENJ",
    "MANA",
    "SAND",
    "AXS",
    "GALA",
    "IMX",
    "RUNE",
    "CAKE",
    "DYDX",
    "ZEC",
    "DASH",
    "XMR",
    "FTM",
    "KAVA",
    "LUNA",
    "LDO",
    "RPL",
    "BLUR",
    "GMX",
    "JOE",
    "PENDLE",
    "ENS",
    "EIGEN",
    "WIF",
    "JUP",
    "PYTH",
    "ONDO",
    "MEME",
    "ORDI",
    "STX",
    "CFX",
    "HBAR",
    "QNT",
    "KAS",
    "TON",
    "ICP",
    "FET",
    "AGIX",
    "RNDR",
    "THETA",
    "FTT",
    "FLOW",
}

# Known cryptocurrency full names (lowercase)
KNOWN_CRYPTO_NAMES = {
    "bitcoin",
    "ethereum",
    "binance",
    "ripple",
    "solana",
    "cardano",
    "dogecoin",
    "avalanche",
    "polkadot",
    "chainlink",
    "polygon",
    "uniswap",
    "cosmos",
    "litecoin",
    "stellar",
    "algorand",
    "vechain",
    "filecoin",
    "near",
    "aptos",
    "arbitrum",
    "optimism",
    "injective",
    "sui",
    "sei",
    "celestia",
    "worldcoin",
    "pepe",
    "shiba",
    "bonk",
    "floki",
    "render",
    "graph",
    "aave",
    "maker",
    "synthetix",
    "curve",
    "compound",
    "sushi",
    "yearn",
    "1inch",
    "enjin",
    "decentraland",
    "sandbox",
    "axie",
    "gala",
    "immutable",
    "thorchain",
    "pancakeswap",
    "dYdX",
    "zcash",
    "dash",
    "monero",
    "fantom",
    "kava",
    "terra",
    "lido",
    "rocket",
    "blur",
    "gmx",
    "traderjoe",
    "pendle",
    "ens",
    "eigenlayer",
    "dogwifhat",
    "jupiter",
    "pyth",
    "ondo",
    "meme",
    "ordinals",
    "stacks",
    "conflux",
    "hedera",
    "quant",
    "kaspa",
    "toncoin",
    "internet computer",
    "fetch",
    "singularity",
    "theta",
    "ftx",
    "flow",
    "tether",
    "usdc",
    "usdt",
    "dai",
    "busd",
    "tusd",
    "usdd",
    "frax",
}


def classify_ticker(ticker: str) -> Literal["stock", "crypto"]:
    """Classify a ticker as either 'stock' or 'crypto' based on pattern matching.

    Classification rules (evaluated in order):
        1. Crypto: Ticker contains '/' or '-' (common crypto pair separators)
        2. Crypto: Ticker ends with USDT, USD, BTC, or ETH (case-insensitive)
        3. Crypto: Ticker matches known crypto symbol (BTC, ETH, SOL, etc.)
        4. Crypto: Ticker matches known crypto name (bitcoin, ethereum, etc.)
        5. Stock: Ticker is 1-5 uppercase letters only (matches US stock format)
        6. Default: Returns 'stock' for any unrecognized pattern

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
        >>> classify_ticker("SOL")
        'crypto'
        >>> classify_ticker("bitcoin")
        'crypto'
    """
    if "/" in ticker or "-" in ticker:
        return "crypto"

    ticker_upper = ticker.upper()
    ticker_lower = ticker.lower()

    crypto_suffixes = ("USDT", "USD", "BTC", "ETH")
    if ticker_upper.endswith(crypto_suffixes):
        return "crypto"

    if ticker_upper in KNOWN_CRYPTO_SYMBOLS:
        return "crypto"

    if ticker_lower in KNOWN_CRYPTO_NAMES:
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
