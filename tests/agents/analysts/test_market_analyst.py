from unittest.mock import MagicMock

import pytest

from agents.analysts.market_analyst import create_market_analyst


@pytest.mark.unit
def test_market_analyst_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    node = create_market_analyst(mock_llm)
    assert callable(node)


@pytest.mark.unit
def test_market_analyst_with_empty_state():
    """Handles empty state gracefully"""
    mock_llm = MagicMock()
    node = create_market_analyst(mock_llm)
    minimal_state = {
        "trade_date": "2024-01-01",
        "company_of_interest": "AAPL",
        "messages": [],
    }

    mock_llm.invoke.return_value = MagicMock(content="Market analysis", tool_calls=[])

    result = node(minimal_state)
    assert "messages" in result
    assert "market_report" in result
