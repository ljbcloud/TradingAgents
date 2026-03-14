from unittest.mock import MagicMock

import pytest

from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.managers.risk_manager import create_risk_manager
from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
from tradingagents.agents.researchers.bull_researcher import create_bull_researcher
from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
from tradingagents.agents.risk_mgmt.conservative_debator import (
    create_conservative_debator,
)
from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator


def test_two_round_investment_debate(mock_openai_client, mock_llm_response):
    """Two-round bull-bear debate preserves history and count"""
    mock_llm_response.content = "Argument content"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    bull_node = create_bull_researcher(mock_openai_client, mock_memory)
    bear_node = create_bear_researcher(mock_openai_client, mock_memory)

    state = {
        "market_report": "Market analysis",
        "sentiment_report": "Sentiment analysis",
        "news_report": "News analysis",
        "fundamentals_report": "Fundamentals analysis",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
    }

    # Round 1: Bull speaks
    result = bull_node(state)
    assert result["investment_debate_state"]["count"] == 1
    assert "Bull Analyst:" in result["investment_debate_state"]["history"]
    state = {**state, **result}

    # Round 2: Bear responds
    result = bear_node(state)
    assert result["investment_debate_state"]["count"] == 2
    assert result["investment_debate_state"]["history"].count("Bull Analyst:") == 1
    assert result["investment_debate_state"]["history"].count("Bear Analyst:") == 1


def test_three_round_investment_debate_with_research_manager(
    mock_openai_client, mock_llm_response
):
    """Three-round debate ends with research manager decision"""
    mock_llm_response.content = "Analysis and recommendation"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    bull_node = create_bull_researcher(mock_openai_client, mock_memory)
    bear_node = create_bear_researcher(mock_openai_client, mock_memory)
    research_manager_node = create_research_manager(mock_openai_client, mock_memory)

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

    # Round 1: Bull
    state = {**state, **bull_node(state)}
    assert state["investment_debate_state"]["count"] == 1

    # Round 2: Bear
    state = {**state, **bear_node(state)}
    assert state["investment_debate_state"]["count"] == 2

    # Round 3: Bull again
    state = {**state, **bull_node(state)}
    assert state["investment_debate_state"]["count"] == 3

    # Research manager makes decision
    result = research_manager_node(state)
    assert "investment_plan" in result
    assert (
        result["investment_debate_state"]["judge_decision"]
        == "Analysis and recommendation"
    )
    assert result["investment_debate_state"]["count"] == 3  # Manager doesn't increment


def test_investment_debate_memory_persistence(mock_openai_client, mock_llm_response):
    """Debate retrieves and uses past memories"""
    mock_llm_response.content = "Informed by past decisions"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = [
        {"recommendation": "Buy - successful trend"},
        {"recommendation": "Hold - volatility too high"},
    ]

    bull_node = create_bull_researcher(mock_openai_client, mock_memory)
    bear_node = create_bear_researcher(mock_openai_client, mock_memory)

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

    # Both researchers should access memory
    result1 = bull_node(state)
    assert mock_memory.get_memories.call_count >= 1

    state = {**state, **result1}
    result2 = bear_node(state)
    assert mock_memory.get_memories.call_count >= 2


def test_investment_debate_count_tracking(mock_openai_client, mock_llm_response):
    """Debate count increments correctly with multiple rounds"""
    mock_llm_response.content = "Argument"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    bull_node = create_bull_researcher(mock_openai_client, mock_memory)
    bear_node = create_bear_researcher(mock_openai_client, mock_memory)

    state = {
        "market_report": "Data",
        "sentiment_report": "Data",
        "news_report": "Data",
        "fundamentals_report": "Data",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 5,  # Starting from 5
        },
    }

    for i in range(5, 9):
        if i % 2 == 1:
            state = {**state, **bull_node(state)}
        else:
            state = {**state, **bear_node(state)}
        assert state["investment_debate_state"]["count"] == i + 1


def test_two_round_risk_debate(mock_openai_client, mock_llm_response):
    """Two-round aggressive-conservative debate preserves history"""
    mock_llm_response.content = "Risk assessment"
    mock_openai_client.invoke.return_value = mock_llm_response

    aggressive_node = create_aggressive_debator(mock_openai_client)
    conservative_node = create_conservative_debator(mock_openai_client)

    state = {
        "company_of_interest": "AAPL",
        "trader_investment_plan": "Buy 100 shares",
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
            "latest_speaker": "",
        },
    }

    # Round 1: Aggressive
    result = aggressive_node(state)
    assert result["risk_debate_state"]["count"] == 1
    assert result["risk_debate_state"]["latest_speaker"] == "Aggressive"
    state = {**state, **result}

    # Round 2: Conservative
    result = conservative_node(state)
    assert result["risk_debate_state"]["count"] == 2
    assert result["risk_debate_state"]["latest_speaker"] == "Conservative"


def test_three_round_risk_debate_all_debators(mock_openai_client, mock_llm_response):
    """Three-round debate with all three risk debators"""
    mock_llm_response.content = "Risk analysis"
    mock_openai_client.invoke.return_value = mock_llm_response

    aggressive_node = create_aggressive_debator(mock_openai_client)
    conservative_node = create_conservative_debator(mock_openai_client)
    neutral_node = create_neutral_debator(mock_openai_client)

    state = {
        "company_of_interest": "MSFT",
        "trader_investment_plan": "Sell 50 shares",
        "market_report": "Market",
        "sentiment_report": "Sentiment",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
            "latest_speaker": "",
        },
    }

    # Round 1: Aggressive
    state = {**state, **aggressive_node(state)}
    assert state["risk_debate_state"]["count"] == 1

    # Round 2: Conservative
    state = {**state, **conservative_node(state)}
    assert state["risk_debate_state"]["count"] == 2

    # Round 3: Neutral
    state = {**state, **neutral_node(state)}
    assert state["risk_debate_state"]["count"] == 3
    assert state["risk_debate_state"]["latest_speaker"] == "Neutral"


def test_risk_debate_with_neutral_mediation(mock_openai_client, mock_llm_response):
    """Neutral debator mediates between aggressive and conservative"""
    mock_llm_response.content = "Balanced view"
    mock_openai_client.invoke.return_value = mock_llm_response

    aggressive_node = create_aggressive_debator(mock_openai_client)
    neutral_node = create_neutral_debator(mock_openai_client)
    risk_manager_node = create_risk_manager(mock_openai_client, MagicMock())

    state = {
        "company_of_interest": "GOOGL",
        "trader_investment_plan": "Hold position",
        "market_report": "Market data",
        "sentiment_report": "Sentiment data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "investment_plan": "Hold current position",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
            "latest_speaker": "",
        },
    }

    # Aggressive makes case
    state = {**state, **aggressive_node(state)}

    # Neutral mediates
    state = {**state, **neutral_node(state)}
    assert "Neutral Analyst:" in state["risk_debate_state"]["history"]

    # Risk manager decides
    result = risk_manager_node(state)
    assert "final_trade_decision" in result
    assert result["risk_debate_state"]["judge_decision"] == "Balanced view"
    assert result["risk_debate_state"]["latest_speaker"] == "Judge"


def test_risk_debate_count_tracking(mock_openai_client, mock_llm_response):
    """Risk debate count increments correctly across multiple rounds"""
    mock_llm_response.content = "Risk argument"
    mock_openai_client.invoke.return_value = mock_llm_response

    aggressive_node = create_aggressive_debator(mock_openai_client)
    conservative_node = create_conservative_debator(mock_openai_client)

    state = {
        "company_of_interest": "TSLA",
        "trader_investment_plan": "Buy",
        "market_report": "Market",
        "sentiment_report": "Sentiment",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 3,
            "latest_speaker": "",
        },
    }

    for i in range(3, 7):
        if i % 2 == 1:
            state = {**state, **aggressive_node(state)}
        else:
            state = {**state, **conservative_node(state)}
        assert state["risk_debate_state"]["count"] == i + 1


def test_investment_debate_followed_by_risk_debate(
    mock_openai_client, mock_llm_response
):
    """Investment debate flows into risk debate"""
    mock_llm_response.content = "Recommendation"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    # Investment debate participants
    bull_node = create_bull_researcher(mock_openai_client, mock_memory)
    bear_node = create_bear_researcher(mock_openai_client, mock_memory)
    research_manager_node = create_research_manager(mock_openai_client, mock_memory)

    # Risk debate participants
    aggressive_node = create_aggressive_debator(mock_openai_client)
    risk_manager_node = create_risk_manager(mock_openai_client, mock_memory)

    state = {
        "company_of_interest": "AMZN",
        "trader_investment_plan": "Buy AMZN",
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
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
            "latest_speaker": "",
        },
    }

    # Investment debate rounds
    state = {**state, **bull_node(state)}
    state = {**state, **bear_node(state)}

    # Research manager creates investment plan
    state = {**state, **research_manager_node(state)}
    assert "investment_plan" in state

    # Risk debate rounds (using the investment plan)
    state = {**state, **aggressive_node(state)}
    assert state["risk_debate_state"]["count"] == 1

    # Risk manager makes final decision
    result = risk_manager_node(state)
    assert "final_trade_decision" in result


def test_trader_plan_flows_through_both_debates(mock_openai_client, mock_llm_response):
    """Trader's plan is used in both investment and risk debates"""
    from tradingagents.agents.trader.trader import create_trader

    mock_llm_response.content = "FINAL TRANSACTION PROPOSAL: **BUY**"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    trader_node = create_trader(mock_openai_client, mock_memory)
    research_manager_node = create_research_manager(mock_openai_client, mock_memory)
    risk_manager_node = create_risk_manager(mock_openai_client, mock_memory)

    state = {
        "company_of_interest": "META",
        "market_report": "Market analysis",
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
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
            "latest_speaker": "",
        },
    }

    # Research manager creates initial investment plan
    state.update(research_manager_node(state))
    initial_plan = state["investment_plan"]

    # Trader creates refined plan
    state.update(trader_node(state))
    trader_plan = state["trader_investment_plan"]

    # Risk manager uses trader's plan
    state.update(risk_manager_node(state))

    # Verify investment plan flows through
    assert "investment_plan" in state
    assert "final_trade_decision" in state
    assert mock_openai_client.invoke.call_count >= 3


def test_full_workflow_investment_to_risk(mock_openai_client, mock_llm_response):
    """Complete workflow: investment debate → research manager → risk debate → risk manager"""
    mock_llm_response.content = "Analysis complete"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    # Create all nodes
    bull_node = create_bull_researcher(mock_openai_client, mock_memory)
    bear_node = create_bear_researcher(mock_openai_client, mock_memory)
    research_manager_node = create_research_manager(mock_openai_client, mock_memory)
    aggressive_node = create_aggressive_debator(mock_openai_client)
    conservative_node = create_conservative_debator(mock_openai_client)
    risk_manager_node = create_risk_manager(mock_openai_client, mock_memory)

    state = {
        "company_of_interest": "NVDA",
        "trader_investment_plan": "Buy NVDA",
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
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
            "latest_speaker": "",
        },
    }

    # Investment phase
    state = {**state, **bull_node(state)}
    state = {**state, **bear_node(state)}
    state = {**state, **bull_node(state)}
    assert state["investment_debate_state"]["count"] == 3

    state = {**state, **research_manager_node(state)}
    assert "investment_plan" in state

    # Risk phase
    state = {**state, **aggressive_node(state)}
    state = {**state, **conservative_node(state)}
    assert state["risk_debate_state"]["count"] == 2

    result = risk_manager_node(state)
    assert "final_trade_decision" in result

    # Verify both debate states are preserved (risk manager returns partial state)
    full_result = {**state, **result}
    assert full_result["investment_debate_state"]["count"] == 3
    assert full_result["risk_debate_state"]["count"] == 2
    assert mock_openai_client.invoke.call_count == 7


def test_state_preservation_across_debate_stages(mock_openai_client, mock_llm_response):
    """State is properly preserved when transitioning between debate stages"""
    mock_llm_response.content = "Decision"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    research_manager_node = create_research_manager(mock_openai_client, mock_memory)
    aggressive_node = create_aggressive_debator(mock_openai_client)
    risk_manager_node = create_risk_manager(mock_openai_client, mock_memory)

    initial_state = {
        "company_of_interest": "AAPL",
        "trader_investment_plan": "Buy AAPL",
        "market_report": "Original market report",
        "sentiment_report": "Original sentiment report",
        "news_report": "Original news report",
        "fundamentals_report": "Original fundamentals report",
        "investment_debate_state": {
            "history": "Debate history",
            "bull_history": "Bull history",
            "bear_history": "Bear history",
            "current_response": "Current response",
            "count": 2,
        },
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
            "latest_speaker": "",
        },
    }

    # Preserve original values
    original_investment_count = initial_state["investment_debate_state"]["count"]

    # Stage 1: Research manager
    state = initial_state.copy()
    state = {**state, **research_manager_node(state)}

    # Verify market reports are preserved
    assert state["market_report"] == initial_state["market_report"]
    assert state["sentiment_report"] == initial_state["sentiment_report"]
    assert state["news_report"] == initial_state["news_report"]
    assert state["fundamentals_report"] == initial_state["fundamentals_report"]

    # Verify investment debate state is preserved
    assert state["investment_debate_state"]["count"] == original_investment_count
    assert (
        state["investment_debate_state"]["history"]
        == initial_state["investment_debate_state"]["history"]
    )

    # Stage 2: Risk debate
    state = {**state, **aggressive_node(state)}

    # Verify investment state still preserved
    assert state["investment_debate_state"]["count"] == original_investment_count

    # Stage 3: Risk manager
    result = risk_manager_node(state)

    # Risk manager returns partial state (only risk_debate_state and final_trade_decision)
    # Merge to get complete state for verification
    full_result = {**state, **result}
    assert full_result["investment_debate_state"]["count"] == original_investment_count
    assert full_result["risk_debate_state"]["count"] == 1
    assert full_result["market_report"] == initial_state["market_report"]
