"""
CCXT cryptocurrency data vendor implementation.

Provides functions to retrieve cryptocurrency OHLCV candlestick data, ticker data,
and order book information using the CCXT library with exchange caching support.
"""

from datetime import datetime
from typing import Annotated, Any

import ccxt

from .ccxt_common import CCXTRateLimitError, ccxt_logger, create_exchange
from .exceptions import VendorError

# Cache for exchange instances to enable reuse
_exchange_cache: dict[str, Any] = {}


def _get_exchange(exchange_name: str) -> Any:
    """Get or create cached exchange instance."""
    normalized = exchange_name.lower().strip()
    if normalized not in _exchange_cache:
        _exchange_cache[normalized] = create_exchange(normalized)
    return _exchange_cache[normalized]


def _timestamp_to_datetime(timestamp_ms: int) -> str:
    """Convert millisecond timestamp to datetime string."""
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def get_crypto_candles(
    symbol: Annotated[str, "trading pair like BTC/USD, ETH/USD"],
    timeframe: Annotated[str, "candle interval: 1m, 5m, 15m, 1h, 6h, 1d"] = "1h",
    start_date: Annotated[str | None, "start date in yyyy-mm-dd format"] = None,
    end_date: Annotated[str | None, "end date in yyyy-mm-dd format"] = None,
    limit: Annotated[int, "maximum number of candles to fetch"] = 300,
    exchange: Annotated[
        str, "exchange name: coinbase, binance, kraken, etc."
    ] = "coinbase",
) -> str:
    """Fetch OHLCV candlestick data for a cryptocurrency trading pair."""
    ccxt_logger.info(
        f"Fetching crypto candles for {symbol} ({timeframe}) from {exchange}"
    )

    try:
        ex = _get_exchange(exchange)

        # Convert date strings to timestamps if provided
        since = None
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            since = int(start_dt.timestamp() * 1000)

        # Fetch OHLCV data
        ohlcv = ex.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            since=since,
            limit=limit,
        )

        if not ohlcv:
            msg = f"No candle data found for {symbol} on {exchange}"
            ccxt_logger.warning(msg)
            return msg

        # Filter by end_date if provided
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_timestamp = int(end_dt.timestamp() * 1000)
            ohlcv = [candle for candle in ohlcv if candle[0] <= end_timestamp]

        # Build CSV output
        lines = ["timestamp,open,high,low,close,volume"]
        for candle in ohlcv:
            timestamp = _timestamp_to_datetime(candle[0])
            open_price = candle[1]
            high = candle[2]
            low = candle[3]
            close = candle[4]
            volume = candle[5]
            lines.append(f"{timestamp},{open_price},{high},{low},{close},{volume}")

        csv_data = "\n".join(lines)

        # Build header
        header = f"# Crypto OHLCV data for {symbol} from {exchange}\n"
        header += f"# Timeframe: {timeframe}\n"
        header += f"# Total candles: {len(ohlcv)}\n\n"

        ccxt_logger.debug(f"Retrieved {len(ohlcv)} candles for {symbol}")
        return header + csv_data

    except ccxt.RateLimitExceeded as e:
        raise CCXTRateLimitError(str(e), exchange=exchange) from e
    except Exception as e:
        error_msg = f"Error fetching crypto candles for {symbol} from {exchange}"
        ccxt_logger.error(f"{error_msg}: {e}")
        raise VendorError(
            error_msg,
            function="get_crypto_candles",
            vendor="ccxt",
            params={
                "symbol": symbol,
                "timeframe": timeframe,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
                "exchange": exchange,
            },
            original_error=e,
        )


def get_crypto_ticker(
    symbol: Annotated[str, "trading pair like BTC/USD, ETH/USD"],
    exchange: Annotated[
        str, "exchange name: coinbase, binance, kraken, etc."
    ] = "coinbase",
) -> str:
    """Fetch current ticker data for a cryptocurrency trading pair."""
    ccxt_logger.info(f"Fetching crypto ticker for {symbol} from {exchange}")

    try:
        ex = _get_exchange(exchange)
        ticker = ex.fetch_ticker(symbol)

        if not ticker:
            msg = f"No ticker data found for {symbol} on {exchange}"
            ccxt_logger.warning(msg)
            return msg

        # Format timestamp
        timestamp_str = "N/A"
        if ticker.get("timestamp"):
            timestamp_str = _timestamp_to_datetime(ticker["timestamp"])

        # Build output
        lines = [
            f"# Ticker data for {symbol} from {exchange}",
            f"Symbol: {ticker.get('symbol', symbol)}",
            f"Timestamp: {timestamp_str}",
            f"Bid: {ticker.get('bid', 'N/A')}",
            f"Ask: {ticker.get('ask', 'N/A')}",
            f"Last Price: {ticker.get('last', 'N/A')}",
            f"High 24h: {ticker.get('high', 'N/A')}",
            f"Low 24h: {ticker.get('low', 'N/A')}",
            f"Volume 24h: {ticker.get('baseVolume', 'N/A')}",
        ]

        ccxt_logger.debug(f"Retrieved ticker for {symbol}")
        return "\n".join(lines)

    except ccxt.RateLimitExceeded as e:
        raise CCXTRateLimitError(str(e), exchange=exchange) from e
    except Exception as e:
        error_msg = f"Error fetching crypto ticker for {symbol} from {exchange}"
        ccxt_logger.error(f"{error_msg}: {e}")
        raise VendorError(
            error_msg,
            function="get_crypto_ticker",
            vendor="ccxt",
            params={"symbol": symbol, "exchange": exchange},
            original_error=e,
        )


def get_crypto_orderbook(
    symbol: Annotated[str, "trading pair like BTC/USD, ETH/USD"],
    depth: Annotated[int, "number of price levels to fetch"] = 20,
    exchange: Annotated[
        str, "exchange name: coinbase, binance, kraken, etc."
    ] = "coinbase",
) -> str:
    """Fetch order book data for a cryptocurrency trading pair."""
    ccxt_logger.info(f"Fetching crypto order book for {symbol} from {exchange}")

    try:
        ex = _get_exchange(exchange)
        orderbook = ex.fetch_order_book(symbol, limit=depth)

        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        if not bids and not asks:
            msg = f"No order book data found for {symbol} on {exchange}"
            ccxt_logger.warning(msg)
            return msg

        # Build output
        lines = [f"# Order Book for {symbol} from {exchange}"]

        lines.extend(("## Bids (Buy Orders)", "price,amount"))
        for bid in bids[:depth]:
            lines.append(f"{bid[0]},{bid[1]}")

        lines.append("")

        lines.extend(("## Asks (Sell Orders)", "price,amount"))
        for ask in asks[:depth]:
            lines.append(f"{ask[0]},{ask[1]}")

        # Summary section
        lines.append("")

        lines.extend(("## Summary", f"Best Bid: {bids[0][0] if bids else 'N/A'}"))
        lines.append(f"Best Ask: {asks[0][0] if asks else 'N/A'}")
        spread = float(asks[0][0]) - float(bids[0][0]) if bids and asks else "N/A"
        lines.append(f"Spread: {spread}")

        ccxt_logger.debug(f"Retrieved order book for {symbol}")
        return "\n".join(lines)

    except ccxt.RateLimitExceeded as e:
        raise CCXTRateLimitError(str(e), exchange=exchange) from e
    except Exception as e:
        error_msg = f"Error fetching crypto order book for {symbol} from {exchange}"
        ccxt_logger.error(f"{error_msg}: {e}")
        raise VendorError(
            error_msg,
            function="get_crypto_orderbook",
            vendor="ccxt",
            params={"symbol": symbol, "depth": depth, "exchange": exchange},
            original_error=e,
        )


__all__ = [
    "get_crypto_candles",
    "get_crypto_orderbook",
    "get_crypto_ticker",
]
