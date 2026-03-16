"""Integration tests for vendor routing with configuration.

Tests verify correct vendor selection based on config settings,
including tool-level overrides and category fallback behavior.

These tests verify routing logic without making actual API calls.
"""

# ruff: noqa: S101 - assert is expected in tests

import pytest

from tradingagents.dataflows import config
from tradingagents.dataflows.interface import (
    TOOLS_CATEGORIES,
    VENDOR_METHODS,
    get_category_for_method,
    get_vendor,
)


@pytest.fixture(autouse=True)
def reset_config():
    """Reset configuration before and after each test."""
    config._config = None
    config.initialize_config()
    yield
    config._config = None
    config.initialize_config()


class TestToolSpecificVendorSelection:
    """Tests for tool-specific vendor selection."""

    def test_get_vendor_with_method_returns_vendor(self):
        """get_vendor with method should return a valid vendor."""
        vendor = get_vendor("core_stock_apis", "get_stock_data")
        assert vendor in {"yfinance", "alpha_vantage", "default"}

    def test_get_vendor_all_methods_have_valid_vendors(self):
        """All known methods should return valid vendors."""
        for category, info in TOOLS_CATEGORIES.items():
            for method in info["tools"]:
                vendor = get_vendor(category, method)
                assert vendor is not None
                assert isinstance(vendor, str)

    def test_get_vendor_unknown_method_uses_category(self):
        """get_vendor with unknown method should fall back to category."""
        vendor = get_vendor("core_stock_apis", "unknown_method")
        assert vendor in {"yfinance", "alpha_vantage", "default"}

    def test_tool_vendor_config_takes_precedence(self):
        """Tool-level vendor config should override category-level."""
        # Set tool-level config
        config.set_config({
            "tool_vendors": {
                "get_stock_data": "alpha_vantage",
            }
        })

        vendor = get_vendor("core_stock_apis", "get_stock_data")
        assert vendor == "alpha_vantage"

    def test_multiple_tool_vendor_overrides(self):
        """Multiple tool-level overrides should all work."""
        config.set_config({
            "tool_vendors": {
                "get_stock_data": "alpha_vantage",
                "get_news": "yfinance",
                "get_fundamentals": "alpha_vantage",
            }
        })

        assert get_vendor("core_stock_apis", "get_stock_data") == "alpha_vantage"
        assert get_vendor("news_data", "get_news") == "yfinance"
        assert get_vendor("fundamental_data", "get_fundamentals") == "alpha_vantage"


class TestCategoryFallbackVendor:
    """Tests for category-level fallback vendor selection."""

    def test_category_vendor_used_when_no_tool_override(self):
        """Category vendor should be used when no tool-level override exists."""
        config.set_config({
            "data_vendors": {
                "core_stock_apis": "yfinance",
            },
            "tool_vendors": {},
        })

        vendor = get_vendor("core_stock_apis", "get_stock_data")
        assert vendor == "yfinance"

    def test_category_vendor_default_is_yfinance(self):
        """Category vendor should match configured defaults for all categories."""
        config.set_config({
            "data_vendors": {
                "core_stock_apis": "yfinance",
                "technical_indicators": "yfinance",
                "fundamental_data": "yfinance",
                "news_data": "yfinance",
                "crypto_apis": "ccxt",
                "crypto_fundamentals": "coingecko,defillama",
                "crypto_sentiment": "alternative_me",
            },
        })

        expected = {
            "core_stock_apis": "yfinance",
            "technical_indicators": "yfinance",
            "fundamental_data": "yfinance",
            "news_data": "yfinance",
            "crypto_apis": "ccxt",
            "crypto_fundamentals": "coingecko,defillama",
            "crypto_sentiment": "alternative_me",
        }

        for category in TOOLS_CATEGORIES:
            vendor = get_vendor(category)
            assert vendor == expected[category]

    def test_category_vendor_can_be_changed(self):
        """Category vendor can be changed via config."""
        config.set_config({
            "data_vendors": {
                "core_stock_apis": "alpha_vantage",
                "technical_indicators": "yfinance",
                "fundamental_data": "yfinance",
                "news_data": "yfinance",
            },
        })

        vendor = get_vendor("core_stock_apis")
        assert vendor == "alpha_vantage"

    def test_get_vendor_without_method_uses_category(self):
        """get_vendor without method parameter should use category config."""
        config.set_config({
            "data_vendors": {
                "news_data": "alpha_vantage",
            },
        })
        vendor = get_vendor("news_data")
        assert vendor == "alpha_vantage"

    def test_all_categories_have_vendor_config(self):
        """All categories should have vendor configuration when set."""
        full_config = {
            "data_vendors": {
                "core_stock_apis": "yfinance",
                "technical_indicators": "yfinance",
                "fundamental_data": "yfinance",
                "news_data": "yfinance",
                "crypto_apis": "ccxt",
                "crypto_fundamentals": "coingecko,defillama",
                "crypto_sentiment": "alternative_me",
            },
        }
        config.set_config(full_config)

        current_config = config.get_config()
        data_vendors = current_config.get("data_vendors", {})

        for category in TOOLS_CATEGORIES:
            assert category in data_vendors, f"Missing vendor config for {category}"


class TestToolVendorOverridesCategory:
    """Tests for tool vendor overriding category vendor."""

    def test_tool_override_takes_precedence_over_category(self):
        """Tool-level config should override category-level even when both exist."""
        config.set_config({
            "data_vendors": {
                "core_stock_apis": "yfinance",
            },
            "tool_vendors": {
                "get_stock_data": "alpha_vantage",
            },
        })

        # get_stock_data should use tool override (alpha_vantage)
        # not category default (yfinance)
        vendor = get_vendor("core_stock_apis", "get_stock_data")
        assert vendor == "alpha_vantage"

    def test_other_tools_in_category_use_category_vendor(self):
        """Tools without override should use category vendor."""
        config.set_config({
            "data_vendors": {
                "fundamental_data": "yfinance",
            },
            "tool_vendors": {
                "get_balance_sheet": "alpha_vantage",
            },
        })

        # get_balance_sheet uses tool override
        assert get_vendor("fundamental_data", "get_balance_sheet") == "alpha_vantage"

        # Other tools in same category use category default
        assert get_vendor("fundamental_data", "get_fundamentals") == "yfinance"
        assert get_vendor("fundamental_data", "get_cashflow") == "yfinance"

    def test_mixed_vendor_selection(self):
        """Test mixed vendor selection across categories and tools."""
        config.set_config({
            "data_vendors": {
                "core_stock_apis": "yfinance",
                "technical_indicators": "alpha_vantage",
                "fundamental_data": "yfinance",
                "news_data": "alpha_vantage",
            },
            "tool_vendors": {
                "get_stock_data": "alpha_vantage",  # Override core_stock_apis
            },
        })

        # Tool override
        assert get_vendor("core_stock_apis", "get_stock_data") == "alpha_vantage"

        # Category defaults
        assert get_vendor("technical_indicators", "get_indicators") == "alpha_vantage"
        assert get_vendor("fundamental_data", "get_fundamentals") == "yfinance"
        assert get_vendor("news_data", "get_news") == "alpha_vantage"

    def test_empty_tool_vendor_uses_category(self):
        """Empty tool_vendors dict should fall back to category."""
        config.set_config({
            "data_vendors": {
                "news_data": "alpha_vantage",
            },
            "tool_vendors": {},
        })

        vendor = get_vendor("news_data", "get_news")
        assert vendor == "alpha_vantage"


class TestKnownMethodCategoryMappings:
    """Tests for known method-to-category mappings."""

    @pytest.mark.parametrize(
        ("method", "expected_category"),
        [
            ("get_stock_data", "core_stock_apis"),
            ("get_indicators", "technical_indicators"),
            ("get_fundamentals", "fundamental_data"),
            ("get_balance_sheet", "fundamental_data"),
            ("get_cashflow", "fundamental_data"),
            ("get_income_statement", "fundamental_data"),
            ("get_news", "news_data"),
            ("get_global_news", "news_data"),
            ("get_insider_transactions", "news_data"),
        ],
    )
    def test_method_category_mapping(self, method: str, expected_category: str):
        """Each method should map to its correct category."""
        category = get_category_for_method(method)
        assert category == expected_category

    def test_all_tools_in_tools_categories(self):
        """All tools in VENDOR_METHODS should be in TOOLS_CATEGORIES."""
        vendor_method_tools = set(VENDOR_METHODS.keys())
        category_tools = set()
        for info in TOOLS_CATEGORIES.values():
            category_tools.update(info["tools"])

        assert vendor_method_tools == category_tools

    def test_all_methods_have_vendor_implementations(self):
        """All methods in TOOLS_CATEGORIES should have vendor implementations."""
        for info in TOOLS_CATEGORIES.values():
            for method in info["tools"]:
                assert method in VENDOR_METHODS, (
                    f"Missing vendor implementation for {method}"
                )

    def test_all_vendor_methods_have_both_vendors(self):
        stock_categories = {
            "core_stock_apis",
            "technical_indicators",
            "fundamental_data",
            "news_data",
        }

        for category, info in TOOLS_CATEGORIES.items():
            for method in info["tools"]:
                vendors = VENDOR_METHODS[method]
                if category in stock_categories:
                    assert "alpha_vantage" in vendors, (
                        f"Missing alpha_vantage for {method}"
                    )
                    assert "yfinance" in vendors, f"Missing yfinance for {method}"
                elif category == "crypto_apis":
                    assert "ccxt" in vendors, f"Missing ccxt for {method}"
                elif category == "crypto_fundamentals":
                    assert vendors, f"Missing vendors for {method}"
                elif category == "crypto_sentiment":
                    assert "alternative_me" in vendors, (
                        f"Missing alternative_me for {method}"
                    )
                else:
                    msg = f"Unknown category '{category}' in TOOLS_CATEGORIES"
                    raise AssertionError(msg)

    def test_unknown_method_raises_value_error(self):
        """Unknown method should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            get_category_for_method("nonexistent_method")


class TestRoutingIntegration:
    """Integration tests for full routing behavior."""

    def test_vendor_methods_are_callable(self):
        """All vendor method implementations should be callable."""
        for method, vendors in VENDOR_METHODS.items():
            for vendor_name, impl in vendors.items():
                assert callable(impl), (
                    f"{method}/{vendor_name} implementation is not callable"
                )

    def test_vendor_list_contains_expected_vendors(self):
        """VENDOR_LIST should contain expected vendors."""
        from tradingagents.dataflows.interface import VENDOR_LIST

        assert "yfinance" in VENDOR_LIST
        assert "alpha_vantage" in VENDOR_LIST

    def test_config_changes_affect_vendor_selection(self):
        """Config changes should affect vendor selection."""
        # Initial state
        initial_vendor = get_vendor("core_stock_apis", "get_stock_data")

        # Change config
        config.set_config({
            "tool_vendors": {
                "get_stock_data": "alpha_vantage"
                if initial_vendor == "yfinance"
                else "yfinance",
            }
        })

        new_vendor = get_vendor("core_stock_apis", "get_stock_data")

        # Vendor should have changed
        assert new_vendor != initial_vendor

    def test_category_info_has_description(self):
        """Each category should have a description."""
        for category, info in TOOLS_CATEGORIES.items():
            assert "description" in info, f"Missing description for {category}"
            assert isinstance(info["description"], str)
