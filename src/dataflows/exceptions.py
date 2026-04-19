"""
Custom exception hierarchy for dataflows module.

This module defines a structured exception hierarchy for handling data fetch errors
across different vendors and data sources. All exceptions inherit from DataFetchError,
providing consistent error handling and context information throughout the dataflows
module.

Exception Hierarchy:
    DataFetchError (base)
        ├── VendorError (vendor-specific errors)
        ├── RateLimitError (API rate limit exceeded)
        ├── ValidationError (invalid input/output data)
        ├── ConfigurationError (configuration issues)
        └── NetworkError (network connectivity problems)

Usage Example:
    >>> from dataflows.exceptions import VendorError
    >>> raise VendorError(
    ...     message="API key invalid",
    ...     function="fetch_stock_data",
    ...     vendor="alpha_vantage",
    ...     params={"symbol": "AAPL"}
    ... )

All exceptions include context information for debugging:
- message: Human-readable error description
- function: Name of the function where error occurred
- vendor: Data vendor name (if applicable)
- params: Function parameters (if available)
"""

from typing import Any


class DataFetchError(Exception):
    """Base exception for all data fetch errors in the dataflows module.

    Attributes:
        message: Human-readable error description
        function: Name of the function where the error occurred
        vendor: Data vendor name (optional)
        params: Function parameters that caused the error (optional)
        original_error: Original exception that triggered this error (optional)
    """

    def __init__(
        self,
        message: str,
        *,
        function: str | None = None,
        vendor: str | None = None,
        params: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize DataFetchError with context information.

        Args:
            message: Human-readable error description
            function: Name of the function where the error occurred
            vendor: Data vendor name (if applicable)
            params: Function parameters that caused the error (if available)
            original_error: Original exception that triggered this error
        """
        self.message = message
        self.function = function
        self.vendor = vendor
        self.params = params or {}
        self.original_error = original_error

        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with context information.

        Returns:
            Formatted error string including all available context
        """
        parts = [self.message]

        if self.function:
            parts.append(f"Function: {self.function}")

        if self.vendor:
            parts.append(f"Vendor: {self.vendor}")

        if self.params:
            param_str = ", ".join(f"{k}={v}" for k, v in self.params.items())
            parts.append(f"Params: {param_str}")

        return " | ".join(parts)

    def __str__(self) -> str:
        """Return formatted error message."""
        return self._format_message()


class VendorError(DataFetchError):
    """Exception raised when a data vendor returns an error response.

    This exception captures vendor-specific errors such as invalid API keys,
    unsupported symbols, or service unavailable messages from the vendor's API.
    """


class RateLimitError(DataFetchError):
    """Exception raised when API rate limits are exceeded.

    This exception indicates that the vendor's API rate limit has been reached.
    The calling code should implement backoff/retry logic or wait before retrying.

    Attributes:
        message: Error description
        function: Function name where error occurred
        vendor: Vendor that enforced the rate limit
        params: Function parameters
        retry_after: Optional suggested retry time in seconds
    """

    def __init__(
        self,
        message: str,
        *,
        function: str | None = None,
        vendor: str | None = None,
        params: dict[str, Any] | None = None,
        retry_after: int | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize RateLimitError with retry information.

        Args:
            message: Error description
            function: Function name where error occurred
            vendor: Vendor that enforced the rate limit
            params: Function parameters
            retry_after: Suggested retry time in seconds (from vendor response)
            original_error: Original exception
        """
        self.retry_after = retry_after
        super().__init__(
            message,
            function=function,
            vendor=vendor,
            params=params,
            original_error=original_error,
        )

    def _format_message(self) -> str:
        """Format message with retry information."""
        base_message = super()._format_message()
        if self.retry_after:
            return f"{base_message} | Retry after: {self.retry_after}s"
        return base_message


class ValidationError(DataFetchError):
    """Exception raised when input/output validation fails.

    This exception indicates that data validation checks failed, such as:
    - Invalid function parameters
    - Malformed API responses
    - Missing required fields
    - Data type mismatches
    """


class ConfigurationError(DataFetchError):
    """Exception raised when configuration is invalid or missing.

    This exception indicates configuration problems such as:
    - Missing API keys
    - Invalid configuration values
    - Unsupported configuration combinations
    - Required configuration settings not set
    """


class NetworkError(DataFetchError):
    """Exception raised when network-related errors occur.

    This exception indicates network connectivity problems such as:
    - Connection timeout
    - DNS resolution failure
    - SSL/TLS certificate errors
    - Connection refused
    """
