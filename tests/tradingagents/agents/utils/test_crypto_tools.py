import pytest

from tradingagents.agents.utils.crypto_tools import (
    get_crypto_candles,
    get_crypto_orderbook,
    get_crypto_ticker,
)


@pytest.mark.unit
class TestGetCryptoCandles:
    def test_should_return_formatted_csv_string(self, mocker):
        """Should return CSV-formatted OHLCV data when candles are fetched."""
        mock_route = mocker.patch(
            "tradingagents.agents.utils.crypto_tools.route_to_vendor"
        )
        mock_route.return_value = (
            "# Crypto OHLCV data for BTC/USD from coinbase\n"
            "# Timeframe: 1h\n"
            "# Total candles: 2\n\n"
            "timestamp,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,42000.0,42500.0,41800.0,42200.0,100.0\n"
            "2024-01-01 01:00:00,42200.0,42800.0,42100.0,42600.0,150.0"
        )

        result = get_crypto_candles.invoke({
            "symbol": "BTC/USD",
            "timeframe": "1h",
            "limit": 300,
        })

        assert "timestamp,open,high,low,close,volume" in result
        assert "42000.0" in result
        mock_route.assert_called_once_with(
            "get_crypto_candles", "BTC/USD", "1h", None, None, 300, "coinbase"
        )

    def test_should_pass_all_parameters_to_vendor(self, mocker):
        """Should pass all parameters to route_to_vendor."""
        mock_route = mocker.patch(
            "tradingagents.agents.utils.crypto_tools.route_to_vendor"
        )
        mock_route.return_value = "data"

        get_crypto_candles.invoke({
            "symbol": "ETH/USD",
            "timeframe": "1d",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "limit": 100,
        })

        mock_route.assert_called_once_with(
            "get_crypto_candles",
            "ETH/USD",
            "1d",
            "2024-01-01",
            "2024-01-31",
            100,
            "coinbase",
        )


@pytest.mark.unit
class TestGetCryptoTicker:
    def test_should_return_formatted_ticker_string(self, mocker):
        """Should return formatted ticker data."""
        mock_route = mocker.patch(
            "tradingagents.agents.utils.crypto_tools.route_to_vendor"
        )
        mock_route.return_value = (
            "# Ticker data for BTC/USD from coinbase\n"
            "Symbol: BTC/USD\n"
            "Bid: 42000.0\n"
            "Ask: 42001.0\n"
            "Last Price: 42000.5"
        )

        result = get_crypto_ticker.invoke({"symbol": "BTC/USD"})

        assert "BTC/USD" in result
        assert "Bid:" in result
        mock_route.assert_called_once_with("get_crypto_ticker", "BTC/USD", "coinbase")

    def test_should_pass_symbol_to_vendor(self, mocker):
        """Should pass symbol parameter to route_to_vendor."""
        mock_route = mocker.patch(
            "tradingagents.agents.utils.crypto_tools.route_to_vendor"
        )
        mock_route.return_value = "ticker data"

        get_crypto_ticker.invoke({"symbol": "ETH/USD"})

        mock_route.assert_called_once_with("get_crypto_ticker", "ETH/USD", "coinbase")


@pytest.mark.unit
class TestGetCryptoOrderbook:
    def test_should_return_formatted_orderbook(self, mocker):
        """Should return formatted order book data."""
        mock_route = mocker.patch(
            "tradingagents.agents.utils.crypto_tools.route_to_vendor"
        )
        mock_route.return_value = (
            "# Order Book for BTC/USD from coinbase\n"
            "## Bids (Buy Orders)\n"
            "price,amount\n"
            "42000.0,1.5\n"
            "## Asks (Sell Orders)\n"
            "price,amount\n"
            "42001.0,1.0\n"
            "## Summary\n"
            "Spread: 1.0"
        )

        result = get_crypto_orderbook.invoke({"symbol": "BTC/USD", "depth": 20})

        assert "Bids" in result
        assert "Asks" in result
        assert "Spread" in result
        mock_route.assert_called_once_with(
            "get_crypto_orderbook", "BTC/USD", 20, "coinbase"
        )

    def test_should_pass_depth_parameter(self, mocker):
        """Should pass depth parameter to route_to_vendor."""
        mock_route = mocker.patch(
            "tradingagents.agents.utils.crypto_tools.route_to_vendor"
        )
        mock_route.return_value = "orderbook data"

        get_crypto_orderbook.invoke({"symbol": "ETH/USD", "depth": 50})

        mock_route.assert_called_once_with(
            "get_crypto_orderbook", "ETH/USD", 50, "coinbase"
        )

    def test_should_use_default_depth(self, mocker):
        """Should use default depth of 20 when not specified."""
        mock_route = mocker.patch(
            "tradingagents.agents.utils.crypto_tools.route_to_vendor"
        )
        mock_route.return_value = "orderbook data"

        get_crypto_orderbook.invoke({"symbol": "BTC/USD"})

        mock_route.assert_called_once_with(
            "get_crypto_orderbook", "BTC/USD", 20, "coinbase"
        )
