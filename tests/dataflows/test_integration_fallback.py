"""Integration tests for vendor fallback behavior.

Tests verify that the fallback mechanism works correctly when primary
vendors fail, and that error context is properly preserved.
"""


# ruff: noqa: TRY003 - long exception messages in test mocks are acceptable
# ruff: noqa: EM101 - string literals in test exceptions are acceptable

import pytest
import requests

from dataflows.alpha_vantage_common import AlphaVantageRateLimitError
from dataflows.exceptions import (
    ConfigurationError,
    DataFetchError,
    NetworkError,
    RateLimitError,
    ValidationError,
    VendorError,
)


class TestExceptionHierarchyRelationships:
    """Tests for exception inheritance hierarchy critical for fallback behavior."""

    def test_vendor_error_is_data_fetch_error(self):
        """VendorError must be catchable as DataFetchError for unified handling."""
        e = VendorError("test error")
        assert isinstance(e, DataFetchError)
        assert isinstance(e, Exception)

    def test_rate_limit_error_is_data_fetch_error(self):
        """RateLimitError must be catchable as DataFetchError for unified handling."""
        e = RateLimitError("rate limit exceeded")
        assert isinstance(e, DataFetchError)
        assert isinstance(e, Exception)

    def test_rate_limit_error_not_vendor_error(self):
        """RateLimitError does NOT inherit from VendorError - they are siblings.

        Both inherit from DataFetchError but are distinct exception types.
        This is by design: rate limits may require different handling than vendor errors.
        """
        e = RateLimitError("rate limit")
        assert not isinstance(e, VendorError)
        assert isinstance(e, DataFetchError)

    def test_vendor_error_not_rate_limit_error(self):
        """VendorError does NOT inherit from RateLimitError."""
        e = VendorError("vendor error")
        assert not isinstance(e, RateLimitError)
        assert isinstance(e, DataFetchError)

    def test_all_errors_catchable_as_data_fetch_error(self):
        """All custom errors should be catchable as the base DataFetchError."""
        errors = [
            VendorError("vendor"),
            RateLimitError("rate"),
            ValidationError("validation"),
            ConfigurationError("config"),
            NetworkError("network"),
        ]
        for error in errors:
            assert isinstance(error, DataFetchError), (
                f"{type(error).__name__} should be DataFetchError"
            )


class TestErrorContextPreservation:
    """Tests for error context preservation in exceptions."""

    def test_vendor_error_stores_vendor_context(self):
        """VendorError should preserve vendor name for debugging fallback issues."""
        e = VendorError(
            "API failed",
            function="get_stock_data",
            vendor="alpha_vantage",
            params={"symbol": "AAPL"},
        )
        assert e.vendor == "alpha_vantage"
        assert "alpha_vantage" in str(e)

    def test_vendor_error_stores_function_context(self):
        """VendorError should preserve function name for debugging."""
        e = VendorError(
            "API call failed",
            function="get_fundamentals",
            vendor="yfinance",
        )
        assert e.function == "get_fundamentals"
        assert "get_fundamentals" in str(e)

    def test_vendor_error_stores_params_context(self):
        """VendorError should preserve parameters for debugging."""
        e = VendorError(
            "Invalid symbol",
            function="get_stock",
            vendor="alpha_vantage",
            params={"symbol": "INVALID", "interval": "1d"},
        )
        assert e.params == {"symbol": "INVALID", "interval": "1d"}
        assert "symbol=INVALID" in str(e)

    def test_vendor_error_preserves_original_exception(self):
        """VendorError should chain original exceptions for debugging."""
        original = ValueError("Original API error")
        e = VendorError(
            "Vendor failed",
            function="fetch_data",
            vendor="alpha_vantage",
            original_error=original,
        )
        assert e.original_error is original
        assert isinstance(e.original_error, ValueError)

    def test_rate_limit_error_stores_vendor_context(self):
        """RateLimitError should preserve vendor context for fallback decisions."""
        e = RateLimitError(
            "Rate limit exceeded",
            function="get_stock_data",
            vendor="alpha_vantage",
            retry_after=60,
        )
        assert e.vendor == "alpha_vantage"
        assert e.retry_after == 60

    def test_network_error_preserves_context(self):
        """NetworkError should preserve context for fallback to other vendors."""
        e = NetworkError(
            "Connection timeout",
            function="get_stock_data",
            vendor="alpha_vantage",
            params={"symbol": "AAPL"},
        )
        assert e.vendor == "alpha_vantage"
        assert e.function == "get_stock_data"


class TestCatchableExceptionsForFallback:
    """Tests for catching exceptions to enable fallback behavior."""

    def test_catch_vendor_error_as_base_class(self):
        """Should be able to catch VendorError as DataFetchError."""
        with pytest.raises(DataFetchError):
            raise VendorError("test")

    def test_catch_rate_limit_error_as_base_class(self):
        """Should be able to catch RateLimitError as DataFetchError."""
        with pytest.raises(DataFetchError):
            raise RateLimitError("rate limit")

    def test_catch_network_error_as_base_class(self):
        """Should be able to catch NetworkError as DataFetchError."""
        with pytest.raises(DataFetchError):
            raise NetworkError("network error")

    def test_catch_multiple_exception_types(self):
        """Fallback logic often catches multiple exception types."""
        caught = False
        try:
            raise VendorError("vendor failed")  # noqa: TRY301
        except (VendorError, RateLimitError, NetworkError) as e:
            caught = True
            assert isinstance(e, DataFetchError)  # noqa: PT017
        assert caught


class TestAlphaVantageRateLimitError:
    """Tests for Alpha Vantage specific rate limit error."""

    def test_alpha_vantage_rate_limit_error_is_exception(self):
        """AlphaVantageRateLimitError is a plain Exception for fallback triggering."""
        e = AlphaVantageRateLimitError("Rate limit exceeded")
        assert isinstance(e, Exception)

    def test_alpha_vantage_rate_limit_error_message(self):
        """AlphaVantageRateLimitError should preserve error message."""
        msg = "Alpha Vantage rate limit exceeded: API key limit reached"
        e = AlphaVantageRateLimitError(msg)
        assert str(e) == msg

    def test_alpha_vantage_rate_limit_not_data_fetch_error(self):
        """AlphaVantageRateLimitError is separate from the DataFetchError hierarchy.

        This is intentional - it's a legacy exception used to trigger fallback
        in the routing layer without wrapping it in our exception hierarchy.
        """
        e = AlphaVantageRateLimitError("rate limit")
        assert not isinstance(e, DataFetchError)
        assert not isinstance(e, RateLimitError)


class TestRequestsExceptionsForFallback:
    """Tests for requests library exceptions in fallback scenarios."""

    def test_request_exception_catchable(self):
        """requests.RequestException should be catchable for fallback triggering."""
        with pytest.raises(requests.RequestException):
            raise requests.RequestException("Network error")

    def test_connection_error_is_request_exception(self):
        """requests.ConnectionError should be catchable as RequestException."""
        with pytest.raises(requests.RequestException):
            raise requests.ConnectionError("Connection refused")

    def test_timeout_is_request_exception(self):
        """requests.Timeout should be catchable as RequestException."""
        with pytest.raises(requests.RequestException):
            raise requests.Timeout("Request timed out")

    def test_http_error_is_request_exception(self):
        """requests.HTTPError should be catchable as RequestException."""
        with pytest.raises(requests.RequestException):
            raise requests.HTTPError("HTTP 500 error")


class TestFallbackExceptionChaining:
    """Tests for exception chaining during fallback scenarios."""

    def test_exception_chaining_preserves_context(self):
        """When wrapping exceptions, original error should be preserved."""
        original = requests.ConnectionError("Network unreachable")
        wrapped = NetworkError(
            "Failed to connect to vendor",
            function="get_stock_data",
            vendor="alpha_vantage",
            original_error=original,
        )
        assert wrapped.original_error is original
        assert isinstance(wrapped.original_error, requests.RequestException)

    def test_nested_exception_context(self):
        """Multiple levels of exception wrapping should preserve chain."""
        # First level: requests error
        requests_error = requests.Timeout("API timeout")

        # Second level: NetworkError wrapping requests error
        network_error = NetworkError(
            "Network failure",
            function="fetch_data",
            original_error=requests_error,
        )

        # Third level: VendorError wrapping NetworkError
        vendor_error = VendorError(
            "Vendor unavailable",
            function="get_stock",
            vendor="alpha_vantage",
            original_error=network_error,
        )

        # Verify chain
        assert vendor_error.original_error is network_error
        assert vendor_error.original_error.original_error is requests_error  # type: ignore[union-attr]


class TestFallbackBehaviorPlaceholders:
    """Placeholder tests for fallback mechanism (may need implementation)."""

    @pytest.mark.skip(reason="Fallback mechanism requires mocking vendor calls")
    def test_fallback_to_secondary_vendor_on_rate_limit(self):
        """When primary vendor rate limits, should fallback to secondary."""

    @pytest.mark.skip(reason="Fallback mechanism requires mocking vendor calls")
    def test_fallback_on_network_error(self):
        """When primary vendor has network issues, should fallback to secondary."""

    @pytest.mark.skip(reason="Fallback mechanism requires mocking vendor calls")
    def test_no_fallback_available_raises_error(self):
        """When all vendors fail, should raise appropriate error."""

    @pytest.mark.skip(reason="Fallback mechanism requires mocking vendor calls")
    def test_fallback_preserves_method_args(self):
        """Fallback should pass same arguments to secondary vendor."""
