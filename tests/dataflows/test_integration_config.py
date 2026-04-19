"""Integration tests for configuration-driven behavior in dataflows.

These tests verify that configuration changes correctly affect dataflow behavior,
ensuring the integration between DEFAULT_CONFIG and the dataflows module works as expected.
"""

from __future__ import annotations

import pytest

import default_config
from dataflows import config as dataflows_config
from dataflows import interface


class TestDefaultConfigLoads:
    """Tests verifying DEFAULT_CONFIG loads correctly."""

    def test_default_config_is_dict(self):
        """DEFAULT_CONFIG should be a dictionary."""
        assert isinstance(default_config.DEFAULT_CONFIG, dict)

    def test_default_config_not_empty(self):
        """DEFAULT_CONFIG should not be empty."""
        assert len(default_config.DEFAULT_CONFIG) > 0


class TestConfigRequiredKeys:
    """Tests verifying required configuration keys exist in the config."""

    def test_config_has_deep_think_llm(self):
        """Config should have deep_think_llm setting."""
        assert "deep_think_llm" in default_config.DEFAULT_CONFIG

    def test_config_has_quick_think_llm(self):
        """Config should have quick_think_llm setting."""
        assert "quick_think_llm" in default_config.DEFAULT_CONFIG

    def test_config_has_data_vendor(self):
        """Config should have data_vendor setting."""
        assert "data_vendor" in default_config.DEFAULT_CONFIG


class TestToolsCategoriesDefinition:
    """Tests verifying TOOLS_CATEGORIES is properly defined."""

    def test_tools_categories_exists(self):
        """TOOLS_CATEGORIES should be defined in interface module."""
        assert hasattr(interface, "TOOLS_CATEGORIES")

    def test_tools_categories_is_dict(self):
        """TOOLS_CATEGORIES should be a dictionary."""
        assert isinstance(interface.TOOLS_CATEGORIES, dict)

    def test_tools_categories_not_empty(self):
        """TOOLS_CATEGORIES should not be empty."""
        assert len(interface.TOOLS_CATEGORIES) > 0

    @pytest.mark.parametrize(
        ("category", "expected_tools"),
        [
            ("core_stock_apis", ["get_stock_data"]),
            ("technical_indicators", ["get_indicators"]),
            (
                "fundamental_data",
                [
                    "get_fundamentals",
                    "get_balance_sheet",
                    "get_cashflow",
                    "get_income_statement",
                ],
            ),
            ("news_data", ["get_news", "get_global_news", "get_insider_transactions"]),
        ],
    )
    def test_category_contains_expected_tools(
        self, category: str, expected_tools: list[str]
    ):
        """Each category should contain its expected tools."""
        assert category in interface.TOOLS_CATEGORIES
        category_info = interface.TOOLS_CATEGORIES[category]
        assert "tools" in category_info
        for tool in expected_tools:
            assert tool in category_info["tools"], (
                f"Tool '{tool}' not in category '{category}'"
            )

    def test_each_category_has_description(self):
        """Each category should have a description."""
        for category, info in interface.TOOLS_CATEGORIES.items():
            assert "description" in info, f"Category '{category}' missing description"


class TestVendorMethodsMapping:
    """Tests verifying VENDOR_METHODS mapping is properly defined."""

    EXPECTED_METHODS = [
        "get_stock_data",
        "get_indicators",
        "get_fundamentals",
        "get_balance_sheet",
        "get_cashflow",
        "get_income_statement",
        "get_news",
        "get_global_news",
        "get_insider_transactions",
    ]

    def test_vendor_methods_exists(self):
        """VENDOR_METHODS should be defined in interface module."""
        assert hasattr(interface, "VENDOR_METHODS")

    def test_vendor_methods_is_dict(self):
        """VENDOR_METHODS should be a dictionary."""
        assert isinstance(interface.VENDOR_METHODS, dict)

    def test_vendor_methods_not_empty(self):
        """VENDOR_METHODS should not be empty."""
        assert len(interface.VENDOR_METHODS) > 0

    @pytest.mark.parametrize("method", EXPECTED_METHODS)
    def test_method_exists_in_vendor_methods(self, method: str):
        """Each expected method should exist in VENDOR_METHODS."""
        assert method in interface.VENDOR_METHODS, (
            f"Method '{method}' not in VENDOR_METHODS"
        )

    @pytest.mark.parametrize("method", EXPECTED_METHODS)
    def test_method_has_vendor_implementations(self, method: str):
        """Each method should have at least one vendor implementation."""
        vendors = interface.VENDOR_METHODS[method]
        assert isinstance(vendors, dict), f"Method '{method}' vendors is not a dict"
        assert len(vendors) > 0, f"Method '{method}' has no vendor implementations"

    @pytest.mark.parametrize("method", EXPECTED_METHODS)
    def test_method_vendor_implementations_are_callable(self, method: str):
        """Each vendor implementation should be callable."""
        vendors = interface.VENDOR_METHODS[method]
        for vendor_name, impl in vendors.items():
            # Handle both single callable and list of callables
            if isinstance(impl, list):
                for func in impl:
                    assert callable(func), (
                        f"Method '{method}' vendor '{vendor_name}' list item is not callable"
                    )
            else:
                assert callable(impl), (
                    f"Method '{method}' vendor '{vendor_name}' implementation is not callable"
                )


class TestDataflowsConfigModule:
    """Tests verifying the dataflows config module works correctly."""

    def test_initialize_config_creates_config(self):
        """initialize_config should create a configuration."""
        dataflows_config._config = None
        dataflows_config.initialize_config()

        config = dataflows_config.get_config()
        assert config is not None
        assert isinstance(config, dict)

    def test_get_config_returns_copy(self):
        """get_config should return a copy, not the original."""
        dataflows_config._config = None
        dataflows_config.initialize_config()

        config1 = dataflows_config.get_config()
        config2 = dataflows_config.get_config()

        assert config1 == config2
        assert config1 is not config2

    def test_set_config_updates_values(self):
        """set_config should update configuration values."""
        dataflows_config._config = None
        dataflows_config.initialize_config()

        dataflows_config.set_config({"custom_key": "custom_value"})

        config = dataflows_config.get_config()
        assert config["custom_key"] == "custom_value"

    def test_set_config_preserves_existing_values(self):
        """set_config should preserve values not being updated."""
        dataflows_config._config = None
        dataflows_config.initialize_config()

        original_config = dataflows_config.get_config()
        original_keys = set(original_config.keys())

        dataflows_config.set_config({"new_key": "new_value"})

        updated_config = dataflows_config.get_config()
        for key in original_keys:
            assert key in updated_config


class TestVendorListDefinition:
    """Tests verifying VENDOR_LIST is properly defined."""

    def test_vendor_list_exists(self):
        """VENDOR_LIST should be defined in interface module."""
        assert hasattr(interface, "VENDOR_LIST")

    def test_vendor_list_is_list(self):
        """VENDOR_LIST should be a list."""
        assert isinstance(interface.VENDOR_LIST, list)

    def test_vendor_list_contains_expected_vendors(self):
        """VENDOR_LIST should contain expected vendor names."""
        expected_vendors = ["yfinance", "alpha_vantage"]
        for vendor in expected_vendors:
            assert vendor in interface.VENDOR_LIST, (
                f"Vendor '{vendor}' not in VENDOR_LIST"
            )


class TestConfigBehaviorIntegration:
    """Integration tests verifying config changes affect behavior."""

    def test_get_vendor_uses_data_vendors_config(self, monkeypatch):
        """get_vendor should use data_vendors configuration."""
        monkeypatch.setattr(
            interface,
            "get_config",
            lambda: {
                "tool_vendors": {},
                "data_vendors": {"core_stock_apis": "alpha_vantage"},
            },
        )

        vendor = interface.get_vendor("core_stock_apis")
        assert vendor == "alpha_vantage"

    def test_get_vendor_tool_level_overrides_category(self, monkeypatch):
        """Tool-level vendor config should override category-level config."""
        monkeypatch.setattr(
            interface,
            "get_config",
            lambda: {
                "tool_vendors": {"get_stock_data": "yfinance"},
                "data_vendors": {"core_stock_apis": "alpha_vantage"},
            },
        )

        vendor = interface.get_vendor("core_stock_apis", "get_stock_data")
        assert vendor == "yfinance"

    def test_get_vendor_defaults_to_default_string_when_missing(self, monkeypatch):
        """get_vendor should return 'default' when category has no configured vendor."""
        monkeypatch.setattr(
            interface, "get_config", lambda: {"tool_vendors": {}, "data_vendors": {}}
        )

        vendor = interface.get_vendor("news_data", "get_news")
        assert vendor == "default"

    def test_get_category_for_method_returns_correct_category(self):
        """get_category_for_method should return correct category for each method."""
        expected_mappings = {
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

        for method, expected_category in expected_mappings.items():
            category = interface.get_category_for_method(method)
            assert category == expected_category

    def test_get_category_for_method_raises_for_unknown_method(self):
        """get_category_for_method should raise ValueError for unknown methods."""
        with pytest.raises(ValueError, match="not found in any category"):
            interface.get_category_for_method("unknown_method")


class TestMethodCategoryConsistency:
    """Tests verifying consistency between TOOLS_CATEGORIES and VENDOR_METHODS."""

    def test_all_vendor_methods_have_categories(self):
        """All methods in VENDOR_METHODS should have a corresponding category."""
        for method in interface.VENDOR_METHODS:
            found = False
            for category_info in interface.TOOLS_CATEGORIES.values():
                if method in category_info["tools"]:
                    found = True
                    break
            assert found, f"Method '{method}' not found in any TOOLS_CATEGORIES"

    def test_all_category_tools_have_vendor_methods(self):
        """All tools in TOOLS_CATEGORIES should have VENDOR_METHODS entries."""
        for category, info in interface.TOOLS_CATEGORIES.items():
            for tool in info["tools"]:
                assert tool in interface.VENDOR_METHODS, (
                    f"Tool '{tool}' in category '{category}' not found in VENDOR_METHODS"
                )
