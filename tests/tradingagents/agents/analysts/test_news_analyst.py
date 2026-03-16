# ruff: noqa: S101 - assert is expected in tests

from unittest.mock import MagicMock

from tradingagents.agents.analysts.news_analyst import create_news_analyst


def test_create_news_analyst_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    node = create_news_analyst(mock_llm)
    assert callable(node)


def test_news_analyst_returns_news_report(
    mock_openai_client, mock_agent_state, mock_llm_response
):
    """Returns news_report in state update"""
    mock_llm_response.tool_calls = []
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_news_analyst(mock_openai_client)
    result = node(mock_agent_state)

    assert "news_report" in result
    assert "messages" in result


def test_news_analyst_empty_state(mock_openai_client, mock_llm_response):
    """Handles minimal state gracefully"""
    mock_llm_response.tool_calls = []
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_news_analyst(mock_openai_client)
    minimal_state = {
        "trade_date": "2024-01-01",
        "company_of_interest": "AAPL",
        "messages": [],
    }

    result = node(minimal_state)

    assert "messages" in result
    assert "news_report" in result
