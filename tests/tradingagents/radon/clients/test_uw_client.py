"""Tests for tradingagents.radon.clients.uw_client module."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def uw_client_no_token():
    from tradingagents.radon.clients.uw_client import UWClient

    with patch.dict("os.environ", {}, clear=True):
        client = UWClient.__new__(UWClient)
        client._token = ""
        client._base_url = "https://api.unusualwhales.com/api"
        client._timeout = 30
        client._max_retries = 3
        client._backoff_factor = 1.0
        client._available = False
        client._client = None
        return client


@pytest.fixture
def uw_client():
    from tradingagents.radon.clients.uw_client import UWClient

    with patch("tradingagents.radon.clients.uw_client.HAS_HTTPX", True):
        return UWClient(token="test-token")


class TestUWClientUnavailable:
    def test_is_available_false_without_token(self, uw_client_no_token):
        assert uw_client_no_token.is_available() is False

    @patch("tradingagents.radon.clients.uw_client.HAS_HTTPX", False)
    def test_is_available_false_without_httpx(self):
        from tradingagents.radon.clients.uw_client import UWClient

        with patch.dict("os.environ", {"UW_TOKEN": "tok"}, clear=False):
            client = UWClient.__new__(UWClient)
            client._token = "tok"
            client._available = False
            client._client = None
            assert client.is_available() is False

    def test_get_darkpool_flow_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_darkpool_flow("AAPL") is None

    def test_get_darkpool_recent_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_darkpool_recent() is None

    def test_get_flow_alerts_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_flow_alerts() is None

    def test_get_stock_info_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_stock_info("AAPL") is None

    def test_get_stock_state_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_stock_state("AAPL") is None

    def test_get_options_volume_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_options_volume("AAPL") is None

    def test_get_option_contracts_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_option_contracts("AAPL") is None

    def test_get_option_chain_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_option_chain("AAPL", "2026-01-01") is None

    def test_get_expiry_breakdown_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_expiry_breakdown("AAPL") is None

    def test_get_greeks_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_greeks("AAPL") is None

    def test_get_greek_exposure_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_greek_exposure("AAPL") is None

    def test_get_realized_volatility_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_realized_volatility("AAPL") is None

    def test_get_analyst_ratings_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_analyst_ratings() is None

    def test_get_short_interest_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_short_interest("AAPL") is None

    def test_get_institutional_ownership_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_institutional_ownership("AAPL") is None

    def test_get_insider_transactions_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_insider_transactions() is None

    def test_get_congress_recent_trades_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_congress_recent_trades() is None

    def test_get_etf_info_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_etf_info("SPY") is None

    def test_get_market_tide_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_market_tide() is None

    def test_get_news_headlines_returns_none(self, uw_client_no_token):
        assert uw_client_no_token.get_news_headlines() is None


class TestUWClientContextManager:
    def test_context_manager_returns_self(self, uw_client):
        with uw_client as client:
            assert client is uw_client

    def test_close_is_safe_when_no_client(self, uw_client_no_token):
        uw_client_no_token.close()
        assert uw_client_no_token._client is None


class TestUWClientInit:
    @patch("tradingagents.radon.clients.uw_client.HAS_HTTPX", True)
    def test_reads_token_from_env(self):
        from tradingagents.radon.clients.uw_client import UWClient

        with patch.dict("os.environ", {"UW_TOKEN": "env-token"}, clear=False):
            client = UWClient()
            assert client._token == "env-token"

    @patch("tradingagents.radon.clients.uw_client.HAS_HTTPX", True)
    def test_constructor_token_overrides_env(self):
        from tradingagents.radon.clients.uw_client import UWClient

        with patch.dict("os.environ", {"UW_TOKEN": "env-token"}, clear=False):
            client = UWClient(token="explicit-token")
            assert client._token == "explicit-token"

    @patch("tradingagents.radon.clients.uw_client.HAS_HTTPX", True)
    def test_available_when_token_present(self):
        from tradingagents.radon.clients.uw_client import UWClient

        client = UWClient(token="tok")
        assert client.is_available() is True

    @patch("tradingagents.radon.clients.uw_client.HAS_HTTPX", False)
    def test_unavailable_when_httpx_missing(self):
        from tradingagents.radon.clients.uw_client import UWClient

        client = UWClient(token="tok")
        assert client.is_available() is False


class TestUWExceptionHierarchy:
    def test_uw_api_error_base(self):
        from tradingagents.radon.clients.uw_client import UWAPIError

        err = UWAPIError("test error", status_code=500)
        assert str(err) == "test error"
        assert err.status_code == 500
        assert err.response_body is None

    def test_uw_api_error_with_response_body(self):
        from tradingagents.radon.clients.uw_client import UWAPIError

        body = {"detail": "not found"}
        err = UWAPIError("err", status_code=404, response_body=body)
        assert err.response_body == body

    def test_uw_auth_error_inherits(self):
        from tradingagents.radon.clients.uw_client import UWAPIError, UWAuthError

        err = UWAuthError("unauthorized", status_code=401)
        assert isinstance(err, UWAPIError)
        assert err.status_code == 401

    def test_uw_rate_limit_error_inherits(self):
        from tradingagents.radon.clients.uw_client import UWAPIError, UWRateLimitError

        err = UWRateLimitError("slow down", status_code=429)
        assert isinstance(err, UWAPIError)

    def test_uw_not_found_error_inherits(self):
        from tradingagents.radon.clients.uw_client import UWAPIError, UWNotFoundError

        err = UWNotFoundError("missing", status_code=404)
        assert isinstance(err, UWAPIError)

    def test_uw_validation_error_inherits(self):
        from tradingagents.radon.clients.uw_client import UWAPIError, UWValidationError

        err = UWValidationError("bad input", status_code=422)
        assert isinstance(err, UWAPIError)

    def test_uw_server_error_inherits(self):
        from tradingagents.radon.clients.uw_client import UWAPIError, UWServerError

        err = UWServerError("crash", status_code=500)
        assert isinstance(err, UWAPIError)


class TestUWClientGet:
    def test_get_returns_json_on_200(self, uw_client, mock_httpx_response):
        resp = mock_httpx_response(status_code=200, json_data={"data": [1, 2, 3]})
        uw_client._client = MagicMock()
        uw_client._client.get.return_value = resp

        result = uw_client._get("test/endpoint")
        assert result == {"data": [1, 2, 3]}

    def test_get_raises_auth_error_on_401(self, uw_client, mock_httpx_response):
        from tradingagents.radon.clients.uw_client import UWAuthError

        resp = mock_httpx_response(
            status_code=401, json_data={"message": "invalid token"}
        )
        uw_client._client = MagicMock()
        uw_client._client.get.return_value = resp

        with pytest.raises(UWAuthError, match="invalid token"):
            uw_client._get("test/endpoint")

    def test_get_raises_auth_error_on_403(self, uw_client, mock_httpx_response):
        from tradingagents.radon.clients.uw_client import UWAuthError

        resp = mock_httpx_response(status_code=403, json_data={"message": "forbidden"})
        uw_client._client = MagicMock()
        uw_client._client.get.return_value = resp

        with pytest.raises(UWAuthError):
            uw_client._get("test/endpoint")

    def test_get_raises_not_found_on_404(self, uw_client, mock_httpx_response):
        from tradingagents.radon.clients.uw_client import UWNotFoundError

        resp = mock_httpx_response(status_code=404, json_data={"message": "not found"})
        uw_client._client = MagicMock()
        uw_client._client.get.return_value = resp

        with pytest.raises(UWNotFoundError, match="not found"):
            uw_client._get("test/endpoint")

    def test_get_raises_validation_error_on_422(self, uw_client, mock_httpx_response):
        from tradingagents.radon.clients.uw_client import UWValidationError

        resp = mock_httpx_response(
            status_code=422, json_data={"message": "invalid params"}
        )
        uw_client._client = MagicMock()
        uw_client._client.get.return_value = resp

        with pytest.raises(UWValidationError, match="invalid params"):
            uw_client._get("test/endpoint")

    def test_get_raises_server_error_on_500_after_retries(
        self, uw_client, mock_httpx_response
    ):
        from tradingagents.radon.clients.uw_client import UWServerError

        resp = mock_httpx_response(
            status_code=500, json_data={"message": "internal error"}
        )
        uw_client._client = MagicMock()
        uw_client._client.get.return_value = resp

        with patch("time.sleep"), pytest.raises(UWServerError, match="internal error"):
            uw_client._get("test/endpoint")

    def test_get_raises_api_error_on_400(self, uw_client, mock_httpx_response):
        from tradingagents.radon.clients.uw_client import UWAPIError

        resp = mock_httpx_response(
            status_code=400, json_data={"message": "bad request"}
        )
        uw_client._client = MagicMock()
        uw_client._client.get.return_value = resp

        with pytest.raises(UWAPIError, match="bad request"):
            uw_client._get("test/endpoint")

    def test_get_retries_on_connection_error(self, uw_client):
        import httpx

        from tradingagents.radon.clients.uw_client import UWAPIError

        uw_client._client = MagicMock()
        uw_client._client.get.side_effect = httpx.ConnectError("refused")
        uw_client._max_retries = 2

        with patch("time.sleep"), pytest.raises(UWAPIError, match="Connection failed"):
            uw_client._get("test/endpoint")

    def test_get_returns_none_when_unavailable(self, uw_client_no_token):
        result = uw_client_no_token._get("anything")
        assert result is None


class TestUWClientRetryDelay:
    def test_retry_delay_from_header(self):
        from tradingagents.radon.clients.uw_client import UWClient

        resp = MagicMock()
        resp.headers = {"Retry-After": "5"}
        delay = UWClient._get_retry_delay(resp, 0)
        assert delay == 5.0

    def test_retry_delay_minimum_one_second(self):
        from tradingagents.radon.clients.uw_client import UWClient

        resp = MagicMock()
        resp.headers = {"Retry-After": "0.1"}
        delay = UWClient._get_retry_delay(resp, 0)
        assert delay == 1.0

    def test_retry_delay_exponential_backoff(self):
        from tradingagents.radon.clients.uw_client import UWClient

        resp = MagicMock()
        resp.headers = {}
        delay = UWClient._get_retry_delay(resp, 2)
        assert delay == 4.0

    def test_retry_delay_invalid_header_falls_back(self):
        from tradingagents.radon.clients.uw_client import UWClient

        resp = MagicMock()
        resp.headers = {"Retry-After": "not-a-number"}
        delay = UWClient._get_retry_delay(resp, 1)
        assert delay == 2.0


class TestUWClientBuildParams:
    def test_filters_none_values(self):
        from tradingagents.radon.clients.uw_client import UWClient

        params = UWClient._build_params(ticker="AAPL", limit=None, date="2026-01-01")
        assert params == {"ticker": "AAPL", "date": "2026-01-01"}

    def test_empty_when_all_none(self):
        from tradingagents.radon.clients.uw_client import UWClient

        params = UWClient._build_params(a=None, b=None)
        assert params == {}

    def test_preserves_false_and_zero(self):
        from tradingagents.radon.clients.uw_client import UWClient

        params = UWClient._build_params(active=False, count=0)
        assert params == {"active": False, "count": 0}


class TestUWClientSafeJson:
    def test_returns_dict_on_valid_json(self):
        from tradingagents.radon.clients.uw_client import UWClient

        resp = MagicMock()
        resp.json.return_value = {"key": "value"}
        assert UWClient._safe_json(resp) == {"key": "value"}

    def test_returns_empty_dict_on_json_error(self):
        from tradingagents.radon.clients.uw_client import UWClient

        resp = MagicMock()
        resp.json.side_effect = ValueError("bad json")
        assert UWClient._safe_json(resp) == {}


class TestUWClientEndpointMethods:
    def test_get_darkpool_flow_calls_get(self, uw_client):
        uw_client._get = MagicMock(return_value={"data": []})
        uw_client.get_darkpool_flow("AAPL", min_premium=100000)
        uw_client._get.assert_called_once()
        call_args = uw_client._get.call_args
        assert "darkpool/AAPL" in call_args[0][0]
        assert call_args[1]["params"]["min_premium"] == 100000

    def test_get_darkpool_recent_calls_get(self, uw_client):
        uw_client._get = MagicMock(return_value={"data": []})
        uw_client.get_darkpool_recent(limit=10)
        uw_client._get.assert_called_once()
        call_args = uw_client._get.call_args
        assert "darkpool/recent" in call_args[0][0]

    def test_get_flow_alerts_calls_get(self, uw_client):
        uw_client._get = MagicMock(return_value={"data": []})
        uw_client.get_flow_alerts(ticker="AAPL", is_call=True)
        uw_client._get.assert_called_once()
        call_args = uw_client._get.call_args
        assert "option-trades/flow-alerts" in call_args[0][0]
        assert call_args[1]["params"]["ticker_symbol"] == "AAPL"

    def test_get_flow_alerts_by_ticker(self, uw_client):
        uw_client.get_flow_alerts = MagicMock(return_value={"data": []})
        uw_client.get_flow_alerts_by_ticker("AAPL", min_premium=50000)
        uw_client.get_flow_alerts.assert_called_once_with(
            ticker="AAPL", min_premium=50000, max_premium=None, limit=None
        )

    def test_get_stock_flow_alerts_uppercases_ticker(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_stock_flow_alerts("aapl")
        call_url = uw_client._get.call_args[0][0]
        assert "stock/AAPL" in call_url

    def test_get_stock_info_uppercases_ticker(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_stock_info("msft")
        assert "stock/MSFT" in uw_client._get.call_args[0][0]

    def test_get_stock_ohlc_with_candle_size(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_stock_ohlc("AAPL", candle_size="1h")
        assert "ohlc/1h" in uw_client._get.call_args[0][0]

    def test_get_option_contracts_with_filters(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_option_contracts("AAPL", expiry="2026-01-01", option_type="call")
        call_args = uw_client._get.call_args
        assert "option-contracts" in call_args[0][0]
        assert call_args[1]["params"]["expiry"] == "2026-01-01"

    def test_get_option_chain_delegates(self, uw_client):
        uw_client.get_option_contracts = MagicMock(return_value={})
        uw_client.get_option_chain("AAPL", "2026-01-01")
        uw_client.get_option_contracts.assert_called_once_with(
            "AAPL", expiry="2026-01-01"
        )

    def test_get_greeks_with_expiry(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_greeks("AAPL", expiry="2026-01-01")
        assert "greeks" in uw_client._get.call_args[0][0]

    def test_get_analyst_ratings_with_ticker(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_analyst_ratings(ticker="AAPL")
        call_args = uw_client._get.call_args
        assert "screener/analysts" in call_args[0][0]
        assert call_args[1]["params"]["ticker"] == "AAPL"

    def test_get_monthly_seasonality(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_monthly_seasonality("AAPL")
        assert "seasonality/AAPL/monthly" in uw_client._get.call_args[0][0]

    def test_get_short_interest(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_short_interest("AAPL")
        assert "shorts/AAPL" in uw_client._get.call_args[0][0]

    def test_get_institutional_ownership(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_institutional_ownership("AAPL")
        assert "institution/AAPL" in uw_client._get.call_args[0][0]

    def test_get_insider_transactions(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_insider_transactions(ticker="AAPL", limit=10)
        call_args = uw_client._get.call_args
        assert "insider/transactions" in call_args[0][0]

    def test_get_congress_recent_trades(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_congress_recent_trades(ticker="AAPL")
        assert "congress/recent-trades" in uw_client._get.call_args[0][0]

    def test_get_etf_info(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_etf_info("SPY")
        assert "etfs/SPY" in uw_client._get.call_args[0][0]

    def test_get_etf_holdings(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_etf_holdings("SPY")
        assert "etfs/SPY/holdings" in uw_client._get.call_args[0][0]

    def test_get_market_tide(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_market_tide()
        assert "market/market-tide" in uw_client._get.call_args[0][0]

    def test_get_sector_etfs(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_sector_etfs()
        assert "market/sector-etfs" in uw_client._get.call_args[0][0]

    def test_get_economic_calendar(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_economic_calendar()
        assert "market/economic-calendar" in uw_client._get.call_args[0][0]

    def test_get_news_headlines(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_news_headlines(ticker="AAPL", limit=5)
        assert "news/headlines" in uw_client._get.call_args[0][0]

    def test_get_max_pain(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_max_pain("AAPL")
        assert "stock/AAPL/max-pain" in uw_client._get.call_args[0][0]

    def test_get_lit_flow_recent(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_lit_flow_recent()
        assert "lit-flow/recent" in uw_client._get.call_args[0][0]

    def test_get_stock_screener(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_stock_screener(min_marketcap=1000000)
        assert "screener/stocks" in uw_client._get.call_args[0][0]

    def test_get_earnings_premarket(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_earnings_premarket()
        assert "earnings/premarket" in uw_client._get.call_args[0][0]

    def test_get_earnings_by_ticker(self, uw_client):
        uw_client._get = MagicMock(return_value={})
        uw_client.get_earnings_by_ticker("AAPL")
        assert "earnings/AAPL" in uw_client._get.call_args[0][0]
