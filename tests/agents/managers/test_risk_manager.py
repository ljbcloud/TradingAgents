from unittest.mock import MagicMock

from agents.managers.risk_manager import create_risk_manager


def test_create_risk_manager_returns_callable():
    """Returns a node function"""
    mock_llm = MagicMock()
    mock_memory = MagicMock()
    node = create_risk_manager(mock_llm, mock_memory)
    assert callable(node)


def test_risk_manager_returns_risk_debate_state(mock_openai_client, mock_llm_response):
    """Returns risk_debate_state in result"""
    mock_llm_response.content = "Buy - Acceptable risk"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market analysis",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "sentiment_report": "Sentiment analysis",
        "investment_plan": "Buy - Strong fundamentals",
        "risk_debate_state": {
            "history": "Aggressive: Go long\nNeutral: Wait\nConservative: Hold",
            "aggressive_history": "Aggressive: Go long",
            "conservative_history": "Conservative: Hold",
            "neutral_history": "Neutral: Wait",
            "current_aggressive_response": "Aggressive: Go long",
            "current_conservative_response": "Conservative: Hold",
            "current_neutral_response": "Neutral: Wait",
            "count": 3,
        },
    }

    result = node(state)

    assert "risk_debate_state" in result


def test_risk_manager_returns_final_trade_decision(
    mock_openai_client, mock_llm_response
):
    """Returns final_trade_decision in result"""
    mock_llm_response.content = "Sell - High risk detected"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "sentiment_report": "Sentiment data",
        "investment_plan": "Buy recommendation",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
    }

    result = node(state)

    assert "final_trade_decision" in result
    assert result["final_trade_decision"] == "Sell - High risk detected"


def test_risk_manager_judge_decision_in_debate_state(
    mock_openai_client, mock_llm_response
):
    """Sets judge_decision in risk_debate_state"""
    mock_llm_response.content = "Hold - Wait for clearer signals"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market report",
        "news_report": "News report",
        "fundamentals_report": "Fundamentals report",
        "sentiment_report": "Sentiment report",
        "investment_plan": "Initial buy plan",
        "risk_debate_state": {
            "history": "Aggressive: Bullish\nConservative: Bearish\nNeutral: Uncertain",
            "aggressive_history": "Aggressive: Bullish",
            "conservative_history": "Conservative: Bearish",
            "neutral_history": "Neutral: Uncertain",
            "current_aggressive_response": "Aggressive: Bullish",
            "current_conservative_response": "Conservative: Bearish",
            "current_neutral_response": "Neutral: Uncertain",
            "count": 3,
        },
    }

    result = node(state)

    assert "judge_decision" in result["risk_debate_state"]
    assert (
        result["risk_debate_state"]["judge_decision"]
        == "Hold - Wait for clearer signals"
    )


def test_risk_manager_uses_memory(mock_openai_client, mock_llm_response):
    """Retrieves past memories and includes them in prompt"""
    mock_llm_response.content = "Buy based on past successful patterns"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = [
        {"recommendation": "Avoid similar risky conditions"},
        {"recommendation": "Wait when uncertain"},
    ]

    node = create_risk_manager(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market conditions",
        "news_report": "News",
        "fundamentals_report": "Fundamentals",
        "sentiment_report": "Sentiment",
        "investment_plan": "Proposed action",
        "risk_debate_state": {
            "history": "",
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "current_aggressive_response": "",
            "current_conservative_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
    }

    node(state)

    mock_memory.get_memories.assert_called_once()


def test_risk_manager_includes_debate_history(mock_openai_client, mock_llm_response):
    """Includes conversation history in prompt"""
    mock_llm_response.content = "Decision based on full risk debate"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market data",
        "news_report": "News data",
        "fundamentals_report": "Fundamentals data",
        "sentiment_report": "Sentiment data",
        "investment_plan": "Trader plan",
        "risk_debate_state": {
            "history": "Aggressive: Take the risk\nConservative: Too dangerous\nNeutral: Proceed with caution",
            "aggressive_history": "Aggressive content",
            "conservative_history": "Conservative content",
            "neutral_history": "Neutral content",
            "current_aggressive_response": "Aggressive: Take the risk",
            "current_conservative_response": "Conservative: Too dangerous",
            "current_neutral_response": "Neutral: Proceed with caution",
            "count": 3,
        },
    }

    result = node(state)

    assert "risk_debate_state" in result


def test_risk_manager_preserves_debate_count(mock_openai_client, mock_llm_response):
    """Does not increment debate count"""
    mock_llm_response.content = "Final risk assessment"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market report",
        "news_report": "News report",
        "fundamentals_report": "Fundamentals report",
        "sentiment_report": "Sentiment report",
        "investment_plan": "Investment plan",
        "risk_debate_state": {
            "history": "Debate content",
            "aggressive_history": "Aggressive",
            "conservative_history": "Conservative",
            "neutral_history": "Neutral",
            "current_aggressive_response": "Last aggressive",
            "current_conservative_response": "Last conservative",
            "current_neutral_response": "Last neutral",
            "count": 4,
        },
    }

    result = node(state)

    assert result["risk_debate_state"]["count"] == 4


def test_risk_manager_sets_latest_speaker_to_judge(
    mock_openai_client, mock_llm_response
):
    """Sets latest_speaker to 'Judge' in risk_debate_state"""
    mock_llm_response.content = "Buy decision"
    mock_openai_client.invoke.return_value = mock_llm_response

    mock_memory = MagicMock()
    mock_memory.get_memories.return_value = []

    node = create_risk_manager(mock_openai_client, mock_memory)
    state = {
        "company_of_interest": "AAPL",
        "market_report": "Market report",
        "news_report": "News report",
        "fundamentals_report": "Fundamentals report",
        "sentiment_report": "Sentiment report",
        "investment_plan": "Plan",
        "risk_debate_state": {
            "history": "Aggressive: Go\nNeutral: Wait\nConservative: Stop",
            "aggressive_history": "Aggressive: Go",
            "conservative_history": "Conservative: Stop",
            "neutral_history": "Neutral: Wait",
            "current_aggressive_response": "Aggressive: Go",
            "current_conservative_response": "Conservative: Stop",
            "current_neutral_response": "Neutral: Wait",
            "count": 3,
            "latest_speaker": "Conservative",
        },
    }

    result = node(state)

    assert result["risk_debate_state"]["latest_speaker"] == "Judge"
