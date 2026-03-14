from unittest.mock import MagicMock

import pytest

from tradingagents.agents.managers.research_manager import create_research_manager


def test_create_research_manager_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    mock_memory = MagicMock()
    node = create_research_manager(mock_llm, mock_memory)
    assert callable(node)


def test_research_manager_returns_investment_debate_state(
    mock_openai_client, mock_llm_response
):
    """Returns investment_debate_state in result"""
    mock_llm_response.content = "Buy - Strong fundamentals"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_research_manager(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market analysis",
        "sentiment_report": "Sentiment analysis",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "investment_debate_state": {
            "history": "Debate content",
            "bull_history": "Bull arguments",
            "bear_history": "Bear arguments",
            "current_response": "Last response",
            "count": 2,
        },
    }

    result = node(state)

    assert "investment_debate_state" in result


def test_research_manager_returns_investment_plan(
    mock_openai_client, mock_llm_response
):
    """Returns investment_plan in result"""
    mock_llm_response.content = "Hold - Wait for clearer signals"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_research_manager(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
    }

    result = node(state)

    assert "investment_plan" in result
    assert "investment_plan" in result


def test_research_manager_judge_decision_in_debate_state(
    mock_openai_client, mock_llm_response
):
    """Sets judge_decision in investment_debate_state"""
    mock_llm_response.content = "Sell - High risk"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_research_manager(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market report",
        "sentiment_report": "Sentiment report",
        "news_report": "News report",
        "fundamentals_report": "Fundamentals report",
        "investment_debate_state": {
            "history": "Bull: Good company\nBear: Overvalued",
            "bull_history": "Bull: Good company",
            "bear_history": "Bear: Overvalued",
            "current_response": "Bear: Overvalued",
            "count": 2,
        },
    }

    result = node(state)

    assert "judge_decision" in result["investment_debate_state"]
    assert result["investment_debate_state"]["judge_decision"] == "Sell - High risk"


def test_research_manager_uses_memory(mock_openai_client, mock_llm_response):
    """Retrieves past memories and includes them in prompt"""
    mock_llm_response.content = "Buy based on past experience"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = [
        {"recommendation": "Buy - Successful in similar conditions"},
        {"recommendation": "Hold - Volatile market"},
    ]

    node = create_research_manager(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market conditions",
        "sentiment_report": "Sentiment analysis",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 2,
        },
    }

    result = node(state)

    mock_memory.get_memories.assert_called_once()


def test_research_manager_includes_debate_history(
    mock_openai_client, mock_llm_response
):
    """Includes conversation history in prompt"""
    mock_llm_response.content = "Decision based on full debate"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_research_manager(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "investment_debate_state": {
            "history": "Bull: Strong growth\nBear: High debt\nBull: Manageable debt\nBear: Interest rate risk",
            "bull_history": "Bull arguments",
            "bear_history": "Bear arguments",
            "current_response": "Bear: Interest rate risk",
            "count": 4,
        },
    }

    result = node(state)

    assert "investment_debate_state" in result


def test_research_manager_preserves_debate_count(mock_openai_client, mock_llm_response):
    """Does not increment debate count"""
    mock_llm_response.content = "Final decision"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_research_manager(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market report",
        "sentiment_report": "Sentiment report",
        "news_report": "News report",
        "fundamentals_report": "Fundamentals report",
        "investment_debate_state": {
            "history": "Debate content",
            "bull_history": "Bull content",
            "bear_history": "Bear content",
            "current_response": "Last response",
            "count": 3,
        },
    }

    result = node(state)

    assert result["investment_debate_state"]["count"] == 3


def test_research_manager_handles_empty_history(mock_openai_client, mock_llm_response):
    """Handles empty debate history gracefully"""
    mock_llm_response.content = "Initial analysis - Hold"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_research_manager(mock_openai_client, mock_memory)
    state = {
        "market_report": "Initial market data",
        "sentiment_report": "Initial sentiment",
        "news_report": "Initial news",
        "fundamentals_report": "Initial fundamentals",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
    }

    result = node(state)

    assert "investment_debate_state" in result
    assert "investment_plan" in result
