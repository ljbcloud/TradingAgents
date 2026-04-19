"""
Shared utilities for CCXT cryptocurrency exchange interactions.

Provides common functions for API key retrieval, exchange configuration,
and error handling used across CCXT-based cryptocurrency data modules.
"""

import os
import re
from typing import Any

import ccxt

from .exceptions import ConfigurationError, VendorError
from .logging_config import get_logger

ccxt_logger = get_logger("ccxt")

# Pattern for reasonable API key format (alphanumeric, typically 16+ chars)
CCXT_API_KEY_PATTERN = re.compile(r"^[A-Za-z0-9]{16,}$")

# Supported exchanges with their CCXT class names
SUPPORTED_EXCHANGES: dict[str, str] = {
    "coinbase": "coinbase",
    "coinbasepro": "coinbasepro",
    "binance": "binance",
    "kraken": "kraken",
    "bybit": "bybit",
    "okx": "okx",
    "huobi": "huobi",
    "bitfinex": "bitfinex",
    "kucoin": "kucoin",
    "gate": "gateio",
    "gateio": "gateio",
    "gemini": "gemini",
    "bitstamp": "bitstamp",
}


class CCXTRateLimitError(Exception):
    """Exception raised when CCXT exchange API rate limit is exceeded.

    This exception wraps CCXT's rate limit errors for consistent error handling
    across the dataflows module.
    """

    def __init__(self, message: str, exchange: str | None = None) -> None:
        """Initialize CCXTRateLimitError.

        Args:
            message: Human-readable error description
            exchange: Name of the exchange that enforced the rate limit
        """
        self.message = message
        self.exchange = exchange
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with exchange context."""
        if self.exchange:
            return f"CCXT rate limit exceeded on {self.exchange}: {self.message}"
        return f"CCXT rate limit exceeded: {self.message}"

    def __str__(self) -> str:
        """Return formatted error message."""
        return self._format_message()


def validate_ccxt_key(api_key: str | None, name: str = "CCXT") -> str:
    """Validate CCXT API key format.

    CCXT API keys are typically 16+ alphanumeric characters, though formats
    vary by exchange. This performs basic format validation.

    Args:
        api_key: The API key to validate
        name: Name of the exchange for error messages (default: "CCXT")

    Returns:
        The validated API key

    Raises:
        ConfigurationError: If key is missing or format is invalid
    """
    if not api_key:
        msg = f"{name} API key is missing. Set {name.upper()}_API_KEY environment variable."
        raise ConfigurationError(msg, function="validate_ccxt_key")

    if not CCXT_API_KEY_PATTERN.match(api_key):
        msg = f"Invalid {name} API key format. Expected 16+ alphanumeric characters, got: {api_key[:4]}..."
        raise ConfigurationError(msg, function="validate_ccxt_key")

    return api_key


def get_exchange_credentials(exchange_name: str) -> dict[str, str]:
    """Get API credentials for an exchange from environment variables.

    Reads credentials from environment variables following the pattern:
    - {EXCHANGE_NAME}_API_KEY
    - {EXCHANGE_NAME}_API_SECRET

    For example, for Coinbase:
    - COINBASE_API_KEY
    - COINBASE_API_SECRET

    Args:
        exchange_name: Name of the exchange (e.g., "coinbase", "binance")

    Returns:
        Dictionary with "apiKey" and "secret" keys for CCXT configuration

    Raises:
        ConfigurationError: If API key or secret is missing
    """
    exchange_upper = exchange_name.upper()
    api_key = os.environ.get(f"{exchange_upper}_API_KEY")
    api_secret = os.environ.get(f"{exchange_upper}_API_SECRET")

    if not api_key:
        msg = (
            f"{exchange_name} API key is missing. "
            f"Set {exchange_upper}_API_KEY environment variable."
        )
        raise ConfigurationError(msg, function="get_exchange_credentials")

    if not api_secret:
        msg = (
            f"{exchange_name} API secret is missing. "
            f"Set {exchange_upper}_API_SECRET environment variable."
        )
        raise ConfigurationError(msg, function="get_exchange_credentials")

    ccxt_logger.debug("Retrieved credentials for %s", exchange_name)

    return {
        "apiKey": api_key,
        "secret": api_secret,
    }


def create_exchange(
    exchange_name: str = "coinbase",
    *,
    credentials: dict[str, str] | None = None,
    extra_config: dict[str, Any] | None = None,
) -> ccxt.Exchange:
    """Create and configure a CCXT exchange instance.

    Creates an exchange instance with rate limiting enabled and optional
    custom configuration. If credentials are not provided, they will be
    loaded from environment variables.

    Args:
        exchange_name: Name of the exchange (default: "coinbase").
                       Supported: coinbase, binance, kraken, bybit, okx,
                       huobi, bitfinex, kucoin, gate, gateio, gemini, bitstamp
        credentials: Optional credentials dict with "apiKey" and "secret".
                     If None, loads from environment variables.
        extra_config: Additional CCXT configuration options to merge

    Returns:
        Configured CCXT Exchange instance

    Raises:
        VendorError: If the exchange name is not supported or creation fails
        ConfigurationError: If credentials are required but not found
    """
    normalized_name = exchange_name.lower().strip()

    if normalized_name not in SUPPORTED_EXCHANGES:
        available = ", ".join(sorted(SUPPORTED_EXCHANGES.keys()))
        msg = (
            f"Unsupported exchange: '{exchange_name}'. Supported exchanges: {available}"
        )
        ccxt_logger.error(msg)
        raise VendorError(
            msg,
            function="create_exchange",
            vendor="ccxt",
            params={"exchange_name": exchange_name},
        )

    ccxt_class_name = SUPPORTED_EXCHANGES[normalized_name]

    try:
        exchange_class = getattr(ccxt, ccxt_class_name)
    except AttributeError as e:
        msg = f"CCXT exchange class '{ccxt_class_name}' not found"
        ccxt_logger.exception(msg)
        raise VendorError(
            msg,
            function="create_exchange",
            vendor="ccxt",
            params={"exchange_name": exchange_name, "ccxt_class": ccxt_class_name},
            original_error=e,
        ) from e

    config: dict[str, Any] = {
        "enableRateLimit": True,
    }

    if credentials:
        config["apiKey"] = credentials.get("apiKey", "")
        config["secret"] = credentials.get("secret", "")
    else:
        try:
            env_credentials = get_exchange_credentials(exchange_name)
            config["apiKey"] = env_credentials["apiKey"]
            config["secret"] = env_credentials["secret"]
        except ConfigurationError:
            ccxt_logger.warning(
                "No credentials found for %s. Some operations may be limited.",
                exchange_name,
            )

    if extra_config:
        config.update(extra_config)

    try:
        exchange = exchange_class(config)
        ccxt_logger.info("Created %s exchange instance", ccxt_class_name)
        return exchange
    except Exception as e:
        msg = f"Failed to create {ccxt_class_name} exchange instance"
        ccxt_logger.exception(msg)
        raise VendorError(
            msg,
            function="create_exchange",
            vendor="ccxt",
            params={"exchange_name": exchange_name, "config": config},
            original_error=e,
        ) from e


__all__ = [
    "CCXT_API_KEY_PATTERN",
    "SUPPORTED_EXCHANGES",
    "CCXTRateLimitError",
    "ccxt_logger",
    "create_exchange",
    "get_exchange_credentials",
    "validate_ccxt_key",
]
