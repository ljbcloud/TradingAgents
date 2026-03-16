from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_crypto_candles(
    symbol: Annotated[str, "trading pair like BTC/USD, ETH/USD"],
    timeframe: Annotated[str, "candle interval: 1m, 5m, 15m, 1h, 6h, 1d"] = "1h",
    start_date: Annotated[str | None, "Start date in yyyy-mm-dd format"] = None,
    end_date: Annotated[str | None, "End date in yyyy-mm-dd format"] = None,
    limit: Annotated[int, "Maximum number of candles to fetch"] = 300,
    exchange: Annotated[str, "exchange name: coinbase, binance, kraken"] = "coinbase",
) -> str:
    """
    Retrieve OHLCV candlestick data for a cryptocurrency trading pair.
    Uses the configured crypto_apis vendor (default: CCXT/Coinbase).
    Args:
        symbol (str): Trading pair symbol, e.g. BTC/USD, ETH/USD
        timeframe (str): Candle interval (1m, 5m, 15m, 1h, 6h, 1d)
        start_date (str | None): Start date in yyyy-mm-dd format
        end_date (str | None): End date in yyyy-mm-dd format
        limit (int): Maximum number of candles to fetch
        exchange (str): Exchange name (coinbase, binance, kraken, etc.)
    Returns:
        str: CSV-formatted OHLCV data with timestamp, open, high, low, close, volume columns.
    """
    return route_to_vendor(
        "get_crypto_candles", symbol, timeframe, start_date, end_date, limit, exchange
    )


@tool
def get_crypto_ticker(
    symbol: Annotated[str, "trading pair like BTC/USD, ETH/USD"],
    exchange: Annotated[str, "exchange name: coinbase, binance, kraken"] = "coinbase",
) -> str:
    """
    Retrieve current ticker data (price, bid/ask, 24h volume) for a cryptocurrency.
    Uses the configured crypto_apis vendor.
    Args:
        symbol (str): Trading pair symbol, e.g. BTC/USD, ETH/USD
        exchange (str): Exchange name (coinbase, binance, kraken, etc.)
    Returns:
        str: Ticker data including bid, ask, last price, 24h high/low, and volume.
    """
    return route_to_vendor("get_crypto_ticker", symbol, exchange)


@tool
def get_crypto_orderbook(
    symbol: Annotated[str, "trading pair like BTC/USD, ETH/USD"],
    depth: Annotated[int, "Number of price levels to fetch"] = 20,
    exchange: Annotated[str, "exchange name: coinbase, binance, kraken"] = "coinbase",
) -> str:
    """
    Retrieve order book data (bids and asks) for a cryptocurrency trading pair.
    Uses the configured crypto_apis vendor.
    Args:
        symbol (str): Trading pair symbol, e.g. BTC/USD, ETH/USD
        depth (int): Number of price levels to fetch
        exchange (str): Exchange name (coinbase, binance, kraken, etc.)
    Returns:
        str: Order book data with bids, asks, and spread calculation.
    """
    return route_to_vendor("get_crypto_orderbook", symbol, depth, exchange)
