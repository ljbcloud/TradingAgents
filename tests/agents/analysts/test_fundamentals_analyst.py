from unittest.mock import MagicMock

from agents.analysts.fundamentals_analyst import (
    create_fundamentals_analyst,
)


def test_create_fundamentals_analyst_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    node = create_fundamentals_analyst(mock_llm)
    assert callable(node)


def test_fundamentals_analyst_returns_fundamentals_report(
    mock_openai_client, mock_agent_state, mock_llm_response
):
    """Returns fundamentals_report in state update"""
    mock_llm_response.tool_calls = []
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_fundamentals_analyst(mock_openai_client)
    result = node(mock_agent_state)

    assert "fundamentals_report" in result
    assert "messages" in result
