from langchain_core.messages import HumanMessage, RemoveMessage

from .core_stock_tools import get_stock_data
from .crypto_fundamentals_tools import (
    get_crypto_protocol_tvl,
    get_crypto_protocol_yields,
    get_crypto_token_info,
)
from .crypto_tools import get_crypto_candles, get_crypto_orderbook, get_crypto_ticker
from .fundamental_data_tools import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)
from .news_data_tools import get_global_news, get_insider_transactions, get_news
from .technical_indicators_tools import get_indicators

__all__ = [
    "get_balance_sheet",
    "get_cashflow",
    "get_crypto_candles",
    "get_crypto_orderbook",
    "get_crypto_protocol_tvl",
    "get_crypto_protocol_yields",
    "get_crypto_ticker",
    "get_crypto_token_info",
    "get_fundamentals",
    "get_global_news",
    "get_income_statement",
    "get_indicators",
    "get_insider_transactions",
    "get_news",
    "get_stock_data",
]


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": [*removal_operations, placeholder]}

    return delete_messages
