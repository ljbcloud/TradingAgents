"""Characterization tests for dataflows current behavior."""


# ruff: noqa: PT006 - parametrize string format is acceptable
# ruff: noqa: PT011 - broad exception matches are acceptable in tests
# ruff: noqa: TRY003 - long exception messages in test mocks are acceptable
# ruff: noqa: EM101, EM102 - string literals in test exceptions are acceptable
# ruff: noqa: ARG005 - unused lambda arguments in test mocks are acceptable

from __future__ import annotations

from datetime import datetime as _datetime

import pandas as pd
import pytest

from dataflows import (
    alpha_vantage_fundamentals,
    alpha_vantage_indicator,
    alpha_vantage_news,
    alpha_vantage_stock,
    interface,
    y_finance,
    yfinance_news,
)
from dataflows.alpha_vantage_common import AlphaVantageRateLimitError
from dataflows.exceptions import VendorError

EXPECTED_METHODS = (
    "get_stock_data",
    "get_indicators",
    "get_fundamentals",
    "get_balance_sheet",
    "get_cashflow",
    "get_income_statement",
    "get_news",
    "get_global_news",
    "get_insider_transactions",
)

METHOD_ARGS: dict[str, tuple] = {
    "get_stock_data": ("AAPL", "2024-01-01", "2024-01-10"),
    "get_indicators": ("AAPL", "rsi", "2024-01-15", 3),
    "get_fundamentals": ("AAPL", "2024-01-15"),
    "get_balance_sheet": ("AAPL", "quarterly", "2024-01-15"),
    "get_cashflow": ("AAPL", "quarterly", "2024-01-15"),
    "get_income_statement": ("AAPL", "quarterly", "2024-01-15"),
    "get_news": ("AAPL", "2024-01-01", "2024-01-15"),
    "get_global_news": ("2024-01-15", 7, 10),
    "get_insider_transactions": ("AAPL",),
}

METHOD_CATEGORY: dict[str, str] = {
    "get_stock_data": "core_stock_apis",
    "get_indicators": "technical_indicators",
    "get_fundamentals": "fundamental_data",
    "get_balance_sheet": "fundamental_data",
    "get_cashflow": "fundamental_data",
    "get_income_statement": "fundamental_data",
    "get_news": "news_data",
    "get_global_news": "news_data",
    "get_insider_transactions": "news_data",
}


class _FixedDateTime(_datetime):
    """Fixed datetime used to stabilize baseline strings."""

    @classmethod
    def now(cls, tz=None):
        return cls(2024, 1, 20, 12, 34, 56, tzinfo=tz)


@pytest.mark.parametrize("method", EXPECTED_METHODS)
def test_vendor_methods_contains_expected_method_names(method):
    """Characterize that every expected dataflow method is exposed in VENDOR_METHODS."""
    assert method in interface.VENDOR_METHODS


@pytest.mark.parametrize("method, category", METHOD_CATEGORY.items())
def test_get_category_for_method_returns_current_mapping(method, category):
    """Characterize category routing map for each exported dataflow method."""
    assert interface.get_category_for_method(method) == category


def test_get_category_for_method_unknown_method_raises_value_error():
    """Characterize the current error raised for methods absent from TOOLS_CATEGORIES."""
    with pytest.raises(ValueError, match="not found in any category"):
        interface.get_category_for_method("not_supported")


def test_get_vendor_prefers_tool_level_vendor_over_category_vendor(monkeypatch):
    """Characterize precedence of tool_vendors over data_vendors in get_vendor."""
    monkeypatch.setattr(
        interface,
        "get_config",
        lambda: {
            "tool_vendors": {"get_stock_data": "alpha_vantage"},
            "data_vendors": {"core_stock_apis": "yfinance"},
        },
    )

    assert interface.get_vendor("core_stock_apis", "get_stock_data") == "alpha_vantage"


def test_get_vendor_falls_back_to_category_vendor(monkeypatch):
    """Characterize category-level fallback when tool_vendors has no method override."""
    monkeypatch.setattr(
        interface,
        "get_config",
        lambda: {
            "tool_vendors": {},
            "data_vendors": {"core_stock_apis": "yfinance"},
        },
    )

    assert interface.get_vendor("core_stock_apis", "get_stock_data") == "yfinance"


def test_get_vendor_defaults_to_literal_default_when_missing(monkeypatch):
    """Characterize current default vendor string when category has no configured vendor."""
    monkeypatch.setattr(
        interface, "get_config", lambda: {"tool_vendors": {}, "data_vendors": {}}
    )

    assert interface.get_vendor("news_data", "get_news") == "default"


@pytest.mark.parametrize("method", EXPECTED_METHODS)
@pytest.mark.parametrize("configured_vendor", ["alpha_vantage", "yfinance"])
def test_route_to_vendor_uses_primary_vendor_without_fallback(
    monkeypatch,
    method,
    configured_vendor,
):
    """Characterize that route_to_vendor returns first successful configured vendor result."""
    args = METHOD_ARGS[method]

    def primary(*called_args, **_kwargs):
        return f"{configured_vendor}:{method}:{called_args}"

    def secondary(*_called_args, **_kwargs):
        return "secondary-should-not-run"

    monkeypatch.setattr(interface, "get_vendor", lambda _c, _m: configured_vendor)
    monkeypatch.setitem(
        interface.VENDOR_METHODS,
        method,
        {configured_vendor: primary, "fallback": secondary},
    )

    assert (
        interface.route_to_vendor(method, *args)
        == f"{configured_vendor}:{method}:{args}"
    )


@pytest.mark.parametrize("method", EXPECTED_METHODS)
def test_route_to_vendor_falls_back_only_on_alpha_vantage_rate_limit(
    monkeypatch, method
):
    """Characterize fallback behavior when the primary vendor raises AlphaVantageRateLimitError."""
    args = METHOD_ARGS[method]

    def rate_limited(*_args, **_kwargs):
        raise AlphaVantageRateLimitError("too many requests")

    def fallback(*called_args, **_kwargs):
        return f"fallback:{method}:{called_args}"

    monkeypatch.setattr(interface, "get_vendor", lambda _c, _m: "alpha_vantage")
    monkeypatch.setitem(
        interface.VENDOR_METHODS,
        method,
        {"alpha_vantage": rate_limited, "yfinance": fallback},
    )

    assert interface.route_to_vendor(method, *args) == f"fallback:{method}:{args}"


@pytest.mark.parametrize("method", EXPECTED_METHODS)
def test_route_to_vendor_does_not_fallback_on_generic_exception(monkeypatch, method):
    """Characterize that non-rate-limit exceptions bubble instead of triggering vendor fallback."""
    args = METHOD_ARGS[method]

    def broken(*_args, **_kwargs):
        raise RuntimeError(f"boom-{method}")

    def fallback(*_args, **_kwargs):
        return "should-not-run"

    monkeypatch.setattr(interface, "get_vendor", lambda _c, _m: "alpha_vantage")
    monkeypatch.setitem(
        interface.VENDOR_METHODS,
        method,
        {"alpha_vantage": broken, "yfinance": fallback},
    )

    with pytest.raises(RuntimeError, match=f"boom-{method}"):
        interface.route_to_vendor(method, *args)


@pytest.mark.parametrize("method", EXPECTED_METHODS)
def test_route_to_vendor_skips_configured_vendor_not_implemented_for_method(
    monkeypatch, method
):
    """Characterize skipping unsupported configured vendors during fallback chain iteration."""
    args = METHOD_ARGS[method]

    def only_available(*called_args, **_kwargs):
        return f"available:{method}:{called_args}"

    monkeypatch.setattr(interface, "get_vendor", lambda _c, _m: "unknown_vendor")
    monkeypatch.setitem(interface.VENDOR_METHODS, method, {"yfinance": only_available})

    assert interface.route_to_vendor(method, *args) == f"available:{method}:{args}"


@pytest.mark.parametrize("method", EXPECTED_METHODS)
def test_route_to_vendor_uses_first_entry_when_vendor_mapping_contains_list(
    monkeypatch, method
):
    """Characterize that list-valued vendor implementations call only the first callable."""
    args = METHOD_ARGS[method]

    called = {"first": 0, "second": 0}

    def first_impl(*called_args, **_kwargs):
        called["first"] += 1
        return f"list-first:{method}:{called_args}"

    def second_impl(*_args, **_kwargs):
        called["second"] += 1
        return "list-second"

    monkeypatch.setattr(interface, "get_vendor", lambda _c, _m: "alpha_vantage")
    monkeypatch.setitem(
        interface.VENDOR_METHODS,
        method,
        {"alpha_vantage": [first_impl, second_impl], "yfinance": second_impl},
    )

    assert interface.route_to_vendor(method, *args) == f"list-first:{method}:{args}"
    assert called == {"first": 1, "second": 0}


def test_route_to_vendor_unknown_method_raises_category_lookup_error():
    """Characterize the current error path ordering for an unknown route_to_vendor method."""
    with pytest.raises(ValueError, match="not found in any category"):
        interface.route_to_vendor("does_not_exist")


def test_route_to_vendor_raises_runtime_error_when_all_vendors_rate_limited(
    monkeypatch,
):
    """Characterize RuntimeError after exhausting fallback vendors via rate-limit errors."""

    def rate_limited(*_args, **_kwargs):
        raise AlphaVantageRateLimitError("limited")

    monkeypatch.setattr(interface, "get_vendor", lambda _c, _m: "alpha_vantage")
    monkeypatch.setitem(
        interface.VENDOR_METHODS,
        "get_stock_data",
        {"alpha_vantage": rate_limited, "yfinance": rate_limited},
    )

    with pytest.raises(RuntimeError, match="No available vendor"):
        interface.route_to_vendor("get_stock_data", *METHOD_ARGS["get_stock_data"])


def test_get_stock_selects_compact_outputsize_for_recent_start_date(monkeypatch):
    """Characterize get_stock outputsize=compact branch for ranges within 100 days of now."""
    monkeypatch.setattr(alpha_vantage_stock, "datetime", _FixedDateTime)

    call_log = {}

    def fake_request(function_name, params):
        call_log["function_name"] = function_name
        call_log["params"] = params
        return "raw-csv"

    monkeypatch.setattr(alpha_vantage_stock, "_make_api_request", fake_request)
    monkeypatch.setattr(
        alpha_vantage_stock,
        "_filter_csv_by_date_range",
        lambda csv_data, start_date, end_date: (
            f"filtered:{csv_data}:{start_date}:{end_date}"
        ),
    )

    result = alpha_vantage_stock.get_stock("AAPL", "2024-01-10", "2024-01-20")

    assert result == "filtered:raw-csv:2024-01-10:2024-01-20"
    assert call_log["function_name"] == "TIME_SERIES_DAILY_ADJUSTED"
    assert call_log["params"]["outputsize"] == "compact"
    assert call_log["params"]["symbol"] == "AAPL"


def test_get_stock_selects_full_outputsize_for_older_start_date(monkeypatch):
    """Characterize get_stock outputsize=full branch for older historical ranges."""
    monkeypatch.setattr(alpha_vantage_stock, "datetime", _FixedDateTime)

    observed = {}
    monkeypatch.setattr(
        alpha_vantage_stock,
        "_make_api_request",
        lambda _function_name, params: (
            observed.setdefault("outputsize", params["outputsize"]) and "csv"
        ),
    )
    monkeypatch.setattr(
        alpha_vantage_stock, "_filter_csv_by_date_range", lambda csv_data, *_: csv_data
    )

    result = alpha_vantage_stock.get_stock("AAPL", "2023-01-01", "2023-01-10")

    assert result == "csv"
    assert observed["outputsize"] == "full"


def test_get_stock_invalid_date_raises_value_error_before_api_call(monkeypatch):
    """Characterize invalid date input handling in Alpha Vantage stock adapter."""
    called = {"api": 0}
    monkeypatch.setattr(
        alpha_vantage_stock,
        "_make_api_request",
        lambda *_args, **_kwargs: called.__setitem__("api", called["api"] + 1),
    )

    with pytest.raises(ValueError):
        alpha_vantage_stock.get_stock("AAPL", "not-a-date", "2024-01-01")

    assert called["api"] == 0


def test_get_indicator_unsupported_indicator_raises_value_error():
    """Characterize validation error for unsupported indicator names."""
    with pytest.raises(ValueError, match="is not supported"):
        alpha_vantage_indicator.get_indicator("AAPL", "not_real", "2024-01-15", 5)


def test_get_indicator_vwma_returns_informative_message_without_api_call(monkeypatch):
    """Characterize current VWMA behavior (informative static response, no API call)."""
    call_count = {"count": 0}
    monkeypatch.setattr(
        alpha_vantage_indicator,
        "_make_api_request",
        lambda *_args, **_kwargs: call_count.__setitem__(
            "count", call_count["count"] + 1
        ),
    )

    result = alpha_vantage_indicator.get_indicator("AAPL", "vwma", "2024-01-15", 3)

    assert "VWMA calculation requires OHLCV data" in result
    assert call_count["count"] == 0


def test_get_indicator_raises_vendor_error_when_csv_has_no_data_rows(monkeypatch):
    """Characterize empty CSV handling for Alpha Vantage indicator data."""
    monkeypatch.setattr(
        alpha_vantage_indicator,
        "_make_api_request",
        lambda *_args, **_kwargs: "time,RSI",
    )

    with pytest.raises(VendorError, match="Error retrieving rsi data"):
        alpha_vantage_indicator.get_indicator("AAPL", "rsi", "2024-01-15", 5)


def test_get_indicator_raises_vendor_error_when_time_column_missing(monkeypatch):
    """Characterize indicator CSV parsing error when 'time' column is absent."""
    csv_data = "date,RSI\n2024-01-15,50.0"
    monkeypatch.setattr(
        alpha_vantage_indicator, "_make_api_request", lambda *_args, **_kwargs: csv_data
    )

    with pytest.raises(VendorError, match="Error retrieving rsi data"):
        alpha_vantage_indicator.get_indicator("AAPL", "rsi", "2024-01-15", 5)


def test_get_indicator_raises_vendor_error_when_target_column_missing(monkeypatch):
    """Characterize indicator CSV parsing error when expected value column is absent."""
    csv_data = "time,VALUE\n2024-01-15,50.0"
    monkeypatch.setattr(
        alpha_vantage_indicator, "_make_api_request", lambda *_args, **_kwargs: csv_data
    )

    with pytest.raises(VendorError, match="Error retrieving rsi data"):
        alpha_vantage_indicator.get_indicator("AAPL", "rsi", "2024-01-15", 5)


@pytest.mark.parametrize(
    "indicator, csv_data, expected_line",
    [
        (
            "rsi",
            "time,RSI\n2024-01-14,40\n2024-01-15,50\n",
            "2024-01-15: 50",
        ),
        (
            "macd",
            "time,MACD,MACD_Signal,MACD_Hist\n2024-01-15,1.0,0.5,0.5\n",
            "2024-01-15: 1.0",
        ),
        (
            "macds",
            "time,MACD,MACD_Signal,MACD_Hist\n2024-01-15,1.0,0.5,0.5\n",
            "2024-01-15: 0.5",
        ),
        (
            "macdh",
            "time,MACD,MACD_Signal,MACD_Hist\n2024-01-15,1.0,0.5,0.5\n",
            "2024-01-15: 0.5",
        ),
        (
            "boll",
            "time,Real Middle Band,Real Upper Band,Real Lower Band\n2024-01-15,100,120,80\n",
            "2024-01-15: 100",
        ),
        (
            "boll_ub",
            "time,Real Middle Band,Real Upper Band,Real Lower Band\n2024-01-15,100,120,80\n",
            "2024-01-15: 120",
        ),
        (
            "boll_lb",
            "time,Real Middle Band,Real Upper Band,Real Lower Band\n2024-01-15,100,120,80\n",
            "2024-01-15: 80",
        ),
        (
            "close_10_ema",
            "time,EMA\n2024-01-15,101\n",
            "2024-01-15: 101",
        ),
        (
            "close_50_sma",
            "time,SMA\n2024-01-15,98\n",
            "2024-01-15: 98",
        ),
        (
            "close_200_sma",
            "time,SMA\n2024-01-15,95\n",
            "2024-01-15: 95",
        ),
        (
            "atr",
            "time,ATR\n2024-01-15,3.2\n",
            "2024-01-15: 3.2",
        ),
    ],
)
def test_get_indicator_parses_current_csv_formats(
    monkeypatch, indicator, csv_data, expected_line
):
    """Characterize CSV column mappings and formatted indicator output for supported indicators."""
    monkeypatch.setattr(
        alpha_vantage_indicator, "_make_api_request", lambda *_args, **_kwargs: csv_data
    )

    result = alpha_vantage_indicator.get_indicator("AAPL", indicator, "2024-01-15", 1)

    assert expected_line in result
    assert "No description available." not in result


def test_get_indicator_raises_vendor_error_when_request_fails(monkeypatch):
    """Characterize top-level exception wrapping behavior for indicator request failures."""

    def raise_error(*_args, **_kwargs):
        raise RuntimeError("api down")

    monkeypatch.setattr(alpha_vantage_indicator, "_make_api_request", raise_error)

    with pytest.raises(VendorError, match="Error retrieving rsi data"):
        alpha_vantage_indicator.get_indicator("AAPL", "rsi", "2024-01-15", 3)


@pytest.mark.parametrize(
    "func_name, function_name",
    [
        ("get_fundamentals", "OVERVIEW"),
        ("get_balance_sheet", "BALANCE_SHEET"),
        ("get_cashflow", "CASH_FLOW"),
        ("get_income_statement", "INCOME_STATEMENT"),
    ],
)
def test_alpha_vantage_fundamental_functions_forward_to_expected_api_function(
    monkeypatch,
    func_name,
    function_name,
):
    """Characterize API function mapping for Alpha Vantage fundamentals wrappers."""
    recorded = {}

    def fake_request(called_function_name, params):
        recorded["function_name"] = called_function_name
        recorded["params"] = params
        return "payload"

    monkeypatch.setattr(alpha_vantage_fundamentals, "_make_api_request", fake_request)

    func = getattr(alpha_vantage_fundamentals, func_name)
    result = (
        func("AAPL", "quarterly", "2024-01-15")
        if func_name != "get_fundamentals"
        else func("AAPL", "2024-01-15")
    )

    assert result == "payload"
    assert recorded["function_name"] == function_name
    assert recorded["params"] == {"symbol": "AAPL"}


def test_alpha_vantage_news_get_news_formats_dates_and_forwards_params(monkeypatch):
    """Characterize NEWS_SENTIMENT request params for ticker-scoped Alpha Vantage news."""
    called = {}
    monkeypatch.setattr(
        alpha_vantage_news, "format_datetime_for_api", lambda value: f"fmt-{value}"
    )

    def fake_request(function_name, params):
        called["function_name"] = function_name
        called["params"] = params
        return "news-payload"

    monkeypatch.setattr(alpha_vantage_news, "_make_api_request", fake_request)

    result = alpha_vantage_news.get_news("AAPL", "2024-01-01", "2024-01-15")

    assert result == "news-payload"
    assert called["function_name"] == "NEWS_SENTIMENT"
    assert called["params"] == {
        "tickers": "AAPL",
        "time_from": "fmt-2024-01-01",
        "time_to": "fmt-2024-01-15",
    }


def test_alpha_vantage_news_get_global_news_builds_topic_and_limit_params(monkeypatch):
    """Characterize global news request payload generation from curr_date and look_back_days."""
    monkeypatch.setattr(
        alpha_vantage_news, "format_datetime_for_api", lambda value: f"fmt-{value}"
    )
    called = {}

    def fake_request(function_name, params):
        called["function_name"] = function_name
        called["params"] = params
        return "global-news"

    monkeypatch.setattr(alpha_vantage_news, "_make_api_request", fake_request)

    result = alpha_vantage_news.get_global_news(
        "2024-01-15", look_back_days=7, limit=20
    )

    assert result == "global-news"
    assert called["function_name"] == "NEWS_SENTIMENT"
    assert (
        called["params"]["topics"] == "financial_markets,economy_macro,economy_monetary"
    )
    assert called["params"]["time_from"] == "fmt-2024-01-08"
    assert called["params"]["time_to"] == "fmt-2024-01-15"
    assert called["params"]["limit"] == "20"


def test_alpha_vantage_news_get_insider_transactions_forwards_symbol(monkeypatch):
    """Characterize INSIDER_TRANSACTIONS request payload forwarding."""
    called = {}

    def fake_request(function_name, params):
        called["function_name"] = function_name
        called["params"] = params
        return "insider-payload"

    monkeypatch.setattr(alpha_vantage_news, "_make_api_request", fake_request)

    result = alpha_vantage_news.get_insider_transactions("AAPL")

    assert result == "insider-payload"
    assert called == {
        "function_name": "INSIDER_TRANSACTIONS",
        "params": {"symbol": "AAPL"},
    }


@pytest.mark.parametrize(
    "function_name, args, expected_error",
    [
        ("get_YFin_data_online", ("AAPL", "not-a-date", "2024-01-15"), ValueError),
        ("get_YFin_data_online", ("AAPL", "2024-01-01", "not-a-date"), ValueError),
        (
            "get_stock_stats_indicators_window",
            ("AAPL", "rsi", "not-a-date", 3),
            ValueError,
        ),
    ],
)
def test_yfinance_functions_raise_on_invalid_date_inputs(
    function_name, args, expected_error
):
    """Characterize current date parsing exceptions for yfinance-based adapters."""
    with pytest.raises(expected_error):
        getattr(y_finance, function_name)(*args)


def test_get_YFin_data_online_returns_no_data_message_for_empty_history(monkeypatch):
    """Characterize empty-history response string for yfinance stock data adapter."""

    class _Ticker:
        def history(self, start, end):
            return pd.DataFrame()

    monkeypatch.setattr(y_finance.yf, "Ticker", lambda _symbol: _Ticker())

    result = y_finance.get_YFin_data_online("AAPL", "2024-01-01", "2024-01-15")

    assert result == "No data found for symbol 'AAPL' between 2024-01-01 and 2024-01-15"


def test_get_YFin_data_online_formats_header_rounding_and_csv(monkeypatch):
    """Characterize successful stock data formatting including rounding and fixed header shape."""

    class _Ticker:
        def history(self, start, end):
            idx = pd.DatetimeIndex(["2024-01-02", "2024-01-03"], tz="UTC")
            return pd.DataFrame(
                {
                    "Open": [100.1234, 101.5678],
                    "High": [102.2222, 103.9999],
                    "Low": [99.4444, 100.2222],
                    "Close": [101.9876, 102.3333],
                    "Adj Close": [101.9876, 102.3333],
                    "Volume": [1000, 1200],
                },
                index=idx,
            )

    monkeypatch.setattr(y_finance, "datetime", _FixedDateTime)
    monkeypatch.setattr(y_finance, "_get_ticker", lambda _symbol: _Ticker())

    result = y_finance.get_YFin_data_online("AAPL", "2024-01-01", "2024-01-15")

    assert result.startswith("# Stock data for AAPL from 2024-01-01 to 2024-01-15\n")
    assert "# Total records: 2\n" in result
    assert "# Data retrieved on: 2024-01-20 12:34:56" in result
    assert "100.12" in result
    assert "101.99" in result


def test_get_stock_stats_indicators_window_rejects_unsupported_indicator():
    """Characterize indicator whitelist enforcement in yfinance indicator adapter."""
    with pytest.raises(ValueError, match="is not supported"):
        y_finance.get_stock_stats_indicators_window("AAPL", "bad", "2024-01-15", 3)


def test_get_stock_stats_indicators_window_uses_bulk_path_when_available(monkeypatch):
    """Characterize bulk indicator path output formatting and missing-day placeholder behavior."""
    monkeypatch.setattr(
        y_finance,
        "_get_stock_stats_bulk",
        lambda *_args, **_kwargs: {
            "2024-01-15": "50",
            "2024-01-14": "49",
        },
    )

    result = y_finance.get_stock_stats_indicators_window("AAPL", "rsi", "2024-01-15", 2)

    assert result.startswith("## rsi values from 2024-01-13 to 2024-01-15")
    assert "2024-01-15: 50" in result
    assert "2024-01-14: 49" in result
    assert "2024-01-13: N/A: Not a trading day (weekend or holiday)" in result


def test_get_stock_stats_indicators_window_falls_back_to_single_day_calls(monkeypatch):
    """Characterize fallback loop that calls get_stockstats_indicator on bulk failures."""

    def fail_bulk(*_args, **_kwargs):
        raise RuntimeError("bulk failed")

    monkeypatch.setattr(y_finance, "_get_stock_stats_bulk", fail_bulk)
    monkeypatch.setattr(
        y_finance,
        "get_stockstats_indicator",
        lambda *_args, **_kwargs: "fallback-value",
    )

    result = y_finance.get_stock_stats_indicators_window("AAPL", "rsi", "2024-01-15", 2)

    assert "2024-01-15: fallback-value" in result
    assert "2024-01-14: fallback-value" in result
    assert "2024-01-13: fallback-value" in result


def test_get_fundamentals_returns_no_data_message_when_info_empty(monkeypatch):
    """Characterize yfinance fundamentals empty-info response."""

    class _Ticker:
        info = {}

    monkeypatch.setattr(y_finance, "_get_ticker", lambda _symbol: _Ticker())

    assert (
        y_finance.get_fundamentals("AAPL")
        == "No fundamentals data found for symbol 'AAPL'"
    )


def test_get_fundamentals_formats_selected_non_none_fields(monkeypatch):
    """Characterize yfinance fundamentals string output and field filtering."""

    class _Ticker:
        info = {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "marketCap": 100,
            "trailingPE": None,
        }

    monkeypatch.setattr(y_finance, "datetime", _FixedDateTime)
    monkeypatch.setattr(y_finance, "_get_ticker", lambda _symbol: _Ticker())

    result = y_finance.get_fundamentals("AAPL")

    assert result.startswith("# Company Fundamentals for AAPL\n")
    assert "# Data retrieved on: 2024-01-20 12:34:56" in result
    assert "Name: Apple Inc." in result
    assert "Sector: Technology" in result
    assert "Market Cap: 100" in result
    assert "PE Ratio (TTM):" not in result


def test_get_fundamentals_raises_vendor_error_on_exception(monkeypatch):
    """Characterize yfinance fundamentals exception wrapping behavior."""
    monkeypatch.setattr(
        y_finance,
        "_get_ticker",
        lambda _symbol: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(VendorError, match="Error retrieving fundamentals for AAPL"):
        y_finance.get_fundamentals("AAPL")


@pytest.mark.parametrize(
    "func_name, attr_quarterly, attr_annual, expected_prefix, empty_message",
    [
        (
            "get_balance_sheet",
            "quarterly_balance_sheet",
            "balance_sheet",
            "# Balance Sheet data for AAPL",
            "No balance sheet data found for symbol 'AAPL'",
        ),
        (
            "get_cashflow",
            "quarterly_cashflow",
            "cashflow",
            "# Cash Flow data for AAPL",
            "No cash flow data found for symbol 'AAPL'",
        ),
        (
            "get_income_statement",
            "quarterly_income_stmt",
            "income_stmt",
            "# Income Statement data for AAPL",
            "No income statement data found for symbol 'AAPL'",
        ),
    ],
)
@pytest.mark.parametrize("freq", ["quarterly", "annual"])
def test_yfinance_financial_statement_functions_characterized(
    monkeypatch,
    func_name,
    attr_quarterly,
    attr_annual,
    expected_prefix,
    empty_message,
    freq,
):
    """Characterize yfinance statement adapters for both frequency branches and empty/non-empty data."""

    class _Ticker:
        def __init__(self):
            self.quarterly_balance_sheet = pd.DataFrame(
                {"2024-03-31": [1]}, index=["Cash"]
            )
            self.balance_sheet = pd.DataFrame({"2023-12-31": [2]}, index=["Cash"])
            self.quarterly_cashflow = pd.DataFrame(
                {"2024-03-31": [3]}, index=["Operating"]
            )
            self.cashflow = pd.DataFrame({"2023-12-31": [4]}, index=["Operating"])
            self.quarterly_income_stmt = pd.DataFrame(
                {"2024-03-31": [5]}, index=["Revenue"]
            )
            self.income_stmt = pd.DataFrame({"2023-12-31": [6]}, index=["Revenue"])

    monkeypatch.setattr(y_finance, "datetime", _FixedDateTime)
    # Clear ticker cache and mock _get_ticker
    y_finance._ticker_cache.clear()
    monkeypatch.setattr(y_finance, "_get_ticker", lambda _symbol: _Ticker())

    func = getattr(y_finance, func_name)
    result = func("AAPL", freq=freq)
    assert expected_prefix in result
    assert "# Data retrieved on: 2024-01-20 12:34:56" in result
    assert "," in result

    class _EmptyTicker:
        quarterly_balance_sheet = pd.DataFrame()
        balance_sheet = pd.DataFrame()
        quarterly_cashflow = pd.DataFrame()
        cashflow = pd.DataFrame()
        quarterly_income_stmt = pd.DataFrame()
        income_stmt = pd.DataFrame()

    y_finance._ticker_cache.clear()
    monkeypatch.setattr(y_finance, "_get_ticker", lambda _symbol: _EmptyTicker())
    empty_result = func("AAPL", freq=freq)
    assert empty_result == empty_message


@pytest.mark.parametrize(
    "func_name, error_pattern",
    [
        ("get_balance_sheet", "Error retrieving balance sheet for AAPL"),
        ("get_cashflow", "Error retrieving cash flow for AAPL"),
        ("get_income_statement", "Error retrieving income statement for AAPL"),
    ],
)
def test_yfinance_statement_functions_raise_vendor_error_on_exception(
    monkeypatch,
    func_name,
    error_pattern,
):
    """Characterize exception behavior for yfinance financial statement adapters."""
    monkeypatch.setattr(
        y_finance,
        "_get_ticker",
        lambda _symbol: (_ for _ in ()).throw(RuntimeError("bad ticker")),
    )

    func = getattr(y_finance, func_name)
    with pytest.raises(VendorError, match=error_pattern):
        func("AAPL")


def test_get_insider_transactions_formats_csv_when_data_present(monkeypatch):
    """Characterize yfinance insider transactions success formatting."""

    class _Ticker:
        insider_transactions = pd.DataFrame(
            [{"insider": "Jane", "shares": 100}],
        )

    monkeypatch.setattr(y_finance, "datetime", _FixedDateTime)
    monkeypatch.setattr(y_finance, "_get_ticker", lambda _symbol: _Ticker())

    result = y_finance.get_insider_transactions("AAPL")
    assert result.startswith("# Insider Transactions data for AAPL\n")
    assert "# Data retrieved on: 2024-01-20 12:34:56" in result
    assert "insider,shares" in result


@pytest.mark.parametrize("insider_data", [None, pd.DataFrame()])
def test_get_insider_transactions_returns_no_data_message(monkeypatch, insider_data):
    """Characterize no-data response for yfinance insider transactions when data is None/empty."""

    class _Ticker:
        insider_transactions = insider_data

    monkeypatch.setattr(y_finance, "_get_ticker", lambda _symbol: _Ticker())

    assert (
        y_finance.get_insider_transactions("AAPL")
        == "No insider transactions data found for symbol 'AAPL'"
    )


def test_get_insider_transactions_raises_vendor_error_on_exception(monkeypatch):
    """Characterize exception behavior for yfinance insider transactions."""
    monkeypatch.setattr(
        y_finance,
        "_get_ticker",
        lambda _symbol: (_ for _ in ()).throw(RuntimeError("bad")),
    )

    with pytest.raises(
        VendorError, match="Error retrieving insider transactions for AAPL"
    ):
        y_finance.get_insider_transactions("AAPL")


def test_extract_article_data_nested_content_shape_is_preserved():
    """Characterize nested yfinance article extraction behavior and normalized keys."""
    article = {
        "content": {
            "title": "Title",
            "summary": "Summary",
            "provider": {"displayName": "Provider"},
            "canonicalUrl": {"url": "https://example.com"},
            "pubDate": "2024-01-10T10:00:00Z",
        },
    }

    result = yfinance_news._extract_article_data(article)

    assert result["title"] == "Title"
    assert result["summary"] == "Summary"
    assert result["publisher"] == "Provider"
    assert result["link"] == "https://example.com"
    assert result["pub_date"] is not None


def test_extract_article_data_flat_shape_is_preserved():
    """Characterize fallback extraction for flat article dictionaries."""
    article = {
        "title": "Flat",
        "summary": "Flat summary",
        "publisher": "FlatPub",
        "link": "https://flat.example.com",
    }

    result = yfinance_news._extract_article_data(article)

    assert result == {
        "title": "Flat",
        "summary": "Flat summary",
        "publisher": "FlatPub",
        "link": "https://flat.example.com",
        "pub_date": None,
    }


def test_get_news_yfinance_returns_no_news_message_when_source_empty(monkeypatch):
    """Characterize no-news response from ticker-specific yfinance news adapter."""

    class _Ticker:
        def get_news(self, count):
            return []

    monkeypatch.setattr(yfinance_news.yf, "Ticker", lambda _ticker: _Ticker())

    assert (
        yfinance_news.get_news_yfinance("AAPL", "2024-01-01", "2024-01-15")
        == "No news found for AAPL"
    )


def test_get_news_yfinance_filters_articles_by_date_and_formats_output(monkeypatch):
    """Characterize yfinance ticker news filtering, formatting, and date-range banner."""

    class _Ticker:
        def get_news(self, count):
            return [
                {
                    "content": {
                        "title": "Inside Range",
                        "summary": "Included",
                        "provider": {"displayName": "ProviderA"},
                        "canonicalUrl": {"url": "https://in.example.com"},
                        "pubDate": "2024-01-15T10:00:00Z",
                    },
                },
                {
                    "content": {
                        "title": "Outside Range",
                        "summary": "Excluded",
                        "provider": {"displayName": "ProviderB"},
                        "canonicalUrl": {"url": "https://out.example.com"},
                        "pubDate": "2023-12-01T10:00:00Z",
                    },
                },
            ]

    monkeypatch.setattr(yfinance_news.yf, "Ticker", lambda _ticker: _Ticker())

    result = yfinance_news.get_news_yfinance("AAPL", "2024-01-01", "2024-01-15")

    assert result.startswith("## AAPL News, from 2024-01-01 to 2024-01-15:\n\n")
    assert "### Inside Range (source: ProviderA)" in result
    assert "Included" in result
    assert "Link: https://in.example.com" in result
    assert "Outside Range" not in result


def test_get_news_yfinance_returns_no_news_in_range_when_all_filtered_out(monkeypatch):
    """Characterize empty-after-filtering response for ticker news queries."""

    class _Ticker:
        def get_news(self, count):
            return [
                {
                    "content": {
                        "title": "Outside",
                        "provider": {"displayName": "P"},
                        "pubDate": "2023-12-01T10:00:00Z",
                    },
                },
            ]

    monkeypatch.setattr(yfinance_news.yf, "Ticker", lambda _ticker: _Ticker())

    assert (
        yfinance_news.get_news_yfinance("AAPL", "2024-01-01", "2024-01-15")
        == "No news found for AAPL between 2024-01-01 and 2024-01-15"
    )


def test_get_news_yfinance_raises_vendor_error_on_exception(monkeypatch):
    """Characterize exception behavior for ticker-scoped yfinance news."""
    monkeypatch.setattr(
        yfinance_news.yf,
        "Ticker",
        lambda _ticker: (_ for _ in ()).throw(RuntimeError("network")),
    )

    with pytest.raises(VendorError, match="Error fetching news for AAPL"):
        yfinance_news.get_news_yfinance("AAPL", "2024-01-01", "2024-01-15")


def test_get_global_news_yfinance_returns_no_news_message_when_searches_empty(
    monkeypatch,
):
    """Characterize no-news response for global yfinance search aggregation."""

    class _Search:
        def __init__(self, *args, **kwargs):
            self.news = []

    monkeypatch.setattr(yfinance_news.yf, "Search", _Search)

    assert (
        yfinance_news.get_global_news_yfinance("2024-01-15")
        == "No global news found for 2024-01-15"
    )


def test_get_global_news_yfinance_deduplicates_titles_and_applies_limit(monkeypatch):
    """Characterize global yfinance news deduplication and result limiting behavior."""

    class _Search:
        def __init__(self, query, news_count, enable_fuzzy_query):
            self.news = [
                {
                    "content": {
                        "title": "Shared",
                        "summary": "S",
                        "provider": {"displayName": "P1"},
                        "canonicalUrl": {"url": "https://shared.example.com"},
                    },
                },
                {
                    "title": "Flat unique",
                    "publisher": "P2",
                    "link": "https://flat.example.com",
                },
            ]

    monkeypatch.setattr(yfinance_news.yf, "Search", _Search)

    result = yfinance_news.get_global_news_yfinance(
        "2024-01-15", look_back_days=7, limit=2
    )

    assert result.startswith(
        "## Global Market News, from 2024-01-08 to 2024-01-15:\n\n"
    )
    assert result.count("### Shared") == 1
    assert "### Flat unique (source: P2)" in result


def test_get_global_news_yfinance_raises_vendor_error_on_exception(monkeypatch):
    """Characterize exception behavior for global yfinance news search."""
    monkeypatch.setattr(
        yfinance_news.yf,
        "Search",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("search down")),
    )

    with pytest.raises(VendorError, match="Error fetching global news"):
        yfinance_news.get_global_news_yfinance("2024-01-15")
