"""Interactive Brokers API client with graceful degradation.

Wraps ``ib_insync.IB`` with connection management, portfolio queries,
option chain fetching, and account summary operations.

ib_insync is an **optional** dependency. When it is not installed every
public method returns ``None`` (or an empty list) and :meth:`is_available`
returns ``False`` — no ``ImportError`` is raised.

Usage::

    from tradingagents.radon.clients.ib_client import IBClient

    with IBClient() as client:
        client.connect(host="127.0.0.1", port=4001, client_id=1)
        positions = client.get_positions()

    # Graceful degradation — works even without ib_insync installed
    client = IBClient()
    print(client.is_available())  # False when ib_insync is absent
    result = client.get_option_chain("AAPL")  # Returns None
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import threading
import time
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from types import TracebackType

from tradingagents.radon.clients.base import (
    ClientCheckResult,
    ClientStatus,
    check_optional_dependency,
)

# ---------------------------------------------------------------------------
# Dependency gate — checked once at import time
# ---------------------------------------------------------------------------

HAS_IB: bool = check_optional_dependency("ib_insync")

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class IBError(Exception):
    """Base exception for all IB client errors."""


class IBConnectionError(IBError):
    """Raised when an IB connection cannot be established or is lost."""


class IBOrderError(IBError):
    """Raised when an order operation fails."""


class IBTimeoutError(IBError):
    """Raised when an operation times out."""


class IBContractError(IBError):
    """Raised when contract qualification or lookup fails."""


# ---------------------------------------------------------------------------
# IB error-code constants (used by the error callback)
# ---------------------------------------------------------------------------

# IB error codes that are informational / non-critical
_INFO_CODES = frozenset({
    2104,  # Market data farm connection is OK
    2106,  # HMDS data farm connection is OK
    2108,  # Market data farm connection is inactive
    2158,  # Sec-def data farm connection is OK
})

# IB error codes that should be silently ignored (not user-relevant)
_IGNORE_CODES = frozenset({
    10358,  # Reuters Fundamentals subscription inactive — auto-fallback
})

# IB error codes indicating connectivity issues
_CONNECTIVITY_CODES = frozenset({
    1100,  # Connectivity between IB and TWS has been lost
    1101,  # Connectivity restored — data lost
    1102,  # Connectivity restored — data maintained
})

# IB error codes for pacing violations — retry with exponential backoff
_PACING_CODES = frozenset({
    162,  # Historical market data pacing violation
    366,  # No historical data query found for ticker id
})

_MAX_PACING_RETRIES = 3

# IB error codes for invalid contracts — don't retry
_INVALID_CONTRACT_CODES = frozenset({
    200,  # No security definition has been found
    354,  # Requested market data is not subscribed
})

# Reconnection constants
MAX_RECONNECT_ATTEMPTS = 5
MAX_RECONNECT_BACKOFF = 30  # seconds

_DEFAULT_HOST = os.environ.get("IB_GATEWAY_HOST", "127.0.0.1")
_DEFAULT_PORT = int(os.environ.get("IB_GATEWAY_PORT", "4001"))

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IBClient
# ---------------------------------------------------------------------------


class IBClient:  # noqa: PLR0904
    """High-level Interactive Brokers API client with graceful degradation.

    When *ib_insync* is not installed the client is completely inert:
    :meth:`is_available` returns ``False`` and every data-fetching method
    returns ``None`` (or an empty list) without raising ``ImportError``.

    Wraps ``ib_insync.IB`` with:
    - Connection lifecycle (connect / disconnect / reconnect)
    - Context manager support
    - Portfolio, order, market-data, and execution operations
    - Structured logging
    - Retry logic for transient connection errors
    - Graceful handling of known IB error codes
    - Dedicated asyncio event-loop thread for ib_insync
    """

    def __init__(self) -> None:
        self._ib: Any = None
        self._connected: bool = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

        self._last_host: str = _DEFAULT_HOST
        self._last_port: int = _DEFAULT_PORT
        self._last_client_id: int = 0
        self._last_timeout: int = 10
        self._last_error: tuple | None = None

        # Subscription tracking for recovery after disconnect
        self._subscriptions: list[dict[str, Any]] = []

        # Reconnection state
        self._reconnecting: bool = False

        # Pacing violation retry tracking (reqId -> count)
        self._pacing_retries: dict[int, int] = {}

        # Invalid contracts
        self._failed_contracts: set[Any] = set()

    # -- availability -------------------------------------------------------

    def check_availability(self) -> ClientCheckResult:
        """Return a :class:`ClientCheckResult` describing current status."""
        if not HAS_IB:
            return ClientCheckResult(
                status=ClientStatus.UNAVAILABLE,
                message="ib_insync package is not installed",
            )
        if not self._connected:
            return ClientCheckResult(
                status=ClientStatus.UNAVAILABLE,
                message="Not connected to IB Gateway/TWS",
            )
        return ClientCheckResult(
            status=ClientStatus.AVAILABLE,
            message="Connected to IB Gateway/TWS",
        )

    def is_available(self) -> bool:
        """Return ``True`` when ib_insync is importable **and** connected."""
        if not HAS_IB:
            return False
        return self._connected

    # -- properties ---------------------------------------------------------

    @property
    def ib(self) -> Any:
        """Return the underlying ``ib_insync.IB`` instance (or ``None``)."""
        return self._ib

    @property
    def failed_contracts(self) -> set[Any]:
        """Return the set of contracts that returned invalid from IB."""
        return self._failed_contracts

    # -- connection lifecycle -----------------------------------------------

    def _ensure_ib_instance(self) -> bool:
        """Lazily create the ``ib_insync.IB`` instance and event-loop thread.

        Returns ``True`` on success, ``False`` when ib_insync is unavailable.
        """
        if not HAS_IB:
            return False

        if self._ib is not None:
            return True

        try:
            from ib_insync import IB
        except ImportError:
            return False

        self._ib = IB()
        self._ib.errorEvent += self._on_error

        # Create a dedicated event loop running in its own thread — ib_insync
        # requires its own loop that stays alive for callbacks.
        self._loop = asyncio.new_event_loop()

        def _run_loop() -> None:
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._thread = threading.Thread(target=_run_loop, daemon=True)
        self._thread.start()
        return True

    def _run_in_ib_thread(self, coro: Any, timeout: float = 30.0) -> Any:
        """Run *coro* in IB's dedicated event-loop thread.

        Returns ``None`` when not connected or when the call times out.
        """
        if not self._ib or not self._connected or self._loop is None:
            return None
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=timeout)
        except Exception:
            logger.exception("IB thread call failed")
            return None

    def connect(
        self,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        client_id: int = 0,
        timeout: int = 3,
        max_retries: int = 1,
    ) -> None:
        """Connect to TWS / IB Gateway.

        Args:
            host: IB Gateway / TWS host.
            port: IB Gateway / TWS port.
            client_id: Explicit client ID (int).
            timeout: Connection timeout in seconds.
            max_retries: Number of attempts before giving up.

        Raises:
            IBConnectionError: If the connection cannot be established.
        """
        if not self._ensure_ib_instance():
            logger.warning("ib_insync unavailable — connect() is a no-op")
            return

        self._last_host = host
        self._last_port = port
        self._last_client_id = client_id
        self._last_timeout = timeout

        attempt = 0
        last_exc: Exception | None = None
        while attempt < max_retries:
            attempt += 1
            try:
                self._run_in_ib_thread(
                    self._ib.connectAsync(
                        host,
                        port,
                        clientId=client_id,
                        timeout=timeout,
                    ),
                    timeout=timeout + 5,
                )
                self._connected = True
                logger.info(
                    "Connected to IB on %s:%s (clientId=%s)",
                    host,
                    port,
                    client_id,
                )
                return
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Connection attempt %d/%d failed: %s",
                    attempt,
                    max_retries,
                    exc,
                )
                if attempt < max_retries:
                    time.sleep(min(attempt, 5))

        msg = f"Failed to connect to IB on {host}:{port} after {max_retries} attempt(s): {last_exc}"
        raise IBConnectionError(msg)

    def disconnect(self) -> None:
        """Disconnect from IB. Safe to call when not connected."""
        if self._ib is not None and self._connected:
            with contextlib.suppress(Exception):
                self._ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IB")

        # Shut down the dedicated event-loop thread.
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._loop = None
        self._thread = None

    def reconnect(self) -> None:
        """Disconnect and reconnect using the last connection parameters."""
        logger.info(
            "Reconnecting to IB (%s:%s)",
            self._last_host,
            self._last_port,
        )
        self.disconnect()
        self.connect(
            host=self._last_host,
            port=self._last_port,
            client_id=self._last_client_id,
            timeout=self._last_timeout,
        )

    def is_connected(self) -> bool:
        """Return ``True`` if connected to IB."""
        if not HAS_IB or self._ib is None:
            return False
        return self._connected

    # -- context manager ----------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.disconnect()

    # -- connection guard ---------------------------------------------------

    def _require_connection(self) -> None:
        """Raise if not connected."""
        if not self.is_connected():
            msg = "Not connected to IB. Call connect() first."
            raise IBConnectionError(msg)

    # -- error handling -----------------------------------------------------

    def _on_error(
        self,
        req_id: Any,
        error_code: Any,
        error_string: str,
        contract: Any = None,
    ) -> None:
        """Handle IB error/warning callbacks (wired into ``ib.errorEvent``)."""
        code = int(error_code) if error_code else 0

        if code in _IGNORE_CODES:
            logger.debug("IB info %d (ignored): %s", code, error_string)
            return

        if code in _INFO_CODES:
            logger.info("IB info %d: %s", code, error_string)
            return

        if code in _CONNECTIVITY_CODES:
            logger.warning("IB connectivity %d: %s", code, error_string)
            return

        if code in _PACING_CODES:
            rid = int(req_id) if req_id else 0
            current = self._pacing_retries.get(rid, 0)
            if current < _MAX_PACING_RETRIES:
                self._pacing_retries[rid] = current + 1
                logger.warning(
                    "IB pacing violation %d (reqId=%s, retry %d/%d): %s",
                    code,
                    rid,
                    current + 1,
                    _MAX_PACING_RETRIES,
                    error_string,
                )
            else:
                logger.error(
                    "IB pacing violation %d (reqId=%s) — max retries: %s",
                    code,
                    rid,
                    error_string,
                )
            return

        if code in _INVALID_CONTRACT_CODES:
            if contract is not None:
                self._failed_contracts.add(contract)
            logger.warning(
                "IB invalid contract %d (reqId=%s): %s (contract=%s)",
                code,
                req_id,
                error_string,
                contract,
            )
            return

        self._last_error = (code, error_string)
        logger.error("IB error %d: %s", code, error_string)

    # -- disconnect recovery ------------------------------------------------

    def _on_disconnect(self) -> None:
        """Auto-reconnect with exponential backoff and restore subscriptions."""
        if self._reconnecting:
            return

        self._reconnecting = True
        self._connected = False
        logger.warning("Disconnected from IB — attempting reconnection")

        try:
            connected = False
            for attempt in range(MAX_RECONNECT_ATTEMPTS):
                delay = min(2**attempt, MAX_RECONNECT_BACKOFF)
                try:
                    if self._ib is not None:
                        self._ib.connect(
                            self._last_host,
                            self._last_port,
                            clientId=self._last_client_id,
                            timeout=self._last_timeout,
                        )
                        self._connected = True
                    connected = True
                    logger.info(
                        "Reconnected to IB on attempt %d/%d",
                        attempt + 1,
                        MAX_RECONNECT_ATTEMPTS,
                    )
                    break
                except Exception as exc:
                    logger.warning(
                        "Reconnect attempt %d/%d failed: %s — waiting %ds",
                        attempt + 1,
                        MAX_RECONNECT_ATTEMPTS,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

            if not connected:
                logger.error(
                    "Failed to reconnect after %d attempts",
                    MAX_RECONNECT_ATTEMPTS,
                )
                return

            restored, failed = self._restore_subscriptions()
            logger.info(
                "Subscription restoration: %d restored, %d failed",
                restored,
                failed,
            )
        finally:
            self._reconnecting = False

    def _restore_subscriptions(self) -> tuple[int, int]:
        """Re-subscribe to tracked market-data feeds. Returns (restored, failed)."""
        restored = 0
        failed = 0
        for sub in self._subscriptions:
            try:
                if self._ib is not None:
                    self._ib.reqMktData(
                        sub["contract"],
                        sub["generic_ticks"],
                        snapshot=False,
                        regulatorySnapshot=False,
                    )
                restored += 1
            except Exception as exc:  # noqa: PERF203
                failed += 1
                logger.warning(
                    "Failed to restore subscription for %s: %s",
                    sub["contract"],
                    exc,
                )
        return restored, failed

    # -- subscription management --------------------------------------------

    def clear_subscriptions(self) -> None:
        """Clear all tracked subscriptions."""
        self._subscriptions.clear()

    # -- portfolio operations -----------------------------------------------

    def get_positions(self) -> list | None:
        """Return current positions, or ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.positions()

    def get_portfolio(self, account: str = "") -> list | None:
        """Return portfolio items, or ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.portfolio(account)

    def get_account_summary(
        self,
        group: str = "",
        tags: list[str] | None = None,
    ) -> list | None:
        """Return account summary values, or ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.accountSummary(account=group)

    def get_pnl(self, account: str = "") -> Any:
        """Request P&L for account. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        pnl = self._ib.reqPnL(account)
        self._ib.sleep(2)
        return pnl

    def cancel_pnl(self, pnl_obj: Any) -> None:
        """Cancel P&L subscription."""
        if not self.is_available() or pnl_obj is None:
            return
        with contextlib.suppress(Exception):
            self._ib.cancelPnL(pnl_obj)

    def get_pnl_single(self, account: str, con_id: int) -> Any:
        """Request per-position P&L. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        pnl = self._ib.reqPnLSingle(account, "", con_id)
        self._ib.sleep(0.5)
        return pnl

    def cancel_pnl_single(self, account: str, con_id: int) -> None:
        """Cancel per-position P&L subscription."""
        if not self.is_available():
            return
        with contextlib.suppress(Exception):
            self._ib.cancelPnLSingle(account, "", con_id)

    # -- order operations ---------------------------------------------------

    def place_order(self, contract: Any, order: Any) -> Any:
        """Place an order and return the ``Trade`` object.

        Returns ``None`` when unavailable.
        Raises :class:`IBOrderError` on failure.
        """
        if not self.is_available():
            return None
        self._require_connection()
        try:
            trade = self._ib.placeOrder(contract, order)
            logger.info(
                "Placed order: %s %s %s @ %s (orderId=%s)",
                order.action,
                order.totalQuantity,
                getattr(contract, "symbol", contract),
                getattr(order, "lmtPrice", "MKT"),
                trade.order.orderId,
            )
            return trade
        except Exception as exc:
            msg = f"Failed to place order: {exc}"
            raise IBOrderError(msg) from exc

    def place_bracket_order(
        self,
        contract: Any,
        action: str,
        quantity: float,
        limit_price: float,
        take_profit_price: float,
        stop_loss_price: float,
    ) -> list | None:
        """Place a bracket order (parent + take-profit + stop-loss).

        Returns ``None`` when unavailable.
        """
        if not self.is_available():
            return None
        self._require_connection()
        try:
            bracket = self._ib.bracketOrder(
                action,
                quantity,
                limit_price,
                take_profit_price,
                stop_loss_price,
            )
            trades: list[Any] = []
            for br_order in bracket:
                trade = self._ib.placeOrder(contract, br_order)
                trades.append(trade)
            logger.info(
                "Placed bracket order: %s %s %s limit=%.2f TP=%.2f SL=%.2f",
                action,
                quantity,
                getattr(contract, "symbol", contract),
                limit_price,
                take_profit_price,
                stop_loss_price,
            )
            return trades
        except Exception as exc:
            msg = f"Failed to place bracket order: {exc}"
            raise IBOrderError(msg) from exc

    def cancel_order(self, order: Any) -> Any:
        """Cancel an open order. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        try:
            result = self._ib.cancelOrder(order)
            logger.info(
                "Cancelled order: orderId=%s",
                getattr(order, "orderId", "?"),
            )
            return result
        except Exception as exc:
            msg = f"Failed to cancel order: {exc}"
            raise IBOrderError(msg) from exc

    def modify_order(self, contract: Any, order: Any, **kwargs: Any) -> Any:
        """Modify an existing order. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()

        if "lmt_price" in kwargs:
            order.lmtPrice = kwargs["lmt_price"]
        if "total_quantity" in kwargs:
            order.totalQuantity = kwargs["total_quantity"]
        if "aux_price" in kwargs:
            order.auxPrice = kwargs["aux_price"]
        if "tif" in kwargs:
            order.tif = kwargs["tif"]

        try:
            trade = self._ib.placeOrder(contract, order)
            logger.info(
                "Modified order: orderId=%s new fields=%s",
                getattr(order, "orderId", "?"),
                kwargs,
            )
            return trade
        except Exception as exc:
            msg = f"Failed to modify order: {exc}"
            raise IBOrderError(msg) from exc

    def get_open_orders(self) -> list | None:
        """Return all open orders across all clients, or ``None``."""
        if not self.is_available():
            return None
        self._require_connection()
        self._ib.reqAllOpenOrders()
        self._ib.sleep(0.5)
        return self._ib.openTrades()

    def get_open_trades(self) -> list | None:
        """Return currently open trades, or ``None``."""
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.openTrades()

    def get_trades(self) -> list | None:
        """Return all trades (open + completed) for this session, or ``None``."""
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.trades()

    def get_order_status(
        self,
        order_id: int | None = None,
        perm_id: int | None = None,
    ) -> Any:
        """Look up a trade by order ID or permanent ID. Returns ``None``."""
        if not self.is_available():
            return None
        self._require_connection()
        trades = self._ib.trades()

        if perm_id is not None:
            for trade in trades:
                if trade.order.permId == perm_id:
                    return trade

        if order_id is not None:
            for trade in trades:
                if trade.order.orderId == order_id:
                    return trade

        return None

    # -- market data --------------------------------------------------------

    def get_quote(
        self,
        contract: Any,
        *,
        snapshot: bool = False,
        generic_ticks: str = "",
    ) -> Any:
        """Request market data for a contract. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        ticker = self._ib.reqMktData(
            contract,
            generic_ticks,
            snapshot,
            regulatorySnapshot=False,
        )
        if snapshot:
            self._ib.sleep(2)
        else:
            self._subscriptions.append({
                "contract": contract,
                "generic_ticks": generic_ticks,
            })
        return ticker

    def cancel_market_data(self, contract: Any) -> None:
        """Cancel streaming market data for a contract."""
        if not self.is_available():
            return
        self._require_connection()
        self._ib.cancelMktData(contract)

    def set_market_data_type(self, data_type: int) -> None:
        """Set market data type (1=Live, 2=Frozen, 3=Delayed, 4=Delayed-frozen)."""
        if not self.is_available():
            return
        self._require_connection()
        self._ib.reqMarketDataType(data_type)

    def get_option_chain(
        self,
        symbol: str,
        exchange: str = "",
        sec_type: str = "STK",
    ) -> list | None:
        """Return option chain parameters for an underlying.

        Returns a list of ``OptionChain`` objects with expirations, strikes,
        etc., or ``None`` when IB is unavailable.
        """
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.reqSecDefOptParams(symbol, exchange, sec_type, 0)

    def get_option_price(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        right: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> Any:
        """Get a quote for a specific option contract. Returns ``None``."""
        if not self.is_available():
            return None
        self._require_connection()

        try:
            from ib_insync import Option
        except ImportError:
            return None

        contract = Option(
            symbol=symbol,
            lastTradeDateOrContractMonth=expiry,
            strike=strike,
            right=right,
            exchange=exchange,
            currency=currency,
        )
        qualified = self._ib.qualifyContracts(contract)
        if not qualified:
            msg = f"Could not qualify option: {symbol} {expiry} ${strike} {right}"
            raise IBContractError(msg)
        ticker = self._ib.reqMktData(
            qualified[0],
            "",
            snapshot=False,
            regulatorySnapshot=False,
        )
        self._ib.sleep(2)
        return ticker

    def qualify_contract(self, contract: Any) -> Any:
        """Qualify a single contract. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        results = self._ib.qualifyContracts(contract)
        if not results:
            msg = f"Failed to qualify contract: {contract}"
            raise IBContractError(msg)
        return results[0]

    def qualify_contracts(self, *contracts: Any) -> list | None:
        """Qualify multiple contracts in a single call. Returns ``None``."""
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.qualifyContracts(*contracts)

    # -- execution / fill operations ----------------------------------------

    def get_executions(self, exec_filter: Any = None) -> list | None:
        """Return recent executions. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        if exec_filter is not None:
            return self._ib.reqExecutions(exec_filter)
        return self._ib.reqExecutions()

    def get_fills(self) -> list | None:
        """Return recent fills for this session. Returns ``None``."""
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.fills()

    def wait_for_fill(
        self,
        trade: Any,
        timeout: int = 60,
        poll_interval: float = 1.0,
    ) -> Any:
        """Wait for a trade to fill. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()

        elapsed = 0.0
        while elapsed < timeout:
            self._ib.sleep(poll_interval)
            elapsed += poll_interval

            status = trade.orderStatus.status
            if status == "Filled":
                logger.info(
                    "Order filled: orderId=%s avg=%.2f qty=%s",
                    trade.order.orderId,
                    trade.orderStatus.avgFillPrice,
                    trade.orderStatus.filled,
                )
                return trade

            if status in {"Cancelled", "ApiCancelled"}:
                msg = f"Order cancelled (orderId={trade.order.orderId}): {status}"
                raise IBOrderError(msg)

            if status == "Inactive":
                logger.warning(
                    "Order inactive: orderId=%s — may be rejected",
                    trade.order.orderId,
                )

        msg = (
            f"Order not filled within {timeout}s "
            f"(orderId={trade.order.orderId}, status={trade.orderStatus.status})"
        )
        raise IBTimeoutError(msg)

    # -- historical data ----------------------------------------------------

    def get_historical_data(
        self,
        contract: Any,
        *,
        duration: str = "1 D",
        bar_size: str = "1 hour",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        end_date: str = "",
        keep_up_to_date: bool = False,
    ) -> list | None:
        """Request historical bar data. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.reqHistoricalData(
            contract,
            endDateTime=end_date,
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=1,
            keepUpToDate=keep_up_to_date,
        )

    # -- contract details ---------------------------------------------------

    def get_contract_details(self, contract: Any) -> list | None:
        """Return full contract details. Returns ``None`` when unavailable."""
        if not self.is_available():
            return None
        self._require_connection()
        return self._ib.reqContractDetails(contract)

    # -- Flex Query ---------------------------------------------------------

    def run_flex_query(self, query_id: int, token: str) -> Any:
        """Execute an IB Flex Query. Returns ``None`` when unavailable."""
        if not HAS_IB:
            return None
        try:
            from ib_insync import FlexReport
        except ImportError:
            return None

        try:
            report = FlexReport(token=token, queryId=query_id)
            logger.info("Flex query %d executed successfully", query_id)
            return report
        except Exception as exc:
            msg = f"Flex query {query_id} failed: {exc}"
            raise IBError(msg) from exc

    # -- utility ------------------------------------------------------------

    def sleep(self, seconds: float) -> None:
        """Sleep while processing IB events (``ib.sleep()``). No-op when unavailable."""
        if self._ib is not None and self._connected:
            self._ib.sleep(seconds)
