"""Unit tests for dataflows interface routing."""

import pytest

from dataflows import interface


class TestCategoryMapping:
    """Tests for method-to-category mapping."""

    def test_get_category_for_stock_data(self):
        """get_category_for_method should return core_stock_apis for stock data."""
        assert interface.get_category_for_method("get_stock_data") == "core_stock_apis"

    def test_get_category_for_indicators(self):
        """get_category_for_method should return technical_indicators for indicators."""
        assert (
            interface.get_category_for_method("get_indicators")
            == "technical_indicators"
        )

    def test_get_category_for_fundamentals(self):
        """get_category_for_method should return fundamental_data for fundamentals."""
        assert (
            interface.get_category_for_method("get_fundamentals") == "fundamental_data"
        )

    def test_get_category_for_news(self):
        """get_category_for_method should return news_data for news."""
        assert interface.get_category_for_method("get_news") == "news_data"

    def test_get_category_unknown_raises(self):
        """get_category_for_method should raise for unknown method."""
        with pytest.raises(ValueError, match="not found"):
            interface.get_category_for_method("unknown_method")


class TestVendorMethods:
    """Tests for VENDOR_METHODS structure."""

    def test_vendor_methods_contains_stock_data(self):
        """VENDOR_METHODS should contain get_stock_data."""
        assert "get_stock_data" in interface.VENDOR_METHODS

    def test_vendor_methods_contains_indicators(self):
        """VENDOR_METHODS should contain get_indicators."""
        assert "get_indicators" in interface.VENDOR_METHODS

    def test_vendor_methods_contains_fundamentals(self):
        """VENDOR_METHODS should contain get_fundamentals."""
        assert "get_fundamentals" in interface.VENDOR_METHODS

    def test_vendor_methods_is_dict(self):
        """VENDOR_METHODS should be a dictionary."""
        assert isinstance(interface.VENDOR_METHODS, dict)

    def test_vendor_methods_has_alpha_vantage_and_yfinance(self):
        """VENDOR_METHODS should have both vendors for stock data."""
        stock_methods = interface.VENDOR_METHODS["get_stock_data"]
        assert "alpha_vantage" in stock_methods
        assert "yfinance" in stock_methods


class TestGetVendor:
    """Tests for vendor resolution."""

    def test_get_vendor_returns_configured_default(self):
        """get_vendor should return vendor from config."""
        vendor = interface.get_vendor("core_stock_apis", "get_stock_data")
        assert vendor in {"yfinance", "alpha_vantage", "default"}

    def test_get_vendor_uses_category_fallback(self):
        """get_vendor should use category when method is None."""
        vendor = interface.get_vendor("core_stock_apis")
        assert vendor is not None


class TestToolsCategories:
    """Tests for TOOLS_CATEGORIES structure."""

    def test_tools_categories_is_dict(self):
        """TOOLS_CATEGORIES should be a dictionary."""
        assert isinstance(interface.TOOLS_CATEGORIES, dict)

    def test_tools_categories_has_core_stock(self):
        """TOOLS_CATEGORIES should have core_stock_apis."""
        assert "core_stock_apis" in interface.TOOLS_CATEGORIES

    def test_tools_categories_has_technical_indicators(self):
        """TOOLS_CATEGORIES should have technical_indicators."""
        assert "technical_indicators" in interface.TOOLS_CATEGORIES

    def test_each_category_has_tools(self):
        """Each category should have a tools list."""
        for info in interface.TOOLS_CATEGORIES.values():
            assert "tools" in info
            assert isinstance(info["tools"], list)
