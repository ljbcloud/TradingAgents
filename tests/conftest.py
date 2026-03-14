from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture
def mock_llm_response():
    mock = MagicMock()
    mock.content = "Mock analysis content"
    mock.response_metadata = {"token_usage": {"total_tokens": 100}}
    return mock


@pytest.fixture
def mock_llm_error():
    from langchain_core.exceptions import LangChainException

    return LangChainException("API Error")


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI LLM client for testing."""
    instance = MagicMock()
    instance.bind_tools.return_value = instance
    instance.invoke.return_value = MagicMock(
        content="Analysis result",
        response_metadata={"token_usage": {"total_tokens": 150}},
    )
    return instance


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic LLM client for testing."""
    instance = MagicMock()
    instance.bind_tools.return_value = instance
    instance.invoke.return_value = MagicMock(content="Claude analysis")
    return instance


@pytest.fixture
def mock_google_client():
    """Mock Google LLM client for testing."""
    instance = MagicMock()
    instance.bind_tools.return_value = instance
    instance.invoke.return_value = MagicMock(content="Gemini analysis")
    return instance


@pytest.fixture
def sample_stock_data():
    return pd.DataFrame({
        "close": [150.0, 152.0, 151.0, 153.0, 155.0],
        "volume": [1000000, 1200000, 1100000, 1300000, 1400000],
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="D"),
    }).set_index("timestamp")


@pytest.fixture
def sample_stock_data_expanded():
    return pd.DataFrame({
        "close": [
            150.0,
            152.0,
            151.0,
            153.0,
            155.0,
            154.0,
            156.0,
            153.0,
            157.0,
            158.0,
            155.0,
            159.0,
            160.0,
            157.0,
            162.0,
            161.0,
            163.0,
            160.0,
            164.0,
            165.0,
        ],
        "volume": [
            1000000,
            1200000,
            1100000,
            1300000,
            1400000,
            1350000,
            1450000,
            1250000,
            1500000,
            1550000,
            1300000,
            1600000,
            1650000,
            1400000,
            1700000,
            1750000,
            1450000,
            1800000,
            1850000,
            1900000,
        ],
        "timestamp": pd.date_range("2024-01-01", periods=20, freq="D"),
    }).set_index("timestamp")


@pytest.fixture
def sample_stock_data_with_missing():
    return pd.DataFrame({
        "close": [150.0, None, 151.0, 153.0, 155.0],
        "volume": [1000000, 1200000, None, 1300000, 1400000],
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="D"),
    }).set_index("timestamp")


@pytest.fixture
def mock_config():
    return {
        "deep_think_llm": {"provider": "openai", "model": "gpt-4"},
        "quick_think_llm": {"provider": "openai", "model": "gpt-3.5-turbo"},
        "data_vendor": {"category": "y_finance", "api_key": None},
    }


@pytest.fixture
def mock_agent_state():
    """Mock agent state for testing analyst nodes."""
    return {
        "ticker": "AAPL",
        "trade_date": "2024-01-01",
        "company_of_interest": "AAPL",
        "messages": [],
    }


@pytest.fixture
def mock_yfinance_data(sample_stock_data):
    with patch("tradingagents.dataflows.y_finance.yf") as mock:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = sample_stock_data
        mock_ticker.info = {"marketCap": 2500000000000}
        mock.Ticker.return_value = mock_ticker
        yield mock


@pytest.fixture
def mock_alpha_vantage():
    with patch("tradingagents.dataflows.alpha_vantage.TimeSeries") as mock:
        mock_ts = mock.return_value
        mock_ts.get_intraday.return_value = {
            "Meta Data": {"Symbol": "AAPL"},
            "Time Series (5min)": {},
        }
        yield mock_ts


@pytest.fixture(autouse=True)
def mock_default_config(mock_config):
    with patch("tradingagents.default_config.DEFAULT_CONFIG", mock_config):
        yield
