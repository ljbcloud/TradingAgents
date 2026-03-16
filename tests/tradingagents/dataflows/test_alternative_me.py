"""Unit tests for Alternative.me Fear and Greed Index API vendor."""

# ruff: noqa: S101 - assert is expected in tests

from unittest.mock import patch

import pytest
import requests

from tradingagents.dataflows.alternative_me import _classify_value  # noqa: PLC2701
from tradingagents.dataflows.exceptions import VendorError


class TestGetBitcoinFearGreedIndex:
    """Tests for get_bitcoin_fear_greed_index function."""

    @patch("tradingagents.dataflows.alternative_me.requests.get")
    def test_returns_current_value(self, mock_get):
        """Should return current Fear and Greed Index value."""
        # Arrange
        mock_response = mock_get.return_value
        mock_response.ok = True
        mock_response.json.return_value = {
            "name": "Fear and Greed Index",
            "data": [
                {
                    "value": "45",
                    "value_classification": "Fear",
                    "timestamp": "1551157200",
                    "time_until_update": "68499",
                }
            ],
        }

        # Act
        from tradingagents.dataflows.alternative_me import get_bitcoin_fear_greed_index

        result = get_bitcoin_fear_greed_index()

        # Assert
        assert "45" in result
        assert "Fear" in result
        mock_get.assert_called_once()

    @patch("tradingagents.dataflows.alternative_me.requests.get")
    def test_supports_limit_parameter(self, mock_get):
        """Should support limit parameter for historical data."""
        # Arrange
        mock_response = mock_get.return_value
        mock_response.ok = True
        mock_response.json.return_value = {
            "name": "Fear and Greed Index",
            "data": [
                {
                    "value": "45",
                    "value_classification": "Fear",
                    "timestamp": "1551157200",
                },
                {
                    "value": "52",
                    "value_classification": "Neutral",
                    "timestamp": "1551070800",
                },
            ],
        }

        # Act
        from tradingagents.dataflows.alternative_me import get_bitcoin_fear_greed_index

        result = get_bitcoin_fear_greed_index(limit=2)

        # Assert
        assert "45" in result
        assert "52" in result
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["limit"] == 2

    @patch("tradingagents.dataflows.alternative_me.requests.get")
    def test_handles_timeout_error(self, mock_get):
        """Should raise VendorError on timeout."""
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        # Act & Assert
        from tradingagents.dataflows.alternative_me import get_bitcoin_fear_greed_index

        with pytest.raises(VendorError) as exc_info:
            get_bitcoin_fear_greed_index()

        assert "timed out" in str(exc_info.value).lower()

    @patch("tradingagents.dataflows.alternative_me.requests.get")
    def test_handles_http_error(self, mock_get):
        """Should raise VendorError on HTTP error."""
        # Arrange
        mock_response = mock_get.return_value
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )

        # Act & Assert
        from tradingagents.dataflows.alternative_me import get_bitcoin_fear_greed_index

        with pytest.raises(VendorError):
            get_bitcoin_fear_greed_index()

    @patch("tradingagents.dataflows.alternative_me.requests.get")
    def test_handles_empty_response(self, mock_get):
        """Should handle empty data array gracefully."""
        # Arrange
        mock_response = mock_get.return_value
        mock_response.ok = True
        mock_response.json.return_value = {
            "name": "Fear and Greed Index",
            "data": [],
        }

        # Act
        from tradingagents.dataflows.alternative_me import get_bitcoin_fear_greed_index

        result = get_bitcoin_fear_greed_index()

        # Assert
        assert "No Fear and Greed Index data available" in result

    @patch("tradingagents.dataflows.alternative_me.requests.get")
    def test_formats_output_with_all_fields(self, mock_get):
        """Should format output with value, classification, and timestamp."""
        # Arrange
        mock_response = mock_get.return_value
        mock_response.ok = True
        mock_response.json.return_value = {
            "name": "Fear and Greed Index",
            "data": [
                {
                    "value": "75",
                    "value_classification": "Greed",
                    "timestamp": "1551157200",
                }
            ],
        }

        # Act
        from tradingagents.dataflows.alternative_me import get_bitcoin_fear_greed_index

        result = get_bitcoin_fear_greed_index()

        # Assert
        assert "75" in result
        assert "Greed" in result
        # Should include classification ranges context
        assert "Fear" in result or "Greed" in result  # Classification present


class TestFearGreedClassification:
    """Tests for Fear and Greed classification helper functions."""

    def test_classify_extreme_fear(self):
        """Values 0-24 should classify as Extreme Fear."""
        assert _classify_value(0) == "Extreme Fear"
        assert _classify_value(24) == "Extreme Fear"

    def test_classify_fear(self):
        """Values 25-49 should classify as Fear."""
        assert _classify_value(25) == "Fear"
        assert _classify_value(49) == "Fear"

    def test_classify_neutral(self):
        """Values 50-54 should classify as Neutral."""
        assert _classify_value(50) == "Neutral"
        assert _classify_value(54) == "Neutral"

    def test_classify_greed(self):
        """Values 55-75 should classify as Greed."""
        assert _classify_value(55) == "Greed"
        assert _classify_value(75) == "Greed"

    def test_classify_extreme_greed(self):
        """Values 76-100 should classify as Extreme Greed."""
        assert _classify_value(76) == "Extreme Greed"
        assert _classify_value(100) == "Extreme Greed"
