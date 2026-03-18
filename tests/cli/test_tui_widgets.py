"""Tests for custom Textual TUI widgets."""

from textual.widgets import RichLog

from cli.main import MessageBuffer
from cli.tui_widgets import MessagesPanel, ReportPanel


class TestMessagesPanel:
    """Tests for the MessagesPanel widget."""

    def test_messages_panel_is_rich_log_subclass(self):
        """Verify MessagesPanel is a subclass of RichLog."""
        assert issubclass(MessagesPanel, RichLog)

    def test_messages_panel_accepts_message_buffer(self):
        """Verify MessagesPanel accepts a MessageBuffer in __init__."""
        buffer = MessageBuffer()
        panel = MessagesPanel(buffer)
        assert panel.message_buffer is buffer

    def test_messages_panel_has_default_css(self):
        """Verify MessagesPanel has DEFAULT_CSS defined."""
        assert hasattr(MessagesPanel, "DEFAULT_CSS")
        assert isinstance(MessagesPanel.DEFAULT_CSS, str)

    def test_messages_panel_has_refresh_messages_method(self):
        """Verify MessagesPanel has refresh_messages method."""
        buffer = MessageBuffer()
        panel = MessagesPanel(buffer)
        assert hasattr(panel, "refresh_messages")
        assert callable(panel.refresh_messages)


class TestReportPanel:
    """Tests for the ReportPanel widget."""

    def test_report_panel_is_vertical_scroll_subclass(self):
        """Verify ReportPanel is a subclass of VerticalScroll."""
        from textual.containers import VerticalScroll

        assert issubclass(ReportPanel, VerticalScroll)

    def test_report_panel_accepts_message_buffer(self):
        """Verify ReportPanel accepts a MessageBuffer in __init__."""
        buffer = MessageBuffer()
        panel = ReportPanel(buffer)
        assert panel.message_buffer is buffer

    def test_report_panel_has_default_css(self):
        """Verify ReportPanel has DEFAULT_CSS defined."""
        assert hasattr(ReportPanel, "DEFAULT_CSS")
        assert isinstance(ReportPanel.DEFAULT_CSS, str)

    def test_report_panel_has_refresh_report_method(self):
        """Verify ReportPanel has refresh_report method."""
        buffer = MessageBuffer()
        panel = ReportPanel(buffer)
        assert hasattr(panel, "refresh_report")
        assert callable(panel.refresh_report)
