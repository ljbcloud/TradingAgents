"""Tests for ticker validation module."""

from unittest.mock import MagicMock, patch

import pytest

from cli.ticker_validation import (
    TickerValidationResult,
    check_ambiguity,
    get_validated_ticker,
    search_ticker,
    validate_ticker,
)


class TestTickerValidationResult:
    def test_create_valid_result(self):
        result = TickerValidationResult(
            is_valid=True,
            symbol="AAPL",
            company_name="Apple Inc.",
            security_type="EQUITY",
        )
        assert result.is_valid is True
        assert result.symbol == "AAPL"
        assert result.company_name == "Apple Inc."
        assert result.security_type == "EQUITY"

    def test_create_invalid_result(self):
        result = TickerValidationResult(
            is_valid=False,
            symbol="INVALID",
            error_message="Ticker not found",
        )
        assert result.is_valid is False
        assert result.error_message == "Ticker not found"


class TestValidateTicker:
    def test_validate_ticker_function_exists(self):
        assert callable(validate_ticker)


class TestValidateTickerYFinance:
    @patch("cli.ticker_validation.yf.Ticker")
    def test_validate_valid_stock_ticker(self, mock_ticker_class):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Apple Inc.",
            "quoteType": "EQUITY",
            "symbol": "AAPL",
        }
        mock_ticker_class.return_value = mock_ticker

        result = validate_ticker("AAPL")

        assert result.is_valid is True
        assert result.symbol == "AAPL"
        assert result.company_name == "Apple Inc."
        assert result.security_type == "EQUITY"

    @patch("cli.ticker_validation.yf.Ticker")
    def test_validate_invalid_ticker_returns_invalid(self, mock_ticker_class):
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker_class.return_value = mock_ticker

        result = validate_ticker("INVALIDXYZ123")

        assert result.is_valid is False
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()

    @patch("cli.ticker_validation.yf.Ticker")
    def test_validate_crypto_ticker(self, mock_ticker_class):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Bitcoin USD",
            "quoteType": "CRYPTOCURRENCY",
            "symbol": "BTC-USD",
        }
        mock_ticker_class.return_value = mock_ticker

        result = validate_ticker("BTC-USD")

        assert result.is_valid is True
        assert result.security_type == "CRYPTOCURRENCY"

    @patch("cli.ticker_validation.yf.Ticker")
    def test_validate_handles_network_error_gracefully(self, mock_ticker_class):
        mock_ticker_class.side_effect = Exception("Network error")

        result = validate_ticker("AAPL")

        assert result.is_valid is True
        assert result.company_name is None


class TestSearchTicker:
    @patch("cli.ticker_validation.yf.Search")
    def test_search_returns_matches(self, mock_search_class):
        mock_search = MagicMock()
        mock_search.quotes = [
            {"symbol": "A", "shortname": "Agilent Technologies"},
            {"symbol": "AA", "shortname": "Alcoa Corporation"},
        ]
        mock_search_class.return_value = mock_search

        results = search_ticker("A")

        assert len(results) == 2
        assert results[0]["symbol"] == "A"

    @patch("cli.ticker_validation.yf.Search")
    def test_search_respects_threshold(self, mock_search_class):
        mock_search = MagicMock()
        mock_search.quotes = [
            {"symbol": f"TICK{i}", "shortname": f"Company {i}"} for i in range(10)
        ]
        mock_search_class.return_value = mock_search

        results = search_ticker("TICK", max_results=5)

        assert len(results) == 5

    @patch("cli.ticker_validation.yf.Search")
    def test_search_handles_empty_results(self, mock_search_class):
        mock_search = MagicMock()
        mock_search.quotes = []
        mock_search_class.return_value = mock_search

        results = search_ticker("NOTFOUND")

        assert results == []


class TestCheckAmbiguity:
    @patch("cli.ticker_validation.search_ticker")
    def test_short_ticker_is_flagged_ambiguous(self, mock_search):
        mock_search.return_value = [
            {"symbol": "AB", "shortname": "AB Company"},
            {"symbol": "ABC", "shortname": "ABC Corp"},
        ]

        result = check_ambiguity("A")

        assert result.is_ambiguous is True
        assert result.matches is not None
        assert len(result.matches) == 2

    @patch("cli.ticker_validation.search_ticker")
    def test_unique_ticker_not_ambiguous(self, mock_search):
        mock_search.return_value = [
            {"symbol": "AAPL", "shortname": "Apple Inc."},
        ]

        result = check_ambiguity("AAPL")

        assert result.is_ambiguous is False

    @patch("cli.ticker_validation.search_ticker")
    def test_check_ambiguity_handles_search_failure(self, mock_search):
        mock_search.side_effect = Exception("Search failed")

        result = check_ambiguity("AAPL")

        assert result.is_ambiguous is False


class TestGetValidatedTicker:
    @patch("cli.ticker_validation.questionary.confirm")
    @patch("cli.ticker_validation.validate_ticker")
    def test_confirmed_ticker_returns_symbol(self, mock_validate, mock_confirm):
        mock_validate.return_value = TickerValidationResult(
            is_valid=True,
            symbol="AAPL",
            company_name="Apple Inc.",
            security_type="EQUITY",
        )
        mock_confirm.return_value.ask.return_value = True

        result = get_validated_ticker("AAPL")

        assert result == "AAPL"

    @patch("cli.ticker_validation.questionary.select")
    @patch("cli.ticker_validation.check_ambiguity")
    @patch("cli.ticker_validation.validate_ticker")
    def test_ambiguous_ticker_shows_selection(
        self, mock_validate, mock_ambiguity, mock_select
    ):
        mock_validate.return_value = TickerValidationResult(
            is_valid=True,
            symbol="A",
            company_name="Test",
            security_type="EQUITY",
        )
        mock_ambiguity.return_value = TickerValidationResult(
            is_valid=True,
            symbol="A",
            is_ambiguous=True,
            matches=[
                {"symbol": "A", "shortname": "Agilent Technologies"},
                {"symbol": "AA", "shortname": "Alcoa"},
            ],
        )
        mock_select.return_value.ask.return_value = "A"

        result = get_validated_ticker("A")

        assert result == "A"

    @patch("cli.ticker_validation.console.print")
    @patch("cli.ticker_validation.validate_ticker")
    def test_invalid_ticker_shows_error(self, mock_validate, mock_print):
        mock_validate.return_value = TickerValidationResult(
            is_valid=False,
            symbol="INVALID",
            error_message="Ticker not found",
        )

        with pytest.raises(SystemExit):
            get_validated_ticker("INVALID")


class TestEdgeCases:
    @patch("cli.ticker_validation.yf.Ticker")
    def test_lowercase_input_normalized(self, mock_ticker_class):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Apple Inc.",
            "quoteType": "EQUITY",
            "symbol": "AAPL",
        }
        mock_ticker_class.return_value = mock_ticker

        result = validate_ticker("aapl")

        assert result.symbol == "AAPL"

    @patch("cli.ticker_validation.yf.Ticker")
    def test_whitespace_input_trimmed(self, mock_ticker_class):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Apple Inc.",
            "quoteType": "EQUITY",
            "symbol": "AAPL",
        }
        mock_ticker_class.return_value = mock_ticker

        result = validate_ticker("  AAPL  ")

        assert result.symbol == "AAPL"

    @patch("cli.ticker_validation.yf.Ticker")
    def test_etf_ticker_validated(self, mock_ticker_class):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "SPDR S&P 500 ETF Trust",
            "quoteType": "ETF",
            "symbol": "SPY",
        }
        mock_ticker_class.return_value = mock_ticker

        result = validate_ticker("SPY")

        assert result.is_valid is True
        assert result.security_type == "ETF"

    @patch("cli.ticker_validation.yf.Ticker")
    def test_timeout_parameter_passed(self, mock_ticker_class):
        mock_ticker = MagicMock()
        mock_ticker.info = {"symbol": "AAPL"}
        mock_ticker_class.return_value = mock_ticker

        validate_ticker("AAPL", timeout=10.0)

        mock_ticker_class.assert_called_with("AAPL")
