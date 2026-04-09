"""Shared fixtures for Radon data client tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_ib_class():
    """Mock ib_insync.IB class for IBClient tests."""
    ib_instance = MagicMock()
    ib_instance.positions.return_value = [{"symbol": "AAPL", "position": 100}]
    ib_instance.portfolio.return_value = [{"symbol": "AAPL", "position": 100}]
    ib_instance.accountSummary.return_value = [
        {"tag": "NetLiquidation", "value": "100000"}
    ]
    ib_instance.openTrades.return_value = []
    ib_instance.trades.return_value = []
    ib_instance.reqSecDefOptParams.return_value = []
    ib_instance.qualifyContracts.return_value = []
    ib_instance.reqContractDetails.return_value = []
    ib_instance.reqHistoricalData.return_value = []
    ib_instance.reqExecutions.return_value = []
    ib_instance.fills.return_value = []
    ib_instance.disconnect.return_value = None
    ib_instance.sleep.return_value = None
    ib_instance.errorEvent = MagicMock()
    ib_instance.errorEvent.__iadd__ = MagicMock(return_value=ib_instance.errorEvent)
    return ib_instance


@pytest.fixture
def mock_httpx_response():
    """Factory fixture for creating mock httpx responses."""

    def _make_response(
        status_code: int = 200,
        json_data: dict | None = None,
        headers: dict | None = None,
    ):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.reason_phrase = "OK" if status_code == 200 else "Error"
        resp.headers = headers or {}
        resp.text = str(json_data) if json_data else ""
        return resp

    return _make_response


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.Client for UWClient tests."""
    client = MagicMock()
    client.get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"data": "test"}),
        reason_phrase="OK",
        headers={},
    )
    client.close.return_value = None
    return client
