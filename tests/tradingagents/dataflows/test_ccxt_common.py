"""Unit tests for CCXT common utilities."""

# ruff: noqa: S101 - assert is expected in tests

from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.exceptions import ConfigurationError, VendorError


@pytest.mark.unit
class TestValidateCCXTKey:
    """Tests for CCXT API key validation."""

    def test_valid_key_returns_key(self):
        """validate_ccxt_key should return the key unchanged when valid."""
        from tradingagents.dataflows.ccxt_common import validate_ccxt_key

        result = validate_ccxt_key("validapikey12345678")
        assert result == "validapikey12345678"

    def test_missing_key_raises_configuration_error(self):
        """validate_ccxt_key should raise ConfigurationError for None key."""
        from tradingagents.dataflows.ccxt_common import validate_ccxt_key

        with pytest.raises(ConfigurationError, match="API key"):
            validate_ccxt_key(None)

    def test_empty_key_raises_configuration_error(self):
        """validate_ccxt_key should raise ConfigurationError for empty string key."""
        from tradingagents.dataflows.ccxt_common import validate_ccxt_key

        with pytest.raises(ConfigurationError, match="API key"):
            validate_ccxt_key("")


@pytest.mark.unit
class TestGetExchangeCredentials:
    """Tests for retrieving exchange credentials from environment."""

    def test_returns_credentials_from_env(self):
        """get_exchange_credentials should return credentials dict from env vars."""
        from tradingagents.dataflows.ccxt_common import get_exchange_credentials

        with patch.dict(
            "os.environ",
            {
                "COINBASE_API_KEY": "test_api_key_here",
                "COINBASE_API_SECRET": "test_api_secret_1",
            },
        ):
            result = get_exchange_credentials("coinbase")
            assert result == {
                "apiKey": "test_api_key_here",
                "secret": "test_api_secret_1",
            }

    def test_missing_key_raises_error(self):
        """get_exchange_credentials should raise when no env vars set."""
        from tradingagents.dataflows.ccxt_common import get_exchange_credentials

        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ConfigurationError, match="API key"),
        ):
            get_exchange_credentials("coinbase")

    def test_missing_secret_raises_error(self):
        """get_exchange_credentials should raise when secret is missing."""
        from tradingagents.dataflows.ccxt_common import get_exchange_credentials

        with (
            patch.dict(
                "os.environ",
                {"COINBASE_API_KEY": "test_api_key_here"},
                clear=True,
            ),
            pytest.raises(ConfigurationError, match="API secret"),
        ):
            get_exchange_credentials("coinbase")


@pytest.mark.unit
class TestCreateExchange:
    """Tests for CCXT exchange creation."""

    def test_creates_coinbase_exchange(self):
        """create_exchange should create a Coinbase exchange instance."""
        from tradingagents.dataflows.ccxt_common import create_exchange

        mock_exchange = MagicMock()
        mock_exchange.id = "coinbase"

        with patch(
            "tradingagents.dataflows.ccxt_common.ccxt.coinbase",
            return_value=mock_exchange,
        ):
            exchange = create_exchange("coinbase")
            assert exchange.id == "coinbase"

    def test_creates_exchange_with_rate_limiting(self):
        """create_exchange should enable rate limiting by default."""
        from tradingagents.dataflows.ccxt_common import create_exchange

        mock_exchange = MagicMock()
        mock_exchange.id = "coinbase"

        with patch(
            "tradingagents.dataflows.ccxt_common.ccxt.coinbase",
            return_value=mock_exchange,
        ) as mock_ccxt:
            create_exchange("coinbase")
            call_args = mock_ccxt.call_args
            assert call_args[0][0].get("enableRateLimit") is True

    def test_unknown_exchange_raises_vendor_error(self):
        """create_exchange should raise VendorError for unknown exchange."""
        from tradingagents.dataflows.ccxt_common import create_exchange

        with pytest.raises(VendorError, match="Unsupported exchange"):
            create_exchange("nonexistent_exchange")


@pytest.mark.unit
class TestCCXTRateLimitError:
    """Tests for CCXT rate limit error exception."""

    def test_is_exception(self):
        """CCXTRateLimitError should be a subclass of Exception."""
        from tradingagents.dataflows.ccxt_common import CCXTRateLimitError

        error = CCXTRateLimitError("Rate limit exceeded")
        assert isinstance(error, Exception)
