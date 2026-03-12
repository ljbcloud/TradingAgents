import time

from tradingagents.dataflows.y_finance import (
    get_stock_stats_indicators_window,
)

start_time = time.time()
result = get_stock_stats_indicators_window("AAPL", "macd", "2024-11-01", 30)
end_time = time.time()
