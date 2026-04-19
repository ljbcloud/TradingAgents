def test_get_stock_data_is_structured_tool():
    """Verify get_stock_data is a StructuredTool"""
    from agents.utils.core_stock_tools import get_stock_data

    assert hasattr(get_stock_data, "name")
    assert hasattr(get_stock_data, "description")


def test_get_fundamentals_is_structured_tool():
    """Verify get_fundamentals is a StructuredTool"""
    from agents.utils.fundamental_data_tools import get_fundamentals

    assert hasattr(get_fundamentals, "name")
    assert hasattr(get_fundamentals, "description")


def test_get_news_is_structured_tool():
    """Verify get_news is a StructuredTool"""
    from agents.utils.news_data_tools import get_news

    assert hasattr(get_news, "name")
    assert hasattr(get_news, "description")


def test_get_indicators_is_structured_tool():
    """Verify get_indicators is a StructuredTool"""
    from agents.utils.technical_indicators_tools import get_indicators

    assert hasattr(get_indicators, "name")
    assert hasattr(get_indicators, "description")


def test_get_balance_sheet_is_structured_tool():
    """Verify get_balance_sheet is a StructuredTool"""
    from agents.utils.fundamental_data_tools import get_balance_sheet

    assert hasattr(get_balance_sheet, "name")
    assert hasattr(get_balance_sheet, "description")


def test_tools_have_correct_names():
    """Verify tool names match expected values"""
    from agents.utils.core_stock_tools import get_stock_data
    from agents.utils.fundamental_data_tools import (
        get_balance_sheet,
        get_fundamentals,
    )
    from agents.utils.news_data_tools import get_news
    from agents.utils.technical_indicators_tools import get_indicators

    assert get_stock_data.name == "get_stock_data"
    assert get_fundamentals.name == "get_fundamentals"
    assert get_news.name == "get_news"
    assert get_indicators.name == "get_indicators"
    assert get_balance_sheet.name == "get_balance_sheet"
