from unittest.mock import MagicMock

import pytest

from tradingagents.agents.analysts.fundamentals_analyst import (
    create_fundamentals_analyst,
)
from tradingagents.agents.analysts.market_analyst import create_market_analyst
from tradingagents.agents.analysts.news_analyst import create_news_analyst
from tradingagents.agents.analysts.social_media_analyst import (
    create_social_media_analyst,
)


@pytest.fixture
def mock_llm_response():
    mock = MagicMock()
    mock.content = "Mock analysis content"
    mock.tool_calls = []
    mock.response_metadata = {"token_usage": {"total_tokens": 100}}
    return mock


@pytest.fixture
def mock_llm_error():
    from langchain_core.exceptions import LangChainException

    return LangChainException("API Error")


@pytest.fixture
def mock_agent_state():
    return {"messages": [], "trade_date": "2024-01-01", "company_of_interest": "AAPL"}


class TestMarketAnalyst:
    def test_create_market_analyst_returns_callable(self, mock_llm_response):
        mock_llm = MagicMock()
        node = create_market_analyst(mock_llm)
        assert callable(node)

    def test_market_analyst_with_state_returns_dict(
        self, mock_llm_response, mock_agent_state
    ):
        mock_llm = MagicMock()
        node = create_market_analyst(mock_llm)
        result = node(mock_agent_state)
        assert isinstance(result, dict)
        assert "messages" in result


class TestSocialMediaAnalyst:
    def test_create_social_media_analyst_returns_callable(self, mock_llm_response):
        mock_llm = MagicMock()
        node = create_social_media_analyst(mock_llm)
        assert callable(node)

    def test_social_media_analyst_with_state_returns_dict(
        self, mock_llm_response, mock_agent_state
    ):
        mock_llm = MagicMock()
        node = create_social_media_analyst(mock_llm)
        result = node(mock_agent_state)
        assert isinstance(result, dict)
        assert "messages" in result


class TestNewsAnalyst:
    def test_create_news_analyst_returns_callable(self, mock_llm_response):
        mock_llm = MagicMock()
        node = create_news_analyst(mock_llm)
        assert callable(node)

    def test_news_analyst_with_state_returns_dict(
        self, mock_llm_response, mock_agent_state
    ):
        mock_llm = MagicMock()
        node = create_news_analyst(mock_llm)
        result = node(mock_agent_state)
        assert isinstance(result, dict)
        assert "messages" in result
        assert "news_report" in result


class TestFundamentalsAnalyst:
    def test_create_fundamentals_analyst_returns_callable(self, mock_llm_response):
        mock_llm = MagicMock()
        node = create_fundamentals_analyst(mock_llm)
        assert callable(node)

    def test_fundamentals_analyst_with_state_returns_dict(
        self, mock_llm_response, mock_agent_state
    ):
        mock_llm = MagicMock()
        node = create_fundamentals_analyst(mock_llm)
        result = node(mock_agent_state)
        assert isinstance(result, dict)
        assert "messages" in result
        assert "fundamentals_report" in result
