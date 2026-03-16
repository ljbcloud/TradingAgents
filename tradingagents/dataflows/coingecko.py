"""
CoinGecko API vendor implementation for cryptocurrency fundamentals.

Provides functions to retrieve cryptocurrency tokenomics data including
market cap, supply information, and price changes using the CoinGecko API.
No API key required for free tier access.
"""

from typing import Annotated

import requests

from .exceptions import VendorError
from .logging_config import get_logger

coingecko_logger = get_logger("coingecko")

# CoinGecko API base URL (free tier, no API key required)
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"

# Common symbol to CoinGecko ID mappings
SYMBOL_TO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "SOL": "solana",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "SHIB": "shiba-inu",
    "TRX": "tron",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "ATOM": "cosmos",
    "UNI": "uniswap",
    "XMR": "monero",
    "ETC": "ethereum-classic",
    "XLM": "stellar",
    "BCH": "bitcoin-cash",
    "NEAR": "near",
    "FIL": "filecoin",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "INJ": "injective-protocol",
    "HBAR": "hedera-hashgraph",
    "VET": "vechain",
    "ICP": "internet-computer",
    "FET": "fetch-ai",
    "RENDER": "render-token",
    "IMX": "immutable-x",
}


def _get_coingecko_id(symbol: str) -> str | None:
    """Map cryptocurrency symbol to CoinGecko coin ID.

    Handles various symbol formats:
    - Plain symbols: BTC, ETH
    - Pair formats: BTC-USD, ETH/USDT, SOL-USD

    Args:
        symbol: Cryptocurrency symbol (e.g., BTC, ETH, BTC-USD, ETH/USDT)

    Returns:
        CoinGecko coin ID or None if not found in mapping
    """
    normalized = symbol.upper().strip()

    # Extract base currency from pair formats (e.g., "BTC-USD" -> "BTC", "ETH/USDT" -> "ETH")
    for separator in ("/", "-"):
        if separator in normalized:
            normalized = normalized.split(separator)[0]
            break

    return SYMBOL_TO_ID.get(normalized)


def _search_coin_by_symbol(symbol: str) -> str | None:
    """Search for coin ID using CoinGecko search endpoint.

    Args:
        symbol: Cryptocurrency symbol to search for

    Returns:
        CoinGecko coin ID if found, None otherwise
    """
    try:
        response = requests.get(
            f"{COINGECKO_API_BASE}/search",
            params={"query": symbol},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        coins = data.get("coins", [])
        if coins:
            # Return the first match (most relevant)
            return coins[0].get("id")
        return None
    except Exception:
        return None


def _format_large_number(value: float | None) -> str:
    """Format large numbers with appropriate suffixes.

    Args:
        value: Numeric value to format

    Returns:
        Formatted string with suffix (K, M, B, T)
    """
    if value is None:
        return "N/A"

    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:.2f}"


def _format_supply(value: float | None) -> str:
    """Format supply numbers with appropriate suffixes.

    Args:
        value: Supply value to format

    Returns:
        Formatted string with suffix
    """
    if value is None:
        return "N/A"

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:,.0f}"


def get_crypto_token_info(
    symbol: Annotated[str, "cryptocurrency symbol like BTC, ETH, SOL"],
) -> str:
    """Fetch tokenomics data for a cryptocurrency.

    Retrieves market cap, circulating supply, total supply, max supply,
    and price change percentages from CoinGecko API.

    Args:
        symbol: Cryptocurrency symbol (e.g., BTC, ETH, SOL)

    Returns:
        Formatted string with tokenomics data including:
        - Market cap (USD)
        - Circulating supply
        - Total supply
        - Max supply
        - Price change percentages (1h, 24h, 7d)
        - Current price
        - All-time high and low

    Raises:
        VendorError: If the API request fails or coin is not found
    """
    coingecko_logger.info("Fetching tokenomics for %s", symbol)

    # Try to get CoinGecko ID from mapping first
    coin_id = _get_coingecko_id(symbol)

    # If not in mapping, search for it
    if not coin_id:
        coingecko_logger.debug("Symbol %s not in mapping, searching...", symbol)
        coin_id = _search_coin_by_symbol(symbol)

    if not coin_id:
        msg = f"Could not find CoinGecko ID for symbol: {symbol}"
        coingecko_logger.warning(msg)
        return msg

    try:
        # Fetch market data for the coin
        response = requests.get(
            f"{COINGECKO_API_BASE}/coins/{coin_id}/market_chart",
            params={
                "vs_currency": "usd",
                "days": "1",
            },
            timeout=30,
        )

        # If market_chart fails, try the coins endpoint
        if not response.ok:
            response = requests.get(
                f"{COINGECKO_API_BASE}/coins/{coin_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false",
                },
                timeout=30,
            )

        response.raise_for_status()
        data = response.json()

        # Extract market data
        market_data = data.get("market_data", {})
        if not market_data:
            msg = f"No market data available for {symbol}"
            coingecko_logger.warning(msg)
            return msg

        # Get current price
        current_price = market_data.get("current_price", {}).get("usd")

        # Get market cap
        market_cap = market_data.get("market_cap", {}).get("usd")
        market_cap_rank = data.get("market_cap_rank", "N/A")

        # Get supply information
        circulating_supply = market_data.get("circulating_supply")
        total_supply = market_data.get("total_supply")
        max_supply = market_data.get("max_supply")

        # Get price change percentages
        price_change_1h = market_data.get(
            "price_change_percentage_1h_in_currency", {}
        ).get("usd")
        price_change_24h = market_data.get("price_change_percentage_24h")
        price_change_7d = market_data.get("price_change_percentage_7d")

        # Get all-time high/low
        ath = market_data.get("ath", {}).get("usd")
        ath_change = market_data.get("ath_change_percentage", {}).get("usd")
        atl = market_data.get("atl", {}).get("usd")
        atl_change = market_data.get("atl_change_percentage", {}).get("usd")

        # Get fully diluted valuation
        fdv = market_data.get("fully_diluted_valuation", {}).get("usd")

        # Build output
        lines = [
            f"# Tokenomics for {symbol.upper()} ({coin_id})",
            "# Source: CoinGecko",
            "",
            "## Price Information",
            f"Current Price: ${current_price:,.4f}"
            if current_price
            else "Current Price: N/A",
            f"Market Cap Rank: #{market_cap_rank}"
            if market_cap_rank != "N/A"
            else "Market Cap Rank: N/A",
            "",
            "## Market Capitalization",
            f"Market Cap: {_format_large_number(market_cap)}",
            f"Fully Diluted Valuation: {_format_large_number(fdv)}",
            "",
            "## Supply Information",
            f"Circulating Supply: {_format_supply(circulating_supply)}",
            f"Total Supply: {_format_supply(total_supply)}",
            f"Max Supply: {_format_supply(max_supply)}",
            "",
            "## Price Changes",
        ]

        # Format price changes with +/- indicators
        if price_change_1h is not None:
            sign = "+" if price_change_1h >= 0 else ""
            lines.append(f"1 Hour: {sign}{price_change_1h:.2f}%")
        else:
            lines.append("1 Hour: N/A")

        if price_change_24h is not None:
            sign = "+" if price_change_24h >= 0 else ""
            lines.append(f"24 Hours: {sign}{price_change_24h:.2f}%")
        else:
            lines.append("24 Hours: N/A")

        if price_change_7d is not None:
            sign = "+" if price_change_7d >= 0 else ""
            lines.append(f"7 Days: {sign}{price_change_7d:.2f}%")
        else:
            lines.append("7 Days: N/A")

        lines.extend([
            "",
            "## All-Time High/Low",
            f"ATH: ${ath:,.4f}" if ath else "ATH: N/A",
        ])

        if ath_change is not None:
            sign = "+" if ath_change >= 0 else ""
            lines.append(f"ATH Change: {sign}{ath_change:.2f}%")
        else:
            lines.append("ATH Change: N/A")

        lines.append(f"ATL: ${atl:,.6f}" if atl else "ATL: N/A")

        if atl_change is not None:
            sign = "+" if atl_change >= 0 else ""
            lines.append(f"ATL Change: {sign}{atl_change:.2f}%")
        else:
            lines.append("ATL Change: N/A")

        coingecko_logger.debug("Retrieved tokenomics for %s", symbol)
        return "\n".join(lines)

    except requests.exceptions.Timeout:
        error_msg = f"CoinGecko API request timed out for {symbol}"
        coingecko_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_token_info",
            vendor="coingecko",
            params={"symbol": symbol},
        )
    except requests.exceptions.HTTPError as e:
        error_msg = f"CoinGecko API HTTP error for {symbol}"
        coingecko_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_token_info",
            vendor="coingecko",
            params={"symbol": symbol, "coin_id": coin_id},
            original_error=e,
        )
    except requests.exceptions.RequestException as e:
        error_msg = f"CoinGecko API request failed for {symbol}"
        coingecko_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_token_info",
            vendor="coingecko",
            params={"symbol": symbol},
            original_error=e,
        )
    except Exception as e:
        error_msg = f"Unexpected error fetching tokenomics for {symbol}"
        coingecko_logger.exception(error_msg)
        raise VendorError(
            error_msg,
            function="get_crypto_token_info",
            vendor="coingecko",
            params={"symbol": symbol},
            original_error=e,
        )


__all__ = [
    "get_crypto_token_info",
]
