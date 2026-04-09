"""Tests for tradingagents.radon.clients.base module."""

from unittest.mock import patch

from tradingagents.radon.clients.base import (
    BaseDataClient,
    ClientCheckResult,
    ClientStatus,
    check_optional_dependency,
)


class TestClientStatus:
    def test_available_value(self):
        assert ClientStatus.AVAILABLE == "AVAILABLE"

    def test_unavailable_value(self):
        assert ClientStatus.UNAVAILABLE == "UNAVAILABLE"

    def test_error_value(self):
        assert ClientStatus.ERROR == "ERROR"

    def test_is_str_enum(self):
        assert isinstance(ClientStatus.AVAILABLE, str)


class TestClientCheckResult:
    def test_creation_with_required_fields(self):
        result = ClientCheckResult(status=ClientStatus.AVAILABLE, message="all good")
        assert result.status == ClientStatus.AVAILABLE
        assert result.message == "all good"
        assert result.error is None

    def test_creation_with_error(self):
        exc = RuntimeError("boom")
        result = ClientCheckResult(
            status=ClientStatus.ERROR, message="failed", error=exc
        )
        assert result.error is exc

    def test_is_dataclass(self):
        result = ClientCheckResult(status=ClientStatus.UNAVAILABLE, message="test")
        assert hasattr(result, "__dataclass_fields__")


class TestCheckOptionalDependency:
    def test_returns_true_for_installed_module(self):
        assert check_optional_dependency("os") is True

    def test_returns_true_for_json(self):
        assert check_optional_dependency("json") is True

    def test_returns_false_for_nonexistent_module(self):
        assert check_optional_dependency("nonexistent_package_xyz_12345") is False

    @patch("importlib.util.find_spec", return_value=None)
    def test_returns_false_when_find_spec_returns_none(self, mock_find):
        assert check_optional_dependency("anything") is False
        mock_find.assert_called_once_with("anything")


class TestBaseDataClientProtocol:
    def test_protocol_is_runtime_checkable(self):
        assert hasattr(BaseDataClient, "__protocol_attrs__") or hasattr(
            BaseDataClient, "_is_protocol"
        )

    def test_class_satisfying_protocol(self):
        class FakeClient:
            def check_availability(self) -> ClientCheckResult:
                return ClientCheckResult(status=ClientStatus.AVAILABLE, message="ok")

            def is_available(self) -> bool:
                return True

        client = FakeClient()
        assert isinstance(client, BaseDataClient)
        assert client.is_available() is True
        assert client.check_availability().status == ClientStatus.AVAILABLE
