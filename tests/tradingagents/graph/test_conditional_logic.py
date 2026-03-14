from unittest.mock import MagicMock

import pytest

from tradingagents.graph.conditional_logic import ConditionalLogic


def test_conditional_logic_initialization_defaults():
    """Initializes with default max_debate_rounds and max_risk_discuss_rounds"""
    logic = ConditionalLogic()
    assert logic.max_debate_rounds == 1
    assert logic.max_risk_discuss_rounds == 1


def test_conditional_logic_initialization_custom():
    """Initializes with custom max rounds"""
    logic = ConditionalLogic(max_debate_rounds=3, max_risk_discuss_rounds=5)
    assert logic.max_debate_rounds == 3
    assert logic.max_risk_discuss_rounds == 5


def test_should_continue_market_with_tool_calls():
    """Routes to tools_market when last message has tool_calls"""
    logic = ConditionalLogic()

    mock_message = MagicMock()
    mock_message.tool_calls = [{"name": "get_stock_data"}]

    state = {"messages": [{"content": "Need stock data"}, mock_message]}

    result = logic.should_continue_market(state)
    assert result == "tools_market"


def test_should_continue_market_without_tool_calls():
    """Routes to message clear when last message has no tool_calls"""
    logic = ConditionalLogic()

    mock_message = MagicMock()
    mock_message.tool_calls = []

    state = {"messages": [{"content": "Analysis complete"}, mock_message]}

    result = logic.should_continue_market(state)
    assert result == "Msg Clear Market"


def test_should_continue_social_with_tool_calls():
    """Routes to tools_social when last message has tool_calls"""
    logic = ConditionalLogic()

    mock_message = MagicMock()
    mock_message.tool_calls = [{"name": "get_sentiment"}]

    state = {"messages": [{"content": "Need sentiment data"}, mock_message]}

    result = logic.should_continue_social(state)
    assert result == "tools_social"


def test_should_continue_news_with_tool_calls():
    """Routes to tools_news when last message has tool_calls"""
    logic = ConditionalLogic()

    mock_message = MagicMock()
    mock_message.tool_calls = [{"name": "get_news"}]

    state = {"messages": [MagicMock(content="Need news data"), mock_message]}

    result = logic.should_continue_news(state)
    assert result == "tools_news"


def test_should_continue_fundamentals_with_tool_calls():
    """Routes to tools_fundamentals when last message has tool_calls"""
    logic = ConditionalLogic()

    mock_message = MagicMock()
    mock_message.tool_calls = [{"name": "get_fundamentals"}]

    state = {"messages": [MagicMock(content="Need fundamentals data"), mock_message]}

    result = logic.should_continue_fundamentals(state)
    assert result == "tools_fundamentals"


def test_debate_routing_from_bull_to_bear():
    """Routes to Bear Researcher when current speaker is Bull"""
    logic = ConditionalLogic()

    state = {
        "investment_debate_state": {
            "count": 1,
            "current_response": "Bull Analyst: Strong growth potential",
        }
    }

    result = logic.should_continue_debate(state)
    assert result == "Bear Researcher"


def test_debate_routing_from_bear_to_bull():
    """Routes to Bull Researcher when current speaker is Bear"""
    logic = ConditionalLogic()

    state = {
        "investment_debate_state": {
            "count": 1,
            "current_response": "Bear Analyst: Significant risks ahead",
        }
    }

    result = logic.should_continue_debate(state)
    assert result == "Bull Researcher"


def test_debate_limit_enforcement_max_reached():
    """Routes to Research Manager when max debate rounds reached"""
    logic = ConditionalLogic(max_debate_rounds=2)  # 2 rounds = 4 exchanges

    state = {
        "investment_debate_state": {
            "count": 4,
            "current_response": "Bull Analyst: Final argument",
        }
    }

    result = logic.should_continue_debate(state)
    assert result == "Research Manager"


def test_debate_limit_enforcement_below_max():
    """Continues debate when count is below max limit"""
    logic = ConditionalLogic(max_debate_rounds=2)

    state = {
        "investment_debate_state": {
            "count": 3,
            "current_response": "Bull Analyst: Continuing debate",
        }
    }

    result = logic.should_continue_debate(state)
    assert result == "Bear Researcher"


def test_risk_analysis_routing_from_aggressive():
    """Routes to Conservative Analyst when latest speaker is Aggressive"""
    logic = ConditionalLogic()

    state = {"risk_debate_state": {"count": 1, "latest_speaker": "Aggressive"}}

    result = logic.should_continue_risk_analysis(state)
    assert result == "Conservative Analyst"


def test_risk_analysis_routing_from_conservative():
    """Routes to Neutral Analyst when latest speaker is Conservative"""
    logic = ConditionalLogic()

    state = {"risk_debate_state": {"count": 2, "latest_speaker": "Conservative"}}

    result = logic.should_continue_risk_analysis(state)
    assert result == "Neutral Analyst"


def test_risk_analysis_routing_from_neutral():
    """Routes to Aggressive Analyst when latest speaker is Neutral"""
    logic = ConditionalLogic()

    state = {
        "risk_debate_state": {
            "count": 1,  # Below limit (max_risk_discuss_rounds=1 means 3 exchanges max)
            "latest_speaker": "Neutral",
        }
    }

    result = logic.should_continue_risk_analysis(state)
    assert result == "Aggressive Analyst"


def test_risk_limit_enforcement_max_reached():
    """Routes to Risk Judge when max risk rounds reached"""
    logic = ConditionalLogic(
        max_risk_discuss_rounds=2
    )  # 2 rounds = 6 exchanges (3 agents)

    state = {"risk_debate_state": {"count": 6, "latest_speaker": "Aggressive"}}

    result = logic.should_continue_risk_analysis(state)
    assert result == "Risk Judge"


def test_risk_limit_enforcement_below_max():
    """Continues risk analysis when count is below max limit"""
    logic = ConditionalLogic(max_risk_discuss_rounds=2)

    state = {"risk_debate_state": {"count": 5, "latest_speaker": "Conservative"}}

    result = logic.should_continue_risk_analysis(state)
    assert result == "Neutral Analyst"


def test_debate_default_routing():
    """Routes to Bull Researcher by default when current_response doesn't start with Bull"""
    logic = ConditionalLogic()

    state = {
        "investment_debate_state": {
            "count": 1,
            "current_response": "Some other response",
        }
    }

    result = logic.should_continue_debate(state)
    assert result == "Bull Researcher"


def test_risk_analysis_default_routing():
    """Routes to Aggressive Analyst by default when latest_speaker doesn't start with expected prefixes"""
    logic = ConditionalLogic()

    state = {"risk_debate_state": {"count": 1, "latest_speaker": "Unknown Speaker"}}

    result = logic.should_continue_risk_analysis(state)
    assert result == "Aggressive Analyst"
