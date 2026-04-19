"""Unit tests for dataflows exception hierarchy."""


# ruff: noqa: TRY003 - long exception messages in test mocks are acceptable
# ruff: noqa: EM101 - string literals in test exceptions are acceptable
# ruff: noqa: TRY301 - raise in inner function is acceptable for testing
# ruff: noqa: PT017 - assert on exception in except block is acceptable

import pytest

from dataflows.exceptions import (
    ConfigurationError,
    DataFetchError,
    NetworkError,
    RateLimitError,
    ValidationError,
    VendorError,
)


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    def test_vendor_error_is_data_fetch_error(self):
        """VendorError should inherit from DataFetchError."""
        e = VendorError("test")
        assert isinstance(e, DataFetchError)
        assert isinstance(e, Exception)

    def test_rate_limit_error_is_data_fetch_error(self):
        """RateLimitError should inherit from DataFetchError."""
        e = RateLimitError("test")
        assert isinstance(e, DataFetchError)

    def test_validation_error_is_data_fetch_error(self):
        """ValidationError should inherit from DataFetchError."""
        e = ValidationError("test")
        assert isinstance(e, DataFetchError)

    def test_configuration_error_is_data_fetch_error(self):
        """ConfigurationError should inherit from DataFetchError."""
        e = ConfigurationError("test")
        assert isinstance(e, DataFetchError)

    def test_network_error_is_data_fetch_error(self):
        """NetworkError should inherit from DataFetchError."""
        e = NetworkError("test")
        assert isinstance(e, DataFetchError)


class TestExceptionContext:
    """Tests for exception context preservation."""

    def test_vendor_error_stores_context(self):
        """VendorError should store and format context information."""
        e = VendorError(
            "API failed",
            function="get_stock",
            vendor="alpha_vantage",
            params={"symbol": "AAPL"},
        )
        assert e.function == "get_stock"
        assert e.vendor == "alpha_vantage"
        assert e.params == {"symbol": "AAPL"}
        assert "get_stock" in str(e)
        assert "alpha_vantage" in str(e)

    def test_exception_with_original_error(self):
        """Exception should store original error reference."""
        original = ValueError("original error")
        e = VendorError("wrapped", original_error=original)
        assert e.original_error is original
        assert isinstance(e.original_error, ValueError)

    def test_exception_str_includes_message(self):
        """Exception string representation should include the message."""
        e = ValidationError("Invalid symbol")
        assert "Invalid symbol" in str(e)

    def test_data_fetch_error_default_params(self):
        """DataFetchError should initialize with default empty params."""
        e = DataFetchError("test error")
        assert e.params == {}
        assert e.function is None
        assert e.vendor is None
        assert e.original_error is None

    def test_exception_format_message_with_all_context(self):
        """Exception message should include all context when provided."""
        e = DataFetchError(
            "Error occurred",
            function="fetch_data",
            vendor="yfinance",
            params={"ticker": "MSFT"},
        )
        message = str(e)
        assert "Error occurred" in message
        assert "fetch_data" in message
        assert "yfinance" in message
        assert "ticker=MSFT" in message


class TestRateLimitError:
    """Tests for RateLimitError specific functionality."""

    def test_rate_limit_error_with_retry_after(self):
        """RateLimitError should store retry_after value."""
        e = RateLimitError("Rate limit exceeded", retry_after=60)
        assert e.retry_after == 60
        assert "60s" in str(e)

    def test_rate_limit_error_without_retry_after(self):
        """RateLimitError should work without retry_after."""
        e = RateLimitError("Rate limit exceeded")
        assert e.retry_after is None
        assert "Retry after" not in str(e)

    def test_rate_limit_error_with_context(self):
        """RateLimitError should preserve all context."""
        e = RateLimitError(
            "Too many requests",
            function="get_prices",
            vendor="alpha_vantage",
            params={"symbol": "TSLA"},
            retry_after=30,
        )
        assert e.function == "get_prices"
        assert e.vendor == "alpha_vantage"
        assert e.params == {"symbol": "TSLA"}
        assert e.retry_after == 30
        message = str(e)
        assert "Too many requests" in message
        assert "get_prices" in message
        assert "alpha_vantage" in message
        assert "30s" in message


class TestExceptionRaising:
    """Tests for raising and catching exceptions."""

    def test_raise_and_catch_vendor_error(self):
        """Should be able to raise and catch VendorError."""
        with pytest.raises(VendorError, match="API failed"):
            raise VendorError("API failed")

    def test_catch_as_base_class(self):
        """Should be able to catch subclass as base DataFetchError."""
        with pytest.raises(DataFetchError):
            raise VendorError("test")

    def test_rate_limit_error_message(self):
        """Should be able to catch RateLimitError with message match."""
        with pytest.raises(RateLimitError, match="Rate limit"):
            raise RateLimitError("Rate limit exceeded for Alpha Vantage")

    def test_catch_validation_error(self):
        """Should be able to raise and catch ValidationError."""
        with pytest.raises(ValidationError, match="Invalid"):
            raise ValidationError("Invalid input data")

    def test_catch_configuration_error(self):
        """Should be able to raise and catch ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Missing"):
            raise ConfigurationError("Missing API key")

    def test_catch_network_error(self):
        """Should be able to raise and catch NetworkError."""
        with pytest.raises(NetworkError, match="Connection"):
            raise NetworkError("Connection timeout")


class TestExceptionChaining:
    """Tests for exception chaining behavior."""

    def test_original_error_preserved(self):
        """Original error should be preserved for debugging."""
        original = ConnectionError("Network unreachable")
        e = NetworkError("Failed to fetch data", original_error=original)
        assert e.original_error == original
        assert str(e.original_error) == "Network unreachable"

    def test_nested_exception_context(self):
        """Should handle nested exception context."""
        try:
            try:
                raise ValueError("Invalid JSON")
            except ValueError as ve:
                raise ValidationError(
                    "Data validation failed",
                    function="parse_response",
                    original_error=ve,
                )
        except ValidationError as e:
            assert e.function == "parse_response"
            assert isinstance(e.original_error, ValueError)
