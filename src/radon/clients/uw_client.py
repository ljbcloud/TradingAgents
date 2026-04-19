"""Comprehensive Unusual Whales API client with graceful degradation.

Provides typed, session-managed access to all UW endpoints with automatic
retry, rate-limit backoff, and a clear exception hierarchy.

Requires the ``httpx`` optional dependency and a ``UW_TOKEN`` environment
variable.  When either is missing the client degrades gracefully — every
endpoint method returns ``None`` and ``is_available()`` reports ``False``.

Usage::

    from radon.clients.uw_client import UWClient

    client = UWClient()
    if client.is_available():
        flow = client.get_darkpool_flow("AAPL")
    client.close()

    # Or as context manager:
    with UWClient() as client:
        info = client.get_stock_info("AAPL")
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Self

from radon.clients.base import check_optional_dependency

# ruff: noqa: PLR0904

HAS_HTTPX = check_optional_dependency("httpx")

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# Exception Hierarchy
# ══════════════════════════════════════════════════════════════════════


class UWAPIError(Exception):
    """Base exception for all UW API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict | None = None,
    ):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class UWAuthError(UWAPIError):
    """Authentication or authorization failure (401/403)."""


class UWRateLimitError(UWAPIError):
    """Rate limit exceeded (429)."""


class UWNotFoundError(UWAPIError):
    """Resource not found (404)."""


class UWValidationError(UWAPIError):
    """Invalid parameters (422)."""


class UWServerError(UWAPIError):
    """Server-side error (5xx)."""


# Status codes that are safe to retry
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Default configuration
_DEFAULT_BASE_URL = "https://api.unusualwhales.com/api"
_DEFAULT_TIMEOUT = 30
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_FACTOR = 1.0  # seconds; exponential backoff multiplier


# ══════════════════════════════════════════════════════════════════════
# Client
# ══════════════════════════════════════════════════════════════════════


class UWClient:
    """Comprehensive Unusual Whales REST API client.

    Features:
      - Connection-pooled ``httpx.Client``
      - Automatic retry with exponential backoff for transient errors
      - Rate-limit awareness (Retry-After header)
      - Clear exception hierarchy mapped to HTTP status codes
      - Graceful degradation when httpx or UW_TOKEN is unavailable
    """

    # ── init / lifecycle ───────────────────────────────────────────

    def __init__(
        self,
        token: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: int = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_factor: float = _DEFAULT_BACKOFF_FACTOR,
    ):
        self._token = token or os.environ.get("UW_TOKEN", "")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

        self._available = bool(HAS_HTTPX and self._token)
        self._client: Any = None

        if self._available:
            self._init_httpx_client()

    def _init_httpx_client(self) -> None:
        """Lazily initialise the httpx.Client (called only when available)."""
        import httpx

        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
                "User-Agent": "tradingagents/1.0",
            },
            timeout=self._timeout,
        )

    def is_available(self) -> bool:
        """Return ``True`` when httpx is importable *and* a token is set."""
        return self._available

    def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── internal request layer ─────────────────────────────────────

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict | None:
        """Make an authenticated GET with retry and error mapping.

        Returns ``None`` when the client is unavailable.
        """
        if not self._available:
            return None

        import httpx

        endpoint = endpoint.lstrip("/")
        url = f"{self._base_url}/{endpoint}"

        last_exc: UWAPIError | Exception | None = None

        for attempt in range(1 + self._max_retries):
            try:
                resp = self._client.get(url, params=params)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    self._sleep_backoff(attempt)
                    continue
                msg = f"Connection failed after {attempt + 1} attempts: {exc}"
                raise UWAPIError(msg) from exc

            status = resp.status_code

            if status == 200:
                return resp.json()

            # ── classify error ──
            body = self._safe_json(resp)
            msg = body.get("message", "") or resp.reason_phrase or f"HTTP {status}"

            if status == 429:
                exc: UWAPIError = UWRateLimitError(
                    msg, status_code=status, response_body=body
                )
            elif status in {401, 403}:
                raise UWAuthError(msg, status_code=status, response_body=body)
            elif status == 404:
                raise UWNotFoundError(msg, status_code=status, response_body=body)
            elif status == 422:
                raise UWValidationError(msg, status_code=status, response_body=body)
            elif status >= 500:
                exc = UWServerError(msg, status_code=status, response_body=body)
            elif status >= 400:
                raise UWAPIError(msg, status_code=status, response_body=body)
            else:
                raise UWAPIError(msg, status_code=status, response_body=body)

            # retryable path
            last_exc = exc
            if attempt < self._max_retries:
                sleep_time = self._get_retry_delay(resp, attempt)
                time.sleep(sleep_time)
                continue

            raise exc

        # Should not reach here, but guard against it
        raise last_exc  # type: ignore[misc]

    def _sleep_backoff(self, attempt: int) -> None:
        """Sleep with exponential backoff."""
        delay = self._backoff_factor * (2**attempt)
        time.sleep(delay)

    @staticmethod
    def _get_retry_delay(resp: Any, attempt: int) -> float:
        """Calculate retry delay from Retry-After header or exponential backoff."""
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 1.0)
            except (ValueError, TypeError):
                pass
        return 1.0 * (2**attempt)

    @staticmethod
    def _safe_json(resp: Any) -> dict:
        try:
            return resp.json()
        except Exception:
            return {}

    @staticmethod
    def _build_params(**kwargs: Any) -> dict[str, Any]:
        """Build query params dict, excluding any keys whose value is None."""
        return {k: v for k, v in kwargs.items() if v is not None}

    # ══════════════════════════════════════════════════════════════════
    # DARK POOL ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_darkpool_flow(
        self,
        ticker: str,
        *,
        date: str | None = None,
        min_premium: int | None = None,
        max_premium: int | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
        limit: int | None = None,
    ) -> dict | None:
        """GET /api/darkpool/{ticker} - Dark pool trades for a ticker."""
        params = self._build_params(
            date=date,
            min_premium=min_premium,
            max_premium=max_premium,
            min_size=min_size,
            max_size=max_size,
            limit=limit,
        )
        return self._get(f"darkpool/{ticker.upper()}", params=params)

    def get_darkpool_recent(
        self,
        *,
        limit: int | None = None,
    ) -> dict | None:
        """GET /api/darkpool/recent - Latest dark pool trades across all tickers."""
        params = self._build_params(limit=limit)
        return self._get("darkpool/recent", params=params)

    # ══════════════════════════════════════════════════════════════════
    # OPTIONS FLOW ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_flow_alerts(
        self,
        *,
        ticker: str | None = None,
        min_premium: int | None = None,
        max_premium: int | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
        is_sweep: bool | None = None,
        is_floor: bool | None = None,
        is_call: bool | None = None,
        is_put: bool | None = None,
        is_ask_side: bool | None = None,
        is_bid_side: bool | None = None,
        is_otm: bool | None = None,
        all_opening: bool | None = None,
        min_dte: int | None = None,
        max_dte: int | None = None,
        min_volume_oi_ratio: float | None = None,
        max_volume_oi_ratio: float | None = None,
        rule_name: list | None = None,
        issue_types: list | None = None,
        is_multi_leg: bool | None = None,
        vol_greater_oi: bool | None = None,
        size_greater_oi: bool | None = None,
        min_marketcap: int | None = None,
        max_marketcap: int | None = None,
        newer_than: str | None = None,
        older_than: str | None = None,
        limit: int | None = None,
    ) -> dict | None:
        """GET /api/option-trades/flow-alerts - Options flow alerts with rich filtering."""
        params = self._build_params(
            ticker_symbol=ticker.upper() if ticker else None,
            min_premium=min_premium,
            max_premium=max_premium,
            min_size=min_size,
            max_size=max_size,
            is_sweep=is_sweep,
            is_floor=is_floor,
            is_call=is_call,
            is_put=is_put,
            is_ask_side=is_ask_side,
            is_bid_side=is_bid_side,
            is_otm=is_otm,
            all_opening=all_opening,
            min_dte=min_dte,
            max_dte=max_dte,
            min_volume_oi_ratio=min_volume_oi_ratio,
            max_volume_oi_ratio=max_volume_oi_ratio,
            is_multi_leg=is_multi_leg,
            vol_greater_oi=vol_greater_oi,
            size_greater_oi=size_greater_oi,
            min_marketcap=min_marketcap,
            max_marketcap=max_marketcap,
            newer_than=newer_than,
            older_than=older_than,
            limit=limit,
        )
        if rule_name is not None:
            params["rule_name[]"] = rule_name
        if issue_types is not None:
            params["issue_types[]"] = issue_types

        return self._get("option-trades/flow-alerts", params=params)

    def get_flow_alerts_by_ticker(
        self,
        ticker: str,
        *,
        min_premium: int | None = None,
        max_premium: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> dict | None:
        """Convenience wrapper: flow alerts filtered to a single ticker."""
        return self.get_flow_alerts(
            ticker=ticker,
            min_premium=min_premium,
            max_premium=max_premium,
            limit=limit,
            **kwargs,
        )

    def get_stock_flow_alerts(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/flow-alerts - Per-stock flow alerts."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/flow-alerts", params=params)

    def get_flow_per_strike(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/flow-per-strike"""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/flow-per-strike", params=params)

    def get_flow_per_expiry(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/flow-per-expiry"""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/flow-per-expiry", params=params)

    def get_net_prem_ticks(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/net-prem-ticks - Net premium ticks (1-min intervals)."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/net-prem-ticks", params=params)

    # ══════════════════════════════════════════════════════════════════
    # STOCK INFORMATION ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_stock_info(self, ticker: str) -> dict | None:
        """GET /api/stock/{ticker}/info - Company info, sector, market cap."""
        return self._get(f"stock/{ticker.upper()}/info")

    def get_stock_state(self, ticker: str) -> dict | None:
        """GET /api/stock/{ticker}/stock-state - Last stock state (OHLCV)."""
        return self._get(f"stock/{ticker.upper()}/stock-state")

    def get_options_volume(self, ticker: str) -> dict | None:
        """GET /api/stock/{ticker}/options-volume - Options volume & premium summary."""
        return self._get(f"stock/{ticker.upper()}/options-volume")

    def get_stock_ohlc(
        self, ticker: str, candle_size: str = "1d", **kwargs: Any
    ) -> dict | None:
        """GET /api/stock/{ticker}/ohlc/{candle_size} - OHLC price data."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/ohlc/{candle_size}", params=params)

    # ══════════════════════════════════════════════════════════════════
    # OPTIONS CHAIN ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_option_contracts(
        self,
        ticker: str,
        *,
        expiry: str | None = None,
        option_type: str | None = None,
        vol_greater_oi: bool | None = None,
        exclude_zero_vol_chains: bool | None = None,
        maybe_otm_only: bool | None = None,
    ) -> dict | None:
        """GET /api/stock/{ticker}/option-contracts - All option contracts."""
        params = self._build_params(
            expiry=expiry,
            option_type=option_type,
            vol_greater_oi=vol_greater_oi,
            exclude_zero_vol_chains=exclude_zero_vol_chains,
            maybe_otm_only=maybe_otm_only,
        )
        return self._get(f"stock/{ticker.upper()}/option-contracts", params=params)

    def get_option_chain(self, ticker: str, expiry: str, **kwargs: Any) -> dict | None:
        """Convenience: get_option_contracts filtered to a single expiration."""
        return self.get_option_contracts(ticker, expiry=expiry, **kwargs)

    def get_expiry_breakdown(self, ticker: str) -> dict | None:
        """GET /api/stock/{ticker}/expiry-breakdown - Expirations with volume/OI."""
        return self._get(f"stock/{ticker.upper()}/expiry-breakdown")

    def get_option_contract_historic(self, option_id: str) -> dict | None:
        """GET /api/option-contract/{id}/historic - Historical data for a contract."""
        return self._get(f"option-contract/{option_id}/historic")

    def get_greeks(
        self, ticker: str, *, expiry: str | None = None, **kwargs: Any
    ) -> dict | None:
        """GET /api/stock/{ticker}/greeks - Greeks for each strike at an expiry."""
        params = self._build_params(expiry=expiry, **kwargs)
        return self._get(f"stock/{ticker.upper()}/greeks", params=params)

    # ══════════════════════════════════════════════════════════════════
    # GREEK EXPOSURE (GEX) ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_greek_exposure(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/greek-exposure - Total greek exposure over time."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/greek-exposure", params=params)

    def get_greek_exposure_by_strike(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/greek-exposure/strike"""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/greek-exposure/strike", params=params)

    def get_greek_exposure_by_expiry(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/greek-exposure/expiry"""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/greek-exposure/expiry", params=params)

    def get_greek_flow(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/greek-flow - Intraday delta/vega flow."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/greek-flow", params=params)

    # ══════════════════════════════════════════════════════════════════
    # VOLATILITY ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_realized_volatility(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/volatility/realized - IV vs realized volatility."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/volatility/realized", params=params)

    def get_volatility_term_structure(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/volatility/term-structure - IV term structure."""
        params = self._build_params(**kwargs)
        return self._get(
            f"stock/{ticker.upper()}/volatility/term-structure", params=params
        )

    def get_volatility_stats(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/volatility/stats - Comprehensive volatility stats."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/volatility/stats", params=params)

    def get_iv_rank(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/iv-rank - IV rank data over time."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/iv-rank", params=params)

    # ══════════════════════════════════════════════════════════════════
    # ANALYST RATINGS ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_analyst_ratings(
        self,
        *,
        ticker: str | None = None,
        action: str | None = None,
        recommendation: str | None = None,
        limit: int | None = None,
    ) -> dict | None:
        """GET /api/screener/analysts - Analyst ratings and price targets."""
        params = self._build_params(
            ticker=ticker.upper() if ticker else None,
            action=action,
            recommendation=recommendation,
            limit=limit,
        )
        return self._get("screener/analysts", params=params)

    def get_analyst_ratings_by_ticker(self, ticker: str, **kwargs: Any) -> dict | None:
        """Convenience: analyst ratings filtered to a single ticker."""
        return self.get_analyst_ratings(ticker=ticker, **kwargs)

    # ══════════════════════════════════════════════════════════════════
    # SEASONALITY ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_monthly_seasonality(self, ticker: str) -> dict | None:
        """GET /api/seasonality/{ticker}/monthly - Average return by month."""
        return self._get(f"seasonality/{ticker.upper()}/monthly")

    def get_year_month_seasonality(self, ticker: str) -> dict | None:
        """GET /api/seasonality/{ticker}/year-month - Returns per month per year."""
        return self._get(f"seasonality/{ticker.upper()}/year-month")

    def get_market_seasonality(self) -> dict | None:
        """GET /api/seasonality/market - Market-wide seasonality (SPY, QQQ, etc.)."""
        return self._get("seasonality/market")

    def get_month_performers(self, month: str) -> dict | None:
        """GET /api/seasonality/{month}/performers - Best/worst performers for a month."""
        return self._get(f"seasonality/{month}/performers")

    # ══════════════════════════════════════════════════════════════════
    # SHORT INTEREST ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_short_interest(self, ticker: str) -> dict | None:
        """GET /api/shorts/{ticker}/interest-float/v2 - Short interest and float data."""
        return self._get(f"shorts/{ticker.upper()}/interest-float/v2")

    def get_short_data(self, ticker: str) -> dict | None:
        """GET /api/shorts/{ticker}/data - Short data including borrow rate."""
        return self._get(f"shorts/{ticker.upper()}/data")

    def get_short_volume_ratio(self, ticker: str) -> dict | None:
        """GET /api/shorts/{ticker}/volume-and-ratio - Short volume and ratio."""
        return self._get(f"shorts/{ticker.upper()}/volume-and-ratio")

    # ══════════════════════════════════════════════════════════════════
    # INSTITUTIONAL DATA ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_institutional_ownership(self, ticker: str) -> dict | None:
        """GET /api/institution/{ticker}/ownership - Institutional ownership."""
        return self._get(f"institution/{ticker.upper()}/ownership")

    def get_institution_holdings(self, name: str, **kwargs: Any) -> dict | None:
        """GET /api/institution/{name}/holdings - Holdings for an institution."""
        params = self._build_params(**kwargs)
        return self._get(f"institution/{name}/holdings", params=params)

    def get_institutions(self, **kwargs: Any) -> dict | None:
        """GET /api/institutions - List of institutions."""
        params = self._build_params(**kwargs)
        return self._get("institutions", params=params)

    # ══════════════════════════════════════════════════════════════════
    # INSIDER TRADING ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_insider_transactions(
        self,
        *,
        ticker: str | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> dict | None:
        """GET /api/insider/transactions - Insider buy/sell transactions."""
        params = self._build_params(
            ticker=ticker.upper() if ticker else None,
            limit=limit,
            **kwargs,
        )
        return self._get("insider/transactions", params=params)

    def get_insider_by_ticker(self, ticker: str) -> dict | None:
        """GET /api/insider/{ticker} - Insiders for a ticker."""
        return self._get(f"insider/{ticker.upper()}")

    def get_insider_ticker_flow(self, ticker: str) -> dict | None:
        """GET /api/insider/{ticker}/ticker-flow - Aggregated insider flow."""
        return self._get(f"insider/{ticker.upper()}/ticker-flow")

    # ══════════════════════════════════════════════════════════════════
    # CONGRESS TRADING ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_congress_recent_trades(
        self,
        *,
        ticker: str | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> dict | None:
        """GET /api/congress/recent-trades - Latest congress trades."""
        params = self._build_params(
            ticker=ticker.upper() if ticker else None,
            limit=limit,
            **kwargs,
        )
        return self._get("congress/recent-trades", params=params)

    def get_congress_trader(
        self, *, name: str | None = None, **kwargs: Any
    ) -> dict | None:
        """GET /api/congress/congress-trader - Trades by congress member."""
        params = self._build_params(name=name, **kwargs)
        return self._get("congress/congress-trader", params=params)

    # ══════════════════════════════════════════════════════════════════
    # ETF ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_etf_info(self, ticker: str) -> dict | None:
        """GET /api/etfs/{ticker}/info - ETF information."""
        return self._get(f"etfs/{ticker.upper()}/info")

    def get_etf_holdings(self, ticker: str) -> dict | None:
        """GET /api/etfs/{ticker}/holdings - ETF holdings."""
        return self._get(f"etfs/{ticker.upper()}/holdings")

    def get_etf_exposure(self, ticker: str) -> dict | None:
        """GET /api/etfs/{ticker}/exposure - ETFs containing a ticker."""
        return self._get(f"etfs/{ticker.upper()}/exposure")

    # ══════════════════════════════════════════════════════════════════
    # MARKET OVERVIEW ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_market_tide(self) -> dict | None:
        """GET /api/market/market-tide - Market-wide options sentiment."""
        return self._get("market/market-tide")

    def get_sector_etfs(self) -> dict | None:
        """GET /api/market/sector-etfs - SPDR sector ETF stats."""
        return self._get("market/sector-etfs")

    def get_total_options_volume(self) -> dict | None:
        """GET /api/market/total-options-volume - Total market options volume."""
        return self._get("market/total-options-volume")

    def get_oi_change(self) -> dict | None:
        """GET /api/market/oi-change - Biggest OI changes."""
        return self._get("market/oi-change")

    def get_economic_calendar(self) -> dict | None:
        """GET /api/market/economic-calendar - Economic events."""
        return self._get("market/economic-calendar")

    def get_fda_calendar(self) -> dict | None:
        """GET /api/market/fda-calendar - FDA calendar events."""
        return self._get("market/fda-calendar")

    # ══════════════════════════════════════════════════════════════════
    # EARNINGS ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_earnings_premarket(self) -> dict | None:
        """GET /api/earnings/premarket - Premarket earnings."""
        return self._get("earnings/premarket")

    def get_earnings_afterhours(self) -> dict | None:
        """GET /api/earnings/afterhours - Afterhours earnings."""
        return self._get("earnings/afterhours")

    def get_earnings_by_ticker(self, ticker: str) -> dict | None:
        """GET /api/earnings/{ticker} - Historical earnings for ticker."""
        return self._get(f"earnings/{ticker.upper()}")

    # ══════════════════════════════════════════════════════════════════
    # SCREENER ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_stock_screener(self, **kwargs: Any) -> dict | None:
        """GET /api/screener/stocks - Stock screener with many filters."""
        params = self._build_params(**kwargs)
        return self._get("screener/stocks", params=params)

    def get_option_contracts_screener(self, **kwargs: Any) -> dict | None:
        """GET /api/screener/option-contracts - Options contract screener (Hottest Chains)."""
        params = self._build_params(**kwargs)
        return self._get("screener/option-contracts", params=params)

    def get_short_screener(self, **kwargs: Any) -> dict | None:
        """GET /api/short_screener - Screen for high short interest."""
        params = self._build_params(**kwargs)
        return self._get("short_screener", params=params)

    # ══════════════════════════════════════════════════════════════════
    # NEWS ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_news_headlines(
        self,
        *,
        ticker: str | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> dict | None:
        """GET /api/news/headlines - News headlines."""
        params = self._build_params(
            ticker=ticker.upper() if ticker else None,
            limit=limit,
            **kwargs,
        )
        return self._get("news/headlines", params=params)

    # ══════════════════════════════════════════════════════════════════
    # MAX PAIN / OI CHANGE
    # ══════════════════════════════════════════════════════════════════

    def get_max_pain(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/max-pain - Max pain by expiry."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/max-pain", params=params)

    def get_stock_oi_change(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/oi-change - OI change for a ticker."""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/oi-change", params=params)

    # ══════════════════════════════════════════════════════════════════
    # LIT FLOW ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_lit_flow_recent(self, **kwargs: Any) -> dict | None:
        """GET /api/lit-flow/recent - Recent lit (exchange) trades."""
        params = self._build_params(**kwargs)
        return self._get("lit-flow/recent", params=params)

    def get_lit_flow_by_ticker(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/lit-flow/{ticker} - Lit trades for a ticker."""
        params = self._build_params(**kwargs)
        return self._get(f"lit-flow/{ticker.upper()}", params=params)

    # ══════════════════════════════════════════════════════════════════
    # ADDITIONAL STOCK ENDPOINTS
    # ══════════════════════════════════════════════════════════════════

    def get_spot_exposures(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/spot-exposures"""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/spot-exposures", params=params)

    def get_stock_ownership(self, ticker: str) -> dict | None:
        """GET /api/stock/{ticker}/ownership"""
        return self._get(f"stock/{ticker.upper()}/ownership")

    def get_atm_chains(self, ticker: str, **kwargs: Any) -> dict | None:
        """GET /api/stock/{ticker}/atm-chains"""
        params = self._build_params(**kwargs)
        return self._get(f"stock/{ticker.upper()}/atm-chains", params=params)

    def get_historical_risk_reversal_skew(
        self, ticker: str, **kwargs: Any
    ) -> dict | None:
        """GET /api/stock/{ticker}/historical-risk-reversal-skew"""
        params = self._build_params(**kwargs)
        return self._get(
            f"stock/{ticker.upper()}/historical-risk-reversal-skew", params=params
        )
