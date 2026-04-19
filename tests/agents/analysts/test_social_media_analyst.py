from unittest.mock import MagicMock

from agents.analysts.social_media_analyst import (
    create_social_media_analyst,
)


def test_create_social_media_analyst_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    node = create_social_media_analyst(mock_llm)
    assert callable(node)


def test_social_media_analyst_with_tool_calls(
    mock_openai_client, mock_agent_state, mock_llm_response
):
    """Handles LLM tool calls correctly"""
    mock_llm_response.tool_calls = [{"name": "get_news", "args": {"ticker": "AAPL"}}]
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_social_media_analyst(mock_openai_client)
    result = node(mock_agent_state)

    assert "messages" in result
    assert "sentiment_report" in result


def test_social_media_analyst_without_tool_calls(
    mock_openai_client, mock_agent_state, mock_llm_response
):
    """Extracts report content when no tool calls"""
    mock_llm_response.tool_calls = []
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_social_media_analyst(mock_openai_client)
    result = node(mock_agent_state)

    assert "sentiment_report" in result
    assert result["sentiment_report"] is not None


def test_social_media_analyst_updates_messages(
    mock_openai_client, mock_agent_state, mock_llm_response
):
    """Adds LLM response to messages"""
    mock_llm_response.tool_calls = []
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_social_media_analyst(mock_openai_client)
    initial_msg_count = len(mock_agent_state["messages"])
    result = node(mock_agent_state)

    assert len(result["messages"]) == initial_msg_count + 1


def test_social_media_analyst_empty_state(mock_openai_client, mock_llm_response):
    """Handles minimal state gracefully"""
    mock_llm_response.tool_calls = []
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_social_media_analyst(mock_openai_client)
    minimal_state = {
        "trade_date": "2024-01-01",
        "company_of_interest": "AAPL",
        "messages": [],
    }
    result = node(minimal_state)

    assert "messages" in result
    assert "sentiment_report" in result


def test_social_media_analyst_multiple_invocations(
    mock_openai_client, mock_agent_state, mock_llm_response
):
    """Handles multiple calls correctly"""
    mock_llm_response.tool_calls = []
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_social_media_analyst(mock_openai_client)
    result1 = node(mock_agent_state.copy())
    result2 = node(mock_agent_state.copy())

    assert len(result1["messages"]) == len(result2["messages"])
