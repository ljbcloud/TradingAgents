from unittest.mock import MagicMock

from agents.analysts.fundamentals_analyst import (
    create_fundamentals_analyst,
)
from agents.analysts.market_analyst import create_market_analyst
from agents.analysts.news_analyst import create_news_analyst
from agents.analysts.social_media_analyst import (
    create_social_media_analyst,
)


def test_market_analyst_returns_callable():
    mock_llm = MagicMock()
    node = create_market_analyst(mock_llm)
    assert callable(node)


def test_social_media_analyst_returns_callable():
    mock_llm = MagicMock()
    node = create_social_media_analyst(mock_llm)
    assert callable(node)


def test_news_analyst_returns_callable():
    mock_llm = MagicMock()
    node = create_news_analyst(mock_llm)
    assert callable(node)


def test_fundamentals_analyst_returns_callable():
    mock_llm = MagicMock()
    node = create_fundamentals_analyst(mock_llm)
    assert callable(node)
