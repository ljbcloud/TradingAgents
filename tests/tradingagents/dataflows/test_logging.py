"""Unit tests for dataflows logging configuration."""

# ruff: noqa: S101 - assert is expected in tests

import logging

from tradingagents.dataflows.logging_config import (
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    alpha_vantage_logger,
    common_logger,
    configure_dataflows_logging,
    dataflows_logger,
    get_logger,
    y_finance_logger,
)


class TestLoggingSetup:
    """Tests for logging setup and configuration."""

    def test_configure_dataflows_logging_creates_logger(self):
        """configure_dataflows_logging should create the dataflows logger."""
        configure_dataflows_logging()
        logger = logging.getLogger("tradingagents.dataflows")
        assert logger is not None

    def test_configure_dataflows_logging_sets_level(self):
        """configure_dataflows_logging should set the logger level."""
        configure_dataflows_logging(level=logging.DEBUG)
        logger = logging.getLogger("tradingagents.dataflows")
        assert logger.level == logging.DEBUG

    def test_configure_dataflows_logging_adds_handler(self):
        """configure_dataflows_logging should add a handler to the logger."""
        configure_dataflows_logging()
        logger = logging.getLogger("tradingagents.dataflows")
        assert len(logger.handlers) > 0

    def test_configure_dataflows_logging_uses_stdout_handler(self):
        """configure_dataflows_logging should use a StreamHandler."""
        configure_dataflows_logging()
        logger = logging.getLogger("tradingagents.dataflows")
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_configure_dataflows_logging_sets_formatter(self):
        """configure_dataflows_logging should set a formatter on the handler."""
        configure_dataflows_logging()
        logger = logging.getLogger("tradingagents.dataflows")
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                assert handler.formatter is not None
                break

    def test_configure_dataflows_logging_prevents_propagation(self):
        """configure_dataflows_logging should prevent propagation to root logger."""
        configure_dataflows_logging()
        logger = logging.getLogger("tradingagents.dataflows")
        assert logger.propagate is False

    def test_configure_dataflows_logging_does_not_duplicate_handlers(self):
        """configure_dataflows_logging should not add duplicate handlers."""
        configure_dataflows_logging()
        logger = logging.getLogger("tradingagents.dataflows")
        initial_count = len(logger.handlers)

        configure_dataflows_logging()  # Call again
        assert len(logger.handlers) == initial_count


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger(self):
        """get_logger should return a Logger instance."""
        logger = get_logger("alpha_vantage")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_returns_correct_name(self):
        """get_logger should return a logger with the correct name."""
        logger = get_logger("alpha_vantage")
        assert logger.name == "tradingagents.dataflows.alpha_vantage"

    def test_get_logger_with_different_names(self):
        """get_logger should return different loggers for different names."""
        logger1 = get_logger("alpha_vantage")
        logger2 = get_logger("y_finance")
        assert logger1.name != logger2.name

    def test_get_logger_returns_same_logger_for_same_name(self):
        """get_logger should return the same logger instance for the same name."""
        logger1 = get_logger("common")
        logger2 = get_logger("common")
        assert logger1 is logger2


class TestExportedLoggers:
    """Tests for pre-exported logger instances."""

    def test_dataflows_logger_has_correct_name(self):
        """dataflows_logger should have the correct name."""
        assert dataflows_logger.name == "tradingagents.dataflows"

    def test_alpha_vantage_logger_has_correct_name(self):
        """alpha_vantage_logger should have the correct name."""
        assert alpha_vantage_logger.name == "tradingagents.dataflows.alpha_vantage"

    def test_y_finance_logger_has_correct_name(self):
        """y_finance_logger should have the correct name."""
        assert y_finance_logger.name == "tradingagents.dataflows.y_finance"

    def test_common_logger_has_correct_name(self):
        """common_logger should have the correct name."""
        assert common_logger.name == "tradingagents.dataflows.common"


class TestLogFormat:
    """Tests for log format configuration."""

    def test_log_format_contains_levelname(self):
        """LOG_FORMAT should contain levelname."""
        assert "%(levelname)s" in LOG_FORMAT

    def test_log_format_contains_name(self):
        """LOG_FORMAT should contain logger name."""
        assert "%(name)s" in LOG_FORMAT

    def test_log_format_contains_message(self):
        """LOG_FORMAT should contain the message."""
        assert "%(message)s" in LOG_FORMAT

    def test_log_format_contains_asctime(self):
        """LOG_FORMAT should contain timestamp."""
        assert "%(asctime)s" in LOG_FORMAT

    def test_log_date_format_is_defined(self):
        """LOG_DATE_FORMAT should be defined."""
        assert LOG_DATE_FORMAT is not None
        assert len(LOG_DATE_FORMAT) > 0


class TestLogMessages:
    """Tests for log message emission using direct handler capture."""

    def test_log_info_message(self):
        """Test that info messages are emitted correctly."""
        import io

        logger = get_logger("test_messages")
        logger.setLevel(logging.INFO)
        # Enable propagation for test capture
        logger.propagate = True

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        logger.info("Test info message")
        handler.flush()

        assert "Test info message" in stream.getvalue()
        logger.removeHandler(handler)

    def test_log_warning_message(self):
        """Test that warning messages are emitted correctly."""
        import io

        logger = get_logger("test_warning")
        logger.setLevel(logging.WARNING)
        logger.propagate = True

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.WARNING)
        logger.addHandler(handler)

        logger.warning("Test warning message")
        handler.flush()

        assert "Test warning message" in stream.getvalue()
        logger.removeHandler(handler)

    def test_log_error_message(self):
        """Test that error messages are emitted correctly."""
        import io

        logger = get_logger("test_error")
        logger.setLevel(logging.ERROR)
        logger.propagate = True

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)

        logger.error("Test error message")
        handler.flush()

        assert "Test error message" in stream.getvalue()
        logger.removeHandler(handler)

    def test_log_debug_message(self):
        """Test that debug messages are emitted correctly."""
        import io

        logger = get_logger("test_debug")
        logger.setLevel(logging.DEBUG)
        logger.propagate = True

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        logger.debug("Test debug message")
        handler.flush()

        assert "Test debug message" in stream.getvalue()
        logger.removeHandler(handler)

    def test_log_info_not_emitted_at_warning_level(self):
        """Test that info messages are not emitted at warning level."""
        import io

        logger = get_logger("test_level_filter")
        logger.setLevel(logging.WARNING)
        logger.propagate = True

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.WARNING)
        logger.addHandler(handler)

        logger.info("This info should not be emitted")
        handler.flush()

        assert "This info should not be emitted" not in stream.getvalue()
        logger.removeHandler(handler)

    def test_log_record_has_level(self):
        """Test that log records have the correct level attribute."""
        logger = get_logger("test_level_attr")
        records = []

        class RecordHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        logger.addHandler(RecordHandler())
        logger.setLevel(logging.INFO)

        logger.info("Info level message")

        assert len(records) == 1
        assert records[0].levelname == "INFO"
        logger.handlers = [
            h for h in logger.handlers if not isinstance(h, RecordHandler)
        ]

    def test_log_record_has_logger_name(self):
        """Test that log records have the correct logger name."""
        logger = get_logger("test_name_attr")
        records = []

        class RecordHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        logger.addHandler(RecordHandler())
        logger.setLevel(logging.INFO)

        logger.info("Named logger message")

        assert len(records) == 1
        assert records[0].name == "tradingagents.dataflows.test_name_attr"
        logger.handlers = [
            h for h in logger.handlers if not isinstance(h, RecordHandler)
        ]


class TestLoggerHierarchy:
    """Tests for logger hierarchy behavior."""

    def test_child_logger_inherits_from_parent(self):
        """Test that child loggers inherit from parent logger."""
        parent = logging.getLogger("tradingagents.dataflows")
        child = get_logger("child")

        # Child logger name should start with parent name
        assert child.name.startswith(parent.name)

    def test_multiple_child_loggers_are_distinct(self):
        """Test that multiple child loggers are distinct."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not logger2
        assert logger1.name != logger2.name
