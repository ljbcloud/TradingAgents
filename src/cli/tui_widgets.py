"""Custom Textual widgets for TradingAgents TUI."""

from operator import itemgetter

from rich.markdown import Markdown
from rich.table import Table
from textual.containers import VerticalScroll
from textual.widgets import RichLog, Static

from cli.main import MessageBuffer


class MessagesPanel(RichLog):
    """A panel widget that displays messages and tool calls from MessageBuffer.

    This widget extends RichLog to provide automatic scrolling capabilities
    and displays messages in a formatted table with columns for Time, Type,
    and Content.

    Attributes:
        message_buffer: The MessageBuffer instance containing messages and
            tool calls to display.
    """

    DEFAULT_CSS = """
    MessagesPanel {
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        message_buffer: MessageBuffer,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialize the MessagesPanel.

        Args:
            message_buffer: The MessageBuffer instance containing messages
                and tool calls to display.
            name: The name of the widget.
            id: The ID of the widget in the DOM.
            classes: The CSS classes for the widget.
            disabled: Whether the widget is disabled.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.message_buffer = message_buffer

    def refresh_messages(self) -> None:
        """Refresh the displayed messages from the message buffer.

        This method clears the current log, builds a Rich Table with
        message data, and writes it to the RichLog. Messages are sorted
        by timestamp (newest first).
        """
        self.clear()

        # Build table for messages
        table = Table(
            show_header=True,
            header_style="bold magenta",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        table.add_column("Time", style="cyan", width=8, justify="center")
        table.add_column("Type", style="green", width=10, justify="center")
        table.add_column("Content", style="white", no_wrap=False, ratio=1)

        # Combine messages and tool calls
        all_messages = []

        # Add tool calls with "Tool" type
        for timestamp, tool_name, args in self.message_buffer.tool_calls:
            args_str = str(args)
            max_args_length = 80
            if len(args_str) > max_args_length:
                args_str = args_str[: max_args_length - 3] + "..."
            all_messages.append((timestamp, "Tool", f"{tool_name}: {args_str}"))

        # Add regular messages
        for timestamp, msg_type, content in self.message_buffer.messages:
            content_str = str(content) if content else ""
            max_content_length = 200
            if len(content_str) > max_content_length:
                content_str = content_str[: max_content_length - 3] + "..."
            all_messages.append((timestamp, msg_type, content_str))

        # Sort by timestamp descending (newest first)
        all_messages.sort(key=itemgetter(0), reverse=True)

        # Add messages to table
        for timestamp, msg_type, content in all_messages:
            table.add_row(timestamp, msg_type, content)

        self.write(table)

    def on_mount(self) -> None:
        """Handle the mount event to initially populate the panel."""
        self.refresh_messages()


class ReportPanel(VerticalScroll):
    """A scrollable panel widget that displays the complete analysis report.

    This widget extends VerticalScroll to provide scrolling capabilities
    for the report content displayed as Markdown.

    Attributes:
        message_buffer: The MessageBuffer instance containing the report data.
    """

    DEFAULT_CSS = """
    ReportPanel {
        height: 1fr;
        border: solid $success;
        padding: 1 2;
    }
    """

    def __init__(
        self,
        message_buffer: MessageBuffer,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialize the ReportPanel.

        Args:
            message_buffer: The MessageBuffer instance containing report data.
            name: The name of the widget.
            id: The ID of the widget in the DOM.
            classes: The CSS classes for the widget.
            disabled: Whether the widget is disabled.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.message_buffer = message_buffer

    def refresh_report(self) -> None:
        """Refresh the displayed report from the message buffer.

        This method gets the final_report from the buffer and displays it
        as Markdown content. If no report is available, shows a waiting message.
        """
        # Remove existing content if any
        try:
            existing = self.query_one("#report-content", Static)
            existing.remove()
        except Exception:
            pass  # No existing content to remove

        # Get report content
        report_text = self.message_buffer.final_report
        if not report_text:
            report_text = "Waiting for analysis report..."

        # Create new content widget
        content = Static(Markdown(report_text), id="report-content")
        self.mount(content)

    def on_mount(self) -> None:
        """Handle the mount event to initially populate the panel."""
        self.refresh_report()
