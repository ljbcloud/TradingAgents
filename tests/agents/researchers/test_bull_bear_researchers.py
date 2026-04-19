from unittest.mock import MagicMock

from agents.researchers.bear_researcher import create_bear_researcher
from agents.researchers.bull_researcher import create_bull_researcher


def test_create_bull_researcher_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    mock_memory = MagicMock()
    node = create_bull_researcher(mock_llm, mock_memory)
    assert callable(node)


def test_create_bear_researcher_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    mock_memory = MagicMock()
    node = create_bear_researcher(mock_llm, mock_memory)
    assert callable(node)


def test_bull_researcher_updates_investment_debate_state(
    mock_openai_client, mock_llm_response
):
    """Updates investment_debate_state with new argument"""
    mock_llm_response.content = "Strong growth potential"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_bull_researcher(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market is up",
        "sentiment_report": "Positive sentiment",
        "news_report": "Good news",
        "fundamentals_report": "Strong fundamentals",
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
    assert "Bull Analyst:" in result["investment_debate_state"]["history"]
    assert "Bull Analyst:" in result["investment_debate_state"]["bull_history"]
    assert result["investment_debate_state"]["count"] == 1


def test_bear_researcher_updates_investment_debate_state(
    mock_openai_client, mock_llm_response
):
    """Updates investment_debate_state with new argument"""
    mock_llm_response.content = "Significant risks ahead"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_bear_researcher(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market is up",
        "sentiment_report": "Positive sentiment",
        "news_report": "Good news",
        "fundamentals_report": "Strong fundamentals",
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
    assert "Bear Analyst:" in result["investment_debate_state"]["history"]
    assert "Bear Analyst:" in result["investment_debate_state"]["bear_history"]
    assert result["investment_debate_state"]["count"] == 1


def test_bull_researcher_uses_memory(mock_openai_client, mock_llm_response):
    """Retrieves past memories and includes them in prompt"""
    mock_llm_response.content = "Based on past experience"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = [
        {"recommendation": "Buy - previous success"},
        {"recommendation": "Hold - moderate growth"},
    ]

    node = create_bull_researcher(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market analysis",
        "sentiment_report": "Sentiment analysis",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
    }

    result = node(state)

    mock_memory.get_memories.assert_called_once()
    assert "investment_debate_state" in result


def test_bear_researcher_uses_memory(mock_openai_client, mock_llm_response):
    """Retrieves past memories and includes them in prompt"""
    mock_llm_response.content = "Based on past risks"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = [
        {"recommendation": "Sell - previous decline"},
        {"recommendation": "Avoid - high risk"},
    ]

    node = create_bear_researcher(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market analysis",
        "sentiment_report": "Sentiment analysis",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
    }

    result = node(state)

    mock_memory.get_memories.assert_called_once()
    assert "investment_debate_state" in result


def test_bull_researcher_includes_debate_history(mock_openai_client, mock_llm_response):
    """Includes conversation history in prompt"""
    mock_llm_response.content = "Counter to bear argument"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_bull_researcher(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "investment_debate_state": {
            "history": "Bear Analyst: This stock is overvalued",
            "bull_history": "",
            "bear_history": "Bear Analyst: This stock is overvalued",
            "current_response": "Bear Analyst: This stock is overvalued",
            "count": 1,
        },
    }

    result = node(state)

    assert "investment_debate_state" in result
    assert result["investment_debate_state"]["count"] == 2


def test_bear_researcher_includes_debate_history(mock_openai_client, mock_llm_response):
    """Includes conversation history in prompt"""
    mock_llm_response.content = "Counter to bull argument"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_bear_researcher(mock_openai_client, mock_memory)
    state = {
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "investment_debate_state": {
            "history": "Bull Analyst: Strong growth prospects",
            "bull_history": "Bull Analyst: Strong growth prospects",
            "bear_history": "",
            "current_response": "Bull Analyst: Strong growth prospects",
            "count": 1,
        },
    }

    result = node(state)

    assert "investment_debate_state" in result
    assert result["investment_debate_state"]["count"] == 2
