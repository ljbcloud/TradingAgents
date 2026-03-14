from unittest.mock import MagicMock

import pytest

from tradingagents.graph.signal_processing import SignalProcessor


def test_signal_processor_initialization():
    """Initializes with quick thinking LLM"""
    mock_llm = MagicMock()
    processor = SignalProcessor(mock_llm)
    assert processor.quick_thinking_llm == mock_llm


def test_process_signal_buy_extraction():
    """Extracts BUY decision from signal"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "BUY"
    mock_llm.invoke.return_value = mock_response

    processor = SignalProcessor(mock_llm)
    result = processor.process_signal(
        "Based on analysis, we recommend buying AAPL stock."
    )

    assert result == "BUY"
    mock_llm.invoke.assert_called_once()


def test_process_signal_sell_extraction():
    """Extracts SELL decision from signal"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "SELL"
    mock_llm.invoke.return_value = mock_response

    processor = SignalProcessor(mock_llm)
    result = processor.process_signal("Market conditions suggest selling NVDA shares.")

    assert result == "SELL"
    mock_llm.invoke.assert_called_once()


def test_process_signal_hold_extraction():
    """Extracts HOLD decision from signal"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "HOLD"
    mock_llm.invoke.return_value = mock_response

    processor = SignalProcessor(mock_llm)
    result = processor.process_signal(
        "Current volatility is too high, recommend holding position."
    )

    assert result == "HOLD"
    mock_llm.invoke.assert_called_once()


def test_process_signal_case_handling_uppercase():
    """Handles uppercase signals correctly"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "BUY"
    mock_llm.invoke.return_value = mock_response

    processor = SignalProcessor(mock_llm)
    result = processor.process_signal("MARKET IS STRONGLY BULLISH")

    assert result == "BUY"


def test_process_signal_case_handling_lowercase():
    """Handles lowercase signals correctly"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "SELL"
    mock_llm.invoke.return_value = mock_response

    processor = SignalProcessor(mock_llm)
    result = processor.process_signal("bearish trend detected, sell recommended")

    assert result == "SELL"


def test_process_signal_case_handling_mixed():
    """Handles mixed case signals correctly"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "HOLD"
    mock_llm.invoke.return_value = mock_response

    processor = SignalProcessor(mock_llm)
    result = processor.process_signal("Market Is Too Volatile, Hold Position")

    assert result == "HOLD"


def test_process_signal_complex_parsing():
    """Extracts decision from complex multi-paragraph signal"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "BUY"
    mock_llm.invoke.return_value = mock_response

    processor = SignalProcessor(mock_llm)
    complex_signal = """
    Technical Analysis:
    - 50-day moving average crossed above 200-day
    - RSI indicates strong momentum
    - Volume is increasing
    
    Fundamental Analysis:
    - Earnings beat expectations
    - Revenue growth of 25% YoY
    - Strong cash position
    
    Recommendation:
    Based on the convergence of technical and fundamental indicators,
    we recommend an aggressive BUY position.
    """

    result = processor.process_signal(complex_signal)

    assert result == "BUY"


def test_process_signal_invalid_handling():
    """Handles invalid/unclear signals"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "HOLD"
    mock_llm.invoke.return_value = mock_response

    processor = SignalProcessor(mock_llm)
    result = processor.process_signal("The market data is inconclusive and unclear.")

    assert result == "HOLD"
