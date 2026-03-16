"""Unit tests for DeFiLlama data vendor implementation."""

# ruff: noqa: S101 - assert is expected in tests

from unittest.mock import MagicMock, patch

import pytest
import requests

from tradingagents.dataflows.defillama import (
    get_crypto_chain_tvl,
    get_crypto_protocol_tvl,
    get_crypto_protocol_yields,
)
from tradingagents.dataflows.exceptions import VendorError


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def sample_tvl_list_data():
    """Sample TVL data in new API format (list of historical points)."""
    return [
        {"date": 1703980800, "totalLiquidityUSD": 1000000000},
        {"date": 1704067200, "totalLiquidityUSD": 1010000000},
        {"date": 1704153600, "totalLiquidityUSD": 1020000000},
        {"date": 1704239111, "totalLiquidityUSD": 1030000000},
    ]


@pytest.fixture
def sample_protocol_response_new_api(sample_tvl_list_data):
    """Sample protocol response using new API structure."""
    return {
        "name": "Uniswap",
        "symbol": "UNI",
        "category": "DEX",
        "description": "Leading decentralized trading protocol",
        "tvl": sample_tvl_list_data,
        "currentChainTvls": {
            "Ethereum": 800000000,
            "Arbitrum": 150000000,
            "Polygon": 80000000,
        },
        "twitter": "Uniswap",
        "gecko_id": "uniswap",
    }


@pytest.fixture
def sample_protocol_response_old_api():
    """Sample protocol response using old API structure."""
    return {
        "name": "Aave",
        "symbol": "AAVE",
        "category": "Lending",
        "description": "Decentralized lending protocol",
        "tvl": 5000000000,
        "change_1d": 2.5,
        "change_7d": -1.2,
        "chainTvl": {
            "Ethereum": 4000000000,
            "Avalanche": 800000000,
            "Polygon": 200000000,
        },
        "twitter": "AaveAave",
        "gecko_id": "aave",
    }


@pytest.mark.unit
class TestGetCryptoProtocolTvl:
    """Tests for get_crypto_protocol_tvl function."""

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_new_api_structure_extracts_current_tvl_from_list(
        self, mock_get, mock_response, sample_protocol_response_new_api
    ):
        """Should extract current TVL from last item in tvl list."""
        mock_response.json.return_value = sample_protocol_response_new_api
        mock_get.return_value = mock_response

        result = get_crypto_protocol_tvl("uniswap")

        assert "Current TVL: $1,030,000,000.00" in result
        assert "Uniswap" in result
        mock_get.assert_called_once()

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_new_api_structure_calculates_tvl_changes(
        self, mock_get, mock_response, sample_protocol_response_new_api
    ):
        """Should calculate TVL changes from historical data."""
        mock_response.json.return_value = sample_protocol_response_new_api
        mock_get.return_value = mock_response

        result = get_crypto_protocol_tvl("uniswap")

        assert "TVL Change 24h:" in result
        assert "TVL Change 7d:" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_old_api_structure_fallback_tvl_as_number(
        self, mock_get, mock_response, sample_protocol_response_old_api
    ):
        """Should handle old API structure where tvl is a number."""
        mock_response.json.return_value = sample_protocol_response_old_api
        mock_get.return_value = mock_response

        result = get_crypto_protocol_tvl("aave")

        assert "Current TVL: $5,000,000,000.00" in result
        assert "Aave" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_uses_currentchaintvls_for_chain_breakdown(
        self, mock_get, mock_response, sample_protocol_response_new_api
    ):
        """Should use currentChainTvls for chain TVL breakdown."""
        mock_response.json.return_value = sample_protocol_response_new_api
        mock_get.return_value = mock_response

        result = get_crypto_protocol_tvl("uniswap")

        assert "TVL by Chain" in result
        assert "Ethereum: $800,000,000.00" in result
        assert "Arbitrum: $150,000,000.00" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_fallback_to_chaintvl_if_currentchaintvls_missing(
        self, mock_get, mock_response, sample_protocol_response_old_api
    ):
        """Should fall back to chainTvl if currentChainTvls is missing."""
        mock_response.json.return_value = sample_protocol_response_old_api
        mock_get.return_value = mock_response

        result = get_crypto_protocol_tvl("aave")

        assert "TVL by Chain" in result
        assert "Ethereum: $4,000,000,000.00" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_empty_tvl_list_shows_na(self, mock_get, mock_response):
        """Should show N/A when tvl list is empty."""
        mock_response.json.return_value = {
            "name": "Test",
            "symbol": "TEST",
            "tvl": [],
        }
        mock_get.return_value = mock_response

        result = get_crypto_protocol_tvl("test")

        assert "Current TVL: N/A" in result
        assert "TVL Change 24h: N/A" in result
        assert "TVL Change 7d: N/A" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_single_tvl_data_point_shows_na_for_changes(self, mock_get, mock_response):
        """Should show N/A for changes with only one data point."""
        mock_response.json.return_value = {
            "name": "Test",
            "symbol": "TEST",
            "tvl": [{"date": 1704239111, "totalLiquidityUSD": 1000000000}],
        }
        mock_get.return_value = mock_response

        result = get_crypto_protocol_tvl("test")

        assert "Current TVL: $1,000,000,000.00" in result
        assert "TVL Change 24h: N/A" in result
        assert "TVL Change 7d: N/A" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_empty_response_returns_not_found_message(self, mock_get, mock_response):
        """Should return message when no data is found."""
        mock_response.json.return_value = None
        mock_get.return_value = mock_response

        result = get_crypto_protocol_tvl("unknown")

        assert "No TVL data found" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_protocol_normalized_to_lowercase(self, mock_get, mock_response):
        """Should normalize protocol name to lowercase."""
        mock_response.json.return_value = {"name": "Test", "tvl": []}
        mock_get.return_value = mock_response

        get_crypto_protocol_tvl("UNISWAP")

        call_args = mock_get.call_args
        assert "uniswap" in call_args[0][0]

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_whitespace_stripped_from_protocol(self, mock_get, mock_response):
        """Should strip whitespace from protocol name."""
        mock_response.json.return_value = {"name": "Test", "tvl": []}
        mock_get.return_value = mock_response

        get_crypto_protocol_tvl("  uniswap  ")

        call_args = mock_get.call_args
        assert "uniswap" in call_args[0][0]

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_404_raises_vendor_error(self, mock_get, mock_response):
        """Should raise VendorError on 404 response."""
        http_error = requests.exceptions.HTTPError()
        http_error.response = MagicMock()
        http_error.response.status_code = 404
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        with pytest.raises(VendorError) as exc_info:
            get_crypto_protocol_tvl("nonexistent")

        assert "Protocol not found" in str(exc_info.value)

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_network_error_raises_vendor_error(self, mock_get):
        """Should raise VendorError on network error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network down")

        with pytest.raises(VendorError) as exc_info:
            get_crypto_protocol_tvl("uniswap")

        assert "Network error" in str(exc_info.value)


@pytest.mark.unit
class TestGetCryptoProtocolYields:
    """Tests for get_crypto_protocol_yields function."""

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_returns_formatted_yield_data(self, mock_get, mock_response):
        """Should return formatted yield data for protocol."""
        mock_response.json.return_value = {
            "data": [
                {
                    "project": "uniswap",
                    "pool": "0xabc",
                    "chain": "Ethereum",
                    "symbol": "USDC-ETH",
                    "apy": 5.5,
                    "apyBase": 3.0,
                    "apyReward": 2.5,
                    "tvlUsd": 100000000,
                    "rewardTokens": ["UNI"],
                    "stablecoin": False,
                }
            ]
        }
        mock_get.return_value = mock_response

        result = get_crypto_protocol_yields("uniswap")

        assert "Yield Data for uniswap" in result
        assert "Total APY: 5.50%" in result
        assert "Base APY: 3.00%" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_no_pools_found_returns_message(self, mock_get, mock_response):
        """Should return message when no pools found."""
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        result = get_crypto_protocol_yields("unknown")

        assert "No yield pools found" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_no_data_key_returns_message(self, mock_get, mock_response):
        """Should return message when data key is missing."""
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        result = get_crypto_protocol_yields("uniswap")

        assert "No yield data available" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_network_error_raises_vendor_error(self, mock_get):
        """Should raise VendorError on network error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network down")

        with pytest.raises(VendorError) as exc_info:
            get_crypto_protocol_yields("uniswap")

        assert "Network error" in str(exc_info.value)


@pytest.mark.unit
class TestGetCryptoChainTvl:
    """Tests for get_crypto_chain_tvl function."""

    @pytest.fixture
    def sample_chains_response(self):
        """Sample chains API response."""
        return [
            {
                "name": "Ethereum",
                "tvl": 60000000000,
                "chainId": 1,
                "tokenSymbol": "ETH",
                "gecko_id": "ethereum",
            },
            {
                "name": "Arbitrum",
                "tvl": 3000000000,
                "chainId": 42161,
                "tokenSymbol": "ETH",
                "gecko_id": "arbitrum",
            },
            {
                "name": "Solana",
                "tvl": 5000000000,
                "chainId": 0,
                "tokenSymbol": "SOL",
                "gecko_id": "solana",
            },
        ]

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_returns_formatted_chain_tvl(
        self, mock_get, mock_response, sample_chains_response
    ):
        """Should return formatted chain TVL data."""
        mock_response.json.return_value = sample_chains_response
        mock_get.return_value = mock_response

        result = get_crypto_chain_tvl("ethereum")

        assert "TVL Data for Ethereum" in result
        assert "Total Value Locked: $60,000,000,000.00" in result
        assert "Chain ID: 1" in result
        assert "Native Token: ETH" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_calculates_tvl_rank(self, mock_get, mock_response, sample_chains_response):
        """Should calculate TVL ranking among all chains."""
        mock_response.json.return_value = sample_chains_response
        mock_get.return_value = mock_response

        result = get_crypto_chain_tvl("arbitrum")

        assert "TVL Rank: #3" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_chain_not_found_returns_message(
        self, mock_get, mock_response, sample_chains_response
    ):
        """Should return message when chain is not found."""
        mock_response.json.return_value = sample_chains_response
        mock_get.return_value = mock_response

        result = get_crypto_chain_tvl("unknown")

        assert "Chain not found" in result
        assert "Available chains" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_empty_response_returns_message(self, mock_get, mock_response):
        """Should return message when no chain data available."""
        mock_response.json.return_value = None
        mock_get.return_value = mock_response

        result = get_crypto_chain_tvl("ethereum")

        assert "No chain data available" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_normalizes_chain_name_to_lowercase(
        self, mock_get, mock_response, sample_chains_response
    ):
        """Should normalize chain name to lowercase for matching."""
        mock_response.json.return_value = sample_chains_response
        mock_get.return_value = mock_response

        result = get_crypto_chain_tvl("ETHEREUM")

        assert "TVL Data for Ethereum" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_strips_whitespace_from_chain_name(
        self, mock_get, mock_response, sample_chains_response
    ):
        """Should strip whitespace from chain name."""
        mock_response.json.return_value = sample_chains_response
        mock_get.return_value = mock_response

        result = get_crypto_chain_tvl("  ethereum  ")

        assert "TVL Data for Ethereum" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_handles_zero_tvl_gracefully(self, mock_get, mock_response):
        """Should handle chains with zero TVL."""
        mock_response.json.return_value = [
            {
                "name": "TestChain",
                "tvl": 0,
                "chainId": 999,
                "tokenSymbol": "TST",
                "gecko_id": "testchain",
            },
        ]
        mock_get.return_value = mock_response

        result = get_crypto_chain_tvl("testchain")

        assert "Total Value Locked: N/A" in result

    @patch("tradingagents.dataflows.defillama.requests.get")
    def test_network_error_raises_vendor_error(self, mock_get):
        """Should raise VendorError on network error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network down")

        with pytest.raises(VendorError) as exc_info:
            get_crypto_chain_tvl("ethereum")

        assert "Network error" in str(exc_info.value)
