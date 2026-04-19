"""Tests for radon.clients.ib_client module."""

from unittest.mock import MagicMock, patch

import pytest

from radon.clients.base import ClientStatus

HAS_IB_TARGET = "radon.clients.ib_client.HAS_IB"


@pytest.fixture
def ib_client():
    from radon.clients.ib_client import IBClient

    return IBClient()


@pytest.fixture
def ib_client_connected(ib_client, mock_ib_class):
    """Create an IBClient with mocked ib_insync available and connected."""
    ib_client._ib = mock_ib_class
    ib_client._connected = True
    return ib_client


class TestIBClientUnavailable:
    """Tests for IBClient when ib_insync is not installed."""

    def test_instantiates_without_ib_insync(self, ib_client):
        assert ib_client is not None
        assert ib_client._ib is None
        assert ib_client._connected is False

    @patch(HAS_IB_TARGET, False)
    def test_is_available_returns_false(self, ib_client):
        assert ib_client.is_available() is False

    @patch(HAS_IB_TARGET, False)
    def test_check_availability_reports_unavailable(self, ib_client):
        result = ib_client.check_availability()
        assert result.status == ClientStatus.UNAVAILABLE
        assert "ib_insync" in result.message

    @patch(HAS_IB_TARGET, False)
    def test_is_connected_returns_false(self, ib_client):
        assert ib_client.is_connected() is False

    @patch(HAS_IB_TARGET, False)
    def test_get_positions_returns_none(self, ib_client):
        assert ib_client.get_positions() is None

    @patch(HAS_IB_TARGET, False)
    def test_get_portfolio_returns_none(self, ib_client):
        assert ib_client.get_portfolio() is None

    @patch(HAS_IB_TARGET, False)
    def test_get_account_summary_returns_none(self, ib_client):
        assert ib_client.get_account_summary() is None

    @patch(HAS_IB_TARGET, False)
    def test_get_pnl_returns_none(self, ib_client):
        assert ib_client.get_pnl() is None

    @patch(HAS_IB_TARGET, False)
    def test_get_pnl_single_returns_none(self, ib_client):
        assert ib_client.get_pnl_single("account", 12345) is None

    @patch(HAS_IB_TARGET, False)
    def test_get_option_chain_returns_none(self, ib_client):
        assert ib_client.get_option_chain("AAPL") is None

    @patch(HAS_IB_TARGET, False)
    def test_get_option_price_returns_none(self, ib_client):
        assert ib_client.get_option_price("AAPL", "20260101", 150.0, "C") is None

    @patch(HAS_IB_TARGET, False)
    def test_get_historical_data_returns_none(self, ib_client):
        assert ib_client.get_historical_data(MagicMock()) is None

    @patch(HAS_IB_TARGET, False)
    def test_get_contract_details_returns_none(self, ib_client):
        assert ib_client.get_contract_details(MagicMock()) is None

    @patch(HAS_IB_TARGET, False)
    def test_qualify_contracts_returns_none(self, ib_client):
        assert ib_client.qualify_contracts(MagicMock()) is None

    @patch(HAS_IB_TARGET, False)
    def test_get_executions_returns_none(self, ib_client):
        assert ib_client.get_executions() is None

    @patch(HAS_IB_TARGET, False)
    def test_get_fills_returns_none(self, ib_client):
        assert ib_client.get_fills() is None

    @patch(HAS_IB_TARGET, False)
    def test_get_open_orders_returns_none(self, ib_client):
        assert ib_client.get_open_orders() is None

    @patch(HAS_IB_TARGET, False)
    def test_get_open_trades_returns_none(self, ib_client):
        assert ib_client.get_open_trades() is None

    @patch(HAS_IB_TARGET, False)
    def test_get_trades_returns_none(self, ib_client):
        assert ib_client.get_trades() is None

    @patch(HAS_IB_TARGET, False)
    def test_get_order_status_returns_none(self, ib_client):
        assert ib_client.get_order_status(order_id=1) is None

    @patch(HAS_IB_TARGET, False)
    def test_place_order_returns_none(self, ib_client):
        assert ib_client.place_order(MagicMock(), MagicMock()) is None

    @patch(HAS_IB_TARGET, False)
    def test_cancel_order_returns_none(self, ib_client):
        assert ib_client.cancel_order(MagicMock()) is None

    @patch(HAS_IB_TARGET, False)
    def test_get_quote_returns_none(self, ib_client):
        assert ib_client.get_quote(MagicMock()) is None

    @patch(HAS_IB_TARGET, False)
    def test_run_flex_query_returns_none(self, ib_client):
        assert ib_client.run_flex_query(1, "token") is None


class TestIBClientContextManager:
    def test_context_manager_enter_returns_self(self, ib_client):
        with ib_client as client:
            assert client is ib_client

    @patch(HAS_IB_TARGET, False)
    def test_context_manager_exit_calls_disconnect(self, ib_client):
        ib_client.disconnect()
        assert ib_client._connected is False


class TestIBClientConnect:
    @patch(HAS_IB_TARGET, False)
    def test_connect_is_noop_when_ib_unavailable(self, ib_client):
        ib_client.connect()
        assert ib_client._connected is False
        assert ib_client._ib is None

    @patch(HAS_IB_TARGET, True)
    def test_connect_raises_after_max_retries(self, ib_client):
        from radon.clients.ib_client import IBConnectionError

        with pytest.raises(IBConnectionError, match="Failed to connect"):
            ib_client._connected = False
            ib_client._ib = MagicMock()
            ib_client._loop = MagicMock()
            ib_client._run_in_ib_thread = MagicMock(
                side_effect=Exception("connection refused")
            )
            ib_client.connect(host="127.0.0.1", port=4001, max_retries=1)

    def test_disconnect_when_not_connected(self, ib_client):
        ib_client._ib = None
        ib_client._connected = False
        ib_client.disconnect()
        assert ib_client._connected is False


class TestIBClientConnected:
    """Tests for IBClient when HAS_IB=True and connected."""

    @patch(HAS_IB_TARGET, True)
    def test_check_availability_when_connected(self, ib_client_connected):
        result = ib_client_connected.check_availability()
        assert result.status == ClientStatus.AVAILABLE
        assert "Connected" in result.message

    @patch(HAS_IB_TARGET, True)
    def test_get_positions_delegates_to_ib(self, ib_client_connected, mock_ib_class):
        positions = ib_client_connected.get_positions()
        mock_ib_class.positions.assert_called_once()
        assert positions == [{"symbol": "AAPL", "position": 100}]

    @patch(HAS_IB_TARGET, True)
    def test_get_portfolio_delegates_to_ib(self, ib_client_connected, mock_ib_class):
        result = ib_client_connected.get_portfolio("DU12345")
        mock_ib_class.portfolio.assert_called_once_with("DU12345")
        assert result == [{"symbol": "AAPL", "position": 100}]

    @patch(HAS_IB_TARGET, True)
    def test_get_account_summary_delegates(self, ib_client_connected, mock_ib_class):
        result = ib_client_connected.get_account_summary(group="All")
        mock_ib_class.accountSummary.assert_called_once_with(account="All")
        assert result == [{"tag": "NetLiquidation", "value": "100000"}]

    @patch(HAS_IB_TARGET, True)
    def test_get_option_chain_delegates(self, ib_client_connected, mock_ib_class):
        ib_client_connected.get_option_chain("AAPL")
        mock_ib_class.reqSecDefOptParams.assert_called_once_with("AAPL", "", "STK", 0)

    @patch(HAS_IB_TARGET, True)
    def test_get_contract_details_delegates(self, ib_client_connected, mock_ib_class):
        contract = MagicMock()
        ib_client_connected.get_contract_details(contract)
        mock_ib_class.reqContractDetails.assert_called_once_with(contract)

    @patch(HAS_IB_TARGET, True)
    def test_get_historical_data_delegates(self, ib_client_connected, mock_ib_class):
        contract = MagicMock()
        ib_client_connected.get_historical_data(
            contract, duration="1 D", bar_size="1 hour"
        )
        mock_ib_class.reqHistoricalData.assert_called_once()

    @patch(HAS_IB_TARGET, True)
    def test_get_executions_delegates(self, ib_client_connected, mock_ib_class):
        ib_client_connected.get_executions()
        mock_ib_class.reqExecutions.assert_called_once()

    @patch(HAS_IB_TARGET, True)
    def test_get_fills_delegates(self, ib_client_connected, mock_ib_class):
        ib_client_connected.get_fills()
        mock_ib_class.fills.assert_called_once()

    @patch(HAS_IB_TARGET, True)
    def test_get_open_trades_delegates(self, ib_client_connected, mock_ib_class):
        ib_client_connected.get_open_trades()
        mock_ib_class.openTrades.assert_called_once()

    @patch(HAS_IB_TARGET, True)
    def test_get_trades_delegates(self, ib_client_connected, mock_ib_class):
        ib_client_connected.get_trades()
        mock_ib_class.trades.assert_called_once()

    @patch(HAS_IB_TARGET, True)
    def test_get_open_orders_delegates(self, ib_client_connected, mock_ib_class):
        ib_client_connected.get_open_orders()
        mock_ib_class.reqAllOpenOrders.assert_called_once()
        mock_ib_class.openTrades.assert_called()

    @patch(HAS_IB_TARGET, True)
    def test_get_order_status_finds_by_perm_id(
        self, ib_client_connected, mock_ib_class
    ):
        trade1 = MagicMock()
        trade1.order.permId = 999
        trade1.order.orderId = 1
        mock_ib_class.trades.return_value = [trade1]

        result = ib_client_connected.get_order_status(perm_id=999)
        assert result is trade1

    @patch(HAS_IB_TARGET, True)
    def test_get_order_status_finds_by_order_id(
        self, ib_client_connected, mock_ib_class
    ):
        trade1 = MagicMock()
        trade1.order.permId = 999
        trade1.order.orderId = 42
        mock_ib_class.trades.return_value = [trade1]

        result = ib_client_connected.get_order_status(order_id=42)
        assert result is trade1

    @patch(HAS_IB_TARGET, True)
    def test_get_order_status_returns_none_when_not_found(
        self, ib_client_connected, mock_ib_class
    ):
        mock_ib_class.trades.return_value = []
        result = ib_client_connected.get_order_status(order_id=99)
        assert result is None

    @patch(HAS_IB_TARGET, True)
    def test_qualify_contract_raises_on_empty(self, ib_client_connected, mock_ib_class):
        from radon.clients.ib_client import IBContractError

        mock_ib_class.qualifyContracts.return_value = []
        with pytest.raises(IBContractError, match="Failed to qualify"):
            ib_client_connected.qualify_contract(MagicMock())

    @patch(HAS_IB_TARGET, True)
    def test_qualify_contract_returns_first(self, ib_client_connected, mock_ib_class):
        qualified = [MagicMock()]
        mock_ib_class.qualifyContracts.return_value = qualified
        result = ib_client_connected.qualify_contract(MagicMock())
        assert result is qualified[0]


class TestIBClientOrders:
    @patch(HAS_IB_TARGET, True)
    def test_place_order_delegates(self, ib_client_connected, mock_ib_class):
        contract = MagicMock()
        order = MagicMock()
        order.action = "BUY"
        order.totalQuantity = 100
        trade = MagicMock()
        trade.order.orderId = 1
        mock_ib_class.placeOrder.return_value = trade

        result = ib_client_connected.place_order(contract, order)
        assert result is trade
        mock_ib_class.placeOrder.assert_called_once_with(contract, order)

    @patch(HAS_IB_TARGET, True)
    def test_place_order_raises_on_failure(self, ib_client_connected, mock_ib_class):
        from radon.clients.ib_client import IBOrderError

        mock_ib_class.placeOrder.side_effect = Exception("order rejected")
        with pytest.raises(IBOrderError, match="Failed to place order"):
            ib_client_connected.place_order(MagicMock(), MagicMock())

    @patch(HAS_IB_TARGET, True)
    def test_cancel_order_delegates(self, ib_client_connected, mock_ib_class):
        order = MagicMock()
        order.orderId = 1
        mock_ib_class.cancelOrder.return_value = True

        ib_client_connected.cancel_order(order)
        mock_ib_class.cancelOrder.assert_called_once_with(order)

    @patch(HAS_IB_TARGET, True)
    def test_cancel_order_raises_on_failure(self, ib_client_connected, mock_ib_class):
        from radon.clients.ib_client import IBOrderError

        mock_ib_class.cancelOrder.side_effect = Exception("cancel failed")
        with pytest.raises(IBOrderError, match="Failed to cancel"):
            ib_client_connected.cancel_order(MagicMock())

    @patch(HAS_IB_TARGET, True)
    def test_modify_order_delegates(self, ib_client_connected, mock_ib_class):
        contract = MagicMock()
        order = MagicMock()
        order.orderId = 1
        trade = MagicMock()
        mock_ib_class.placeOrder.return_value = trade

        result = ib_client_connected.modify_order(contract, order, lmt_price=150.0)
        assert result is trade
        assert order.lmtPrice == 150.0


class TestIBClientErrorHandling:
    def test_on_error_ignores_info_codes(self, ib_client):
        ib_client._on_error(1, 2104, "Market data farm OK")
        assert ib_client._last_error is None

    def test_on_error_ignores_ignore_codes(self, ib_client):
        ib_client._on_error(1, 10358, "Reuters inactive")
        assert ib_client._last_error is None

    def test_on_error_tracks_connectivity(self, ib_client):
        ib_client._on_error(1, 1100, "Connectivity lost")
        assert ib_client._last_error is None

    def test_on_error_tracks_pacing_violations(self, ib_client):
        ib_client._pacing_retries = {}
        ib_client._on_error(100, 162, "pacing violation")
        assert ib_client._pacing_retries[100] == 1

    def test_on_error_pacing_max_retries(self, ib_client):
        ib_client._pacing_retries = {100: 3}
        ib_client._on_error(100, 162, "pacing violation")
        assert ib_client._pacing_retries[100] == 3

    def test_on_error_invalid_contract_adds_to_failed(self, ib_client):
        contract = MagicMock()
        ib_client._on_error(1, 200, "No security definition", contract=contract)
        assert contract in ib_client._failed_contracts

    def test_on_error_stores_generic_error(self, ib_client):
        ib_client._on_error(1, 502, "Something bad")
        assert ib_client._last_error == (502, "Something bad")

    def test_on_error_generic_for_unknown_code(self, ib_client):
        ib_client._on_error(1, 0, "")
        assert ib_client._last_error == (0, "")


class TestIBClientProperties:
    def test_ib_property_returns_none_initially(self, ib_client):
        assert ib_client.ib is None

    def test_ib_property_returns_instance(self, ib_client_connected, mock_ib_class):
        assert ib_client_connected.ib is mock_ib_class

    def test_failed_contracts_initially_empty(self, ib_client):
        assert ib_client.failed_contracts == set()

    def test_clear_subscriptions(self, ib_client):
        ib_client._subscriptions = [{"contract": "test"}]
        ib_client.clear_subscriptions()
        assert ib_client._subscriptions == []


class TestIBClientSubscriptions:
    @patch(HAS_IB_TARGET, True)
    def test_quote_tracks_subscription(self, ib_client_connected, mock_ib_class):
        contract = MagicMock()
        mock_ib_class.reqMktData.return_value = MagicMock()
        ib_client_connected.get_quote(contract, snapshot=False)
        assert len(ib_client_connected._subscriptions) == 1
        assert ib_client_connected._subscriptions[0]["contract"] is contract

    @patch(HAS_IB_TARGET, True)
    def test_quote_snapshot_does_not_track(self, ib_client_connected, mock_ib_class):
        contract = MagicMock()
        mock_ib_class.reqMktData.return_value = MagicMock()
        ib_client_connected.get_quote(contract, snapshot=True)
        assert len(ib_client_connected._subscriptions) == 0

    @patch(HAS_IB_TARGET, True)
    def test_cancel_market_data_delegates(self, ib_client_connected, mock_ib_class):
        contract = MagicMock()
        ib_client_connected.cancel_market_data(contract)
        mock_ib_class.cancelMktData.assert_called_once_with(contract)

    @patch(HAS_IB_TARGET, True)
    def test_set_market_data_type_delegates(self, ib_client_connected, mock_ib_class):
        ib_client_connected.set_market_data_type(3)
        mock_ib_class.reqMarketDataType.assert_called_once_with(3)


class TestIBClientPnl:
    @patch(HAS_IB_TARGET, True)
    def test_get_pnl_delegates(self, ib_client_connected, mock_ib_class):
        mock_ib_class.reqPnL.return_value = MagicMock()
        ib_client_connected.get_pnl("DU12345")
        mock_ib_class.reqPnL.assert_called_once_with("DU12345")
        mock_ib_class.sleep.assert_called_once_with(2)

    @patch(HAS_IB_TARGET, True)
    def test_get_pnl_single_delegates(self, ib_client_connected, mock_ib_class):
        mock_ib_class.reqPnLSingle.return_value = MagicMock()
        ib_client_connected.get_pnl_single("DU12345", 12345)
        mock_ib_class.reqPnLSingle.assert_called_once_with("DU12345", "", 12345)

    @patch(HAS_IB_TARGET, False)
    def test_cancel_pnl_when_unavailable(self, ib_client):
        assert ib_client.cancel_pnl(MagicMock()) is None

    @patch(HAS_IB_TARGET, False)
    def test_cancel_pnl_single_when_unavailable(self, ib_client):
        ib_client.cancel_pnl_single("acct", 1)

    @patch(HAS_IB_TARGET, True)
    def test_cancel_pnl_delegates(self, ib_client_connected, mock_ib_class):
        pnl_obj = MagicMock()
        ib_client_connected.cancel_pnl(pnl_obj)
        mock_ib_class.cancelPnL.assert_called_once_with(pnl_obj)


class TestIBClientWaitForFill:
    @patch(HAS_IB_TARGET, True)
    def test_wait_for_fill_returns_filled_trade(
        self, ib_client_connected, mock_ib_class
    ):
        trade = MagicMock()
        trade.order.orderId = 1
        trade.orderStatus.status = "Filled"
        trade.orderStatus.avgFillPrice = 150.0
        trade.orderStatus.filled = 100

        result = ib_client_connected.wait_for_fill(trade, timeout=5, poll_interval=0.1)
        assert result is trade

    @patch(HAS_IB_TARGET, True)
    def test_wait_for_fill_raises_on_cancelled(
        self, ib_client_connected, mock_ib_class
    ):
        from radon.clients.ib_client import IBOrderError

        trade = MagicMock()
        trade.order.orderId = 1
        trade.orderStatus.status = "Cancelled"

        with pytest.raises(IBOrderError, match="cancelled"):
            ib_client_connected.wait_for_fill(trade, timeout=5, poll_interval=0.1)

    @patch(HAS_IB_TARGET, True)
    def test_wait_for_fill_raises_on_timeout(self, ib_client_connected, mock_ib_class):
        from radon.clients.ib_client import IBTimeoutError

        trade = MagicMock()
        trade.order.orderId = 1
        trade.orderStatus.status = "Submitted"

        with pytest.raises(IBTimeoutError, match="not filled"):
            ib_client_connected.wait_for_fill(trade, timeout=2, poll_interval=1.0)


class TestIBClientEnsureIBInstance:
    @patch(HAS_IB_TARGET, False)
    def test_returns_false_when_no_ib(self, ib_client):
        assert ib_client._ensure_ib_instance() is False

    @patch(HAS_IB_TARGET, True)
    def test_returns_true_when_ib_already_created(self, ib_client):
        ib_client._ib = MagicMock()
        assert ib_client._ensure_ib_instance() is True

    @patch(HAS_IB_TARGET, True)
    def test_creates_event_loop_thread(self, ib_client):
        mock_ib = MagicMock()
        mock_ib.errorEvent = MagicMock()
        mock_ib.errorEvent.__iadd__ = MagicMock(return_value=mock_ib.errorEvent)

        mock_ib_module = MagicMock()
        mock_ib_module.IB.return_value = mock_ib

        ib_client._ib = None
        with patch.dict("sys.modules", {"ib_insync": mock_ib_module}):
            result = ib_client._ensure_ib_instance()
            assert result is True
            assert ib_client._ib is not None
            assert ib_client._loop is not None
            assert ib_client._thread is not None
            assert ib_client._thread.daemon is True

            ib_client._loop.call_soon_threadsafe(ib_client._loop.stop)
            ib_client._thread.join(timeout=3)


class TestIBClientSleep:
    def test_sleep_is_noop_when_not_connected(self, ib_client):
        ib_client.sleep(1)

    @patch(HAS_IB_TARGET, True)
    def test_sleep_delegates_when_connected(self, ib_client_connected, mock_ib_class):
        ib_client_connected.sleep(2.5)
        mock_ib_class.sleep.assert_called_once_with(2.5)
