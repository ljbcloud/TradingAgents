from unittest.mock import MagicMock

import pytest

from tradingagents.agents.trader.trader import create_trader


def test_create_trader_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    mock_memory = MagicMock()
    node = create_trader(mock_llm, mock_memory)
    assert callable(node)


def test_trader_returns_messages(mock_openai_client, mock_llm_response):
    """Returns messages in result"""
    mock_llm_response.content = "FINAL TRANSACTION PROPOSAL: **BUY**"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_trader(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "investment_plan": "Buy - Strong fundamentals",
        "market_report": "Market is bullish",
        "sentiment_report": "Positive sentiment",
        "news_report": "Good earnings",
        "fundamentals_report": "Strong financials",
    }

    result = node(state)

    assert "messages" in result
    assert len(result["messages"]) == 1


def test_trader_returns_trader_investment_plan(mock_openai_client, mock_llm_response):
    """Returns trader_investment_plan in result"""
    mock_llm_response.content = "FINAL TRANSACTION PROPOSAL: **HOLD**"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_trader(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "GOOGL",
        "investment_plan": "Hold - Wait for signals",
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
    }

    result = node(state)

    assert "trader_investment_plan" in result
    assert result["trader_investment_plan"] == "FINAL TRANSACTION PROPOSAL: **HOLD**"


def test_trader_returns_sender(mock_openai_client, mock_llm_response):
    """Returns sender as 'Trader'"""
    mock_llm_response.content = "FINAL TRANSACTION PROPOSAL: **SELL**"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_trader(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "TSLA",
        "investment_plan": "Sell plan",
        "market_report": "Market report",
        "sentiment_report": "Sentiment report",
        "news_report": "News report",
        "fundamentals_report": "Fundamentals report",
    }

    result = node(state)

    assert "sender" in result
    assert result["sender"] == "Trader"


def test_trader_uses_memory(mock_openai_client, mock_llm_response):
    """Retrieves past memories for similar situations"""
    mock_llm_response.content = "FINAL TRANSACTION PROPOSAL: **BUY**"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = [
        {"recommendation": "Buy in similar market conditions"},
        {"recommendation": "Hold when sentiment is mixed"},
    ]

    node = create_trader(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "investment_plan": "Buy recommendation",
        "market_report": "Market conditions",
        "sentiment_report": "Sentiment conditions",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
    }

    result = node(state)

    mock_memory.get_memories.assert_called_once()
    assert "trader_investment_plan" in result


def test_trader_handles_empty_memories(mock_openai_client, mock_llm_response):
    """Handles case when no past memories are found"""
    mock_llm_response.content = "FINAL TRANSACTION PROPOSAL: **HOLD**"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_trader(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "investment_plan": "Hold recommendation",
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
    }

    result = node(state)

    mock_memory.get_memories.assert_called_once()
    assert "trader_investment_plan" in result


def test_trader_includes_all_reports(mock_openai_client, mock_llm_response):
    """Uses all available reports in situation context"""
    mock_llm_response.content = "FINAL TRANSACTION PROPOSAL: **BUY**"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_trader(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "investment_plan": "Buy based on comprehensive analysis",
        "market_report": "Technical analysis: Strong uptrend",
        "sentiment_report": "Social media: Very positive",
        "news_report": "Recent: Beat earnings estimates",
        "fundamentals_report": "Financials: Record revenue",
    }

    result = node(state)

    mock_memory.get_memories.assert_called_once()
    assert "trader_investment_plan" in result
