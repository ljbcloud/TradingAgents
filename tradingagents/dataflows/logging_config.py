"""
Logging configuration for tradingagents.dataflows module.

This module provides centralized logging configuration for all data vendor modules.
"""

import logging
import sys

# Configure logging format with timestamp, level, module, and message
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_dataflows_logging(level: int = logging.INFO) -> None:
    """
    Configure logging for the tradingagents.dataflows module.

    Args:
        level: Logging level (default: logging.INFO)
    """
    # Configure root handler for dataflows module
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    handler.setFormatter(formatter)

    # Get or create the dataflows logger
    logger = logging.getLogger("tradingagents.dataflows")
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(handler)
        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False


# Create module-level loggers
_dataflows_logger = logging.getLogger("tradingagents.dataflows")
_alpha_vantage_logger = logging.getLogger("tradingagents.dataflows.alpha_vantage")
_y_finance_logger = logging.getLogger("tradingagents.dataflows.y_finance")
_common_logger = logging.getLogger("tradingagents.dataflows.common")


# Export loggers for use in other modules
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific dataflows submodule.

    Args:
        name: Name of the submodule (e.g., "alpha_vantage", "y_finance", "common")

    Returns:
        Logger instance for the specified submodule
    """
    return logging.getLogger(f"tradingagents.dataflows.{name}")


# Export individual loggers
dataflows_logger = _dataflows_logger
alpha_vantage_logger = _alpha_vantage_logger
y_finance_logger = _y_finance_logger
common_logger = _common_logger


__all__ = [
    "alpha_vantage_logger",
    "common_logger",
    "configure_dataflows_logging",
    "dataflows_logger",
    "get_logger",
    "y_finance_logger",
]
