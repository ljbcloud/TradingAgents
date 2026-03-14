from unittest.mock import MagicMock

import pytest

from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
from tradingagents.agents.risk_mgmt.conservative_debator import (
    create_conservative_debator,
)
from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator


def test_create_aggressive_debator_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    node = create_aggressive_debator(mock_llm)
    assert callable(node)


def test_create_conservative_debator_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    node = create_conservative_debator(mock_llm)
    assert callable(node)


def test_create_neutral_debator_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    node = create_neutral_debator(mock_llm)
    assert callable(node)


def test_aggressive_debator_updates_risk_debate_state(
    mock_openai_client, mock_llm_response
):
    """Updates risk_debate_state with new argument"""
    mock_llm_response.content = "Take the risk, potential upside is huge"
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_aggressive_debator(mock_openai_client)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market analysis",
        "sentiment_report": "Sentiment analysis",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "trader_investment_plan": "Buy - Good opportunity",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "latest_speaker": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
    }

    result = node(state)

    assert "risk_debate_state" in result
    assert "Aggressive Analyst:" in result["risk_debate_state"]["history"]
    assert "Aggressive Analyst:" in result["risk_debate_state"]["aggressive_history"]
    assert result["risk_debate_state"]["latest_speaker"] == "Aggressive"
    assert result["risk_debate_state"]["count"] == 1


def test_conservative_debator_updates_risk_debate_state(
    mock_openai_client, mock_llm_response
):
    """Updates risk_debate_state with new argument"""
    mock_llm_response.content = "This is too risky, we should hold"
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_conservative_debator(mock_openai_client)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market analysis",
        "sentiment_report": "Sentiment analysis",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "trader_investment_plan": "Buy recommendation",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "latest_speaker": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
    }

    result = node(state)

    assert "risk_debate_state" in result
    assert "Conservative Analyst:" in result["risk_debate_state"]["history"]
    assert (
        "Conservative Analyst:" in result["risk_debate_state"]["conservative_history"]
    )
    assert result["risk_debate_state"]["latest_speaker"] == "Conservative"
    assert result["risk_debate_state"]["count"] == 1


def test_neutral_debator_updates_risk_debate_state(
    mock_openai_client, mock_llm_response
):
    """Updates risk_debate_state with new argument"""
    mock_llm_response.content = "We need a balanced approach"
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_neutral_debator(mock_openai_client)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market analysis",
        "sentiment_report": "Sentiment analysis",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "trader_investment_plan": "Hold recommendation",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "latest_speaker": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
    }

    result = node(state)

    assert "risk_debate_state" in result
    assert "Neutral Analyst:" in result["risk_debate_state"]["history"]
    assert "Neutral Analyst:" in result["risk_debate_state"]["neutral_history"]
    assert result["risk_debate_state"]["latest_speaker"] == "Neutral"
    assert result["risk_debate_state"]["count"] == 1


def test_aggressive_debator_includes_other_arguments(
    mock_openai_client, mock_llm_response
):
    """Includes conservative and neutral arguments in prompt"""
    mock_llm_response.content = "You're being too cautious"
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_aggressive_debator(mock_openai_client)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "trader_investment_plan": "Trader decision",
        "risk_debate_state": {
            "history": "Conservative: Too risky\nNeutral: Wait and see",
            "aggressive_history": "",
            "conservative_history": "Conservative: Too risky",
            "neutral_history": "Neutral: Wait and see",
            "latest_speaker": "Neutral",
            "current_aggressive_response": "",
            "current_conservative_response": "Conservative: Too risky",
            "current_neutral_response": "Neutral: Wait and see",
            "count": 2,
        },
    }

    result = node(state)

    assert "risk_debate_state" in result
    assert result["risk_debate_state"]["count"] == 3


def test_conservative_debator_includes_other_arguments(
    mock_openai_client, mock_llm_response
):
    """Includes aggressive and neutral arguments in prompt"""
    mock_llm_response.content = "You're being too reckless"
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_conservative_debator(mock_openai_client)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "trader_investment_plan": "Trader decision",
        "risk_debate_state": {
            "history": "Aggressive: Take the risk\nNeutral: Be balanced",
            "aggressive_history": "Aggressive: Take the risk",
            "conservative_history": "",
            "neutral_history": "Neutral: Be balanced",
            "latest_speaker": "Neutral",
            "current_aggressive_response": "Aggressive: Take the risk",
            "current_conservative_response": "",
            "current_neutral_response": "Neutral: Be balanced",
            "count": 2,
        },
    }

    result = node(state)

    assert "risk_debate_state" in result
    assert result["risk_debate_state"]["count"] == 3


def test_neutral_debator_includes_other_arguments(
    mock_openai_client, mock_llm_response
):
    """Includes aggressive and conservative arguments in prompt"""
    mock_llm_response.content = "Both sides have valid points"
    mock_openai_client.invoke.return_value = mock_llm_response

    node = create_neutral_debator(mock_openai_client)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "trader_investment_plan": "Trader decision",
        "risk_debate_state": {
            "history": "Aggressive: Go for it\nConservative: Too dangerous",
            "aggressive_history": "Aggressive: Go for it",
            "conservative_history": "Conservative: Too dangerous",
            "neutral_history": "",
            "latest_speaker": "Conservative",
            "current_aggressive_response": "Aggressive: Go for it",
            "current_conservative_response": "Conservative: Too dangerous",
            "current_neutral_response": "",
            "count": 2,
        },
    }

    result = node(state)

    assert "risk_debate_state" in result
    assert result["risk_debate_state"]["count"] == 3


def test_all_debators_use_trader_decision(mock_openai_client, mock_llm_response):
    """All debators incorporate trader's decision"""
    mock_llm_response.content = "Response to trader"
    mock_openai_client.invoke.return_value = mock_llm_response

    trader_decision = "FINAL TRANSACTION PROPOSAL: **BUY**"

    for debator_func, name in [
        (create_aggressive_debator, "Aggressive"),
        (create_conservative_debator, "Conservative"),
        (create_neutral_debator, "Neutral"),
    ]:
        node = debator_func(mock_openai_client)
        state = {
            "company_of_interest": "AAPL",
            "market_report": "Market report",
            "sentiment_report": "Sentiment report",
            "news_report": "News report",
            "fundamentals_report": "Fundamentals report",
            "trader_investment_plan": trader_decision,
            "risk_debate_state": {
                "history": "",
                "aggressive_history": "",
                "conservative_history": "",
                "neutral_history": "",
                "latest_speaker": "",
                "current_aggressive_response": "",
                "current_conservative_response": "",
                "current_neutral_response": "",
                "count": 0,
            },
        }

        result = node(state)

        assert "risk_debate_state" in result


def test_all_debators_preserve_other_histories(mock_openai_client, mock_llm_response):
    """Each debator only updates their own history"""
    mock_llm_response.content = "New argument"
    mock_openai_client.invoke.return_value = mock_llm_response

    initial_history = {
        "aggressive_history": "Aggressive: Previous",
        "conservative_history": "Conservative: Previous",
        "neutral_history": "Neutral: Previous",
    }

    for debator_func, history_key in [
        (create_aggressive_debator, "aggressive_history"),
        (create_conservative_debator, "conservative_history"),
        (create_neutral_debator, "neutral_history"),
    ]:
        node = debator_func(mock_openai_client)
        state = {
            "company_of_interest": "AAPL",
            "market_report": "Report",
            "sentiment_report": "Report",
            "news_report": "Report",
            "fundamentals_report": "Report",
            "trader_investment_plan": "Trader decision",
            "risk_debate_state": {
                "history": "Previous history",
                **initial_history,
                "latest_speaker": "",
                "current_aggressive_response": "",
                "current_conservative_response": "",
                "current_neutral_response": "",
                "count": 0,
            },
        }

        result = node(state)

        assert initial_history[history_key] in result["risk_debate_state"][history_key]
