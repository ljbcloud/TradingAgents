"""Textual TUI application for TradingAgents."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from cli.main import MessageBuffer
from cli.tui_widgets import MessagesPanel, ReportPanel


class TradingAgentsApp(App):
    """Textual TUI application for TradingAgents.

    This is a scrollable interface provides:
        - Standard navigation (arrow keys, page up/down)
        - Vi-style navigation (j/k, Ctrl+u/d)
        - Panel focus (Tab, Shift+Tab)
        - Quit (q)
    """

    BINDINGS = [
        # Standard navigation
        ("up", "scroll_up", "Scroll Up"),
        ("down", "scroll_down", "Scroll Down"),
        ("pageup", "scroll_page_up", "Page Up"),
        ("pagedown", "scroll_page_down", "Page Down"),
        ("home", "scroll_to_top", "Scroll to Top"),
        ("end", "scroll_to_bottom", "Scroll to Bottom"),
        # Vi-style navigation
        ("k", "scroll_up", "Scroll Up (vi)"),
        ("j", "scroll_down", "Scroll Down (vi)"),
        ("ctrl+u", "scroll_page_up", "Page Up (vi)"),
        ("ctrl+d", "scroll_page_down", "Page Down (vi)"),
        ("g", "scroll_to_top", "Scroll to Top (vi)"),
        ("G", "scroll_to_bottom", "Scroll to Bottom (vi)"),
        # Panel focus
        ("tab", "focus_next_panel", "Next Panel"),
        ("shift+tab", "focus_prev_panel", "Previous Panel"),
        # Quit
        ("q", "quit", "Quit"),
    ]

    def __init__(self, message_buffer: MessageBuffer | None = None):
        """Initialize the TradingAgents TUI app.

        Args:
            message_buffer: The message buffer containing agent status,
                messages, and report data. If None, a new buffer is created.
        """
        super().__init__()
        self.message_buffer = message_buffer or MessageBuffer()

    def compose(self) -> ComposeResult:
        """Compose the TUI layout.

        Layout structure matching existing Rich Live layout:
        - Header
        - Main container:
            - Upper (horizontal split):
                - Progress panel
                - Messages panel
            - Analysis panel (ReportPanel with scrolling)
        - Footer
        """
        yield Header()

        with Container(id="main"):
            with Vertical(id="upper-container"):  # noqa: SIM117 - Textual requires nested with for DOM hierarchy
                with Horizontal(id="upper"):
                    yield Static("Progress", id="progress")
                    yield MessagesPanel(self.message_buffer, id="messages")
            yield ReportPanel(self.message_buffer, id="analysis")

        yield Footer()

    def action_scroll_up(self) -> None:
        """Scroll up one line in the focused panel."""
        focused = self.focused
        if focused is None:
            return

        # Get the focused scrollable widget
        if hasattr(focused, "scroll_up"):
            focused.scroll_up()

    def action_scroll_down(self) -> None:
        """Scroll down one line in the focused panel."""
        focused = self.focused
        if focused is None:
            return

        # Get the focused scrollable widget
        if hasattr(focused, "scroll_down"):
            focused.scroll_down()

    def action_scroll_page_up(self) -> None:
        """Scroll up one page in the focused panel."""
        focused = self.focused
        if focused is None:
            return

        # Get the focused scrollable widget
        if hasattr(focused, "scroll_page_up"):
            focused.scroll_page_up()

    def action_scroll_page_down(self) -> None:
        """Scroll down one page in the focused panel."""
        focused = self.focused
        if focused is None:
            return

        # Get the focused scrollable widget
        if hasattr(focused, "scroll_page_down"):
            focused.scroll_page_down()

    def action_scroll_to_top(self) -> None:
        """Scroll to top of focused panel."""
        focused = self.focused
        if focused is None:
            return

        # Get the focused scrollable widget
        if hasattr(focused, "scroll_home"):
            focused.scroll_home()

    def action_scroll_to_bottom(self) -> None:
        """Scroll to bottom of focused panel."""
        focused = self.focused
        if focused is None:
            return

        # Get the focused scrollable widget
        if hasattr(focused, "scroll_end"):
            focused.scroll_end()

    def action_focus_next_panel(self) -> None:
        """Focus the next scrollable panel."""
        self.screen.focus_next()

    def action_focus_prev_panel(self) -> None:
        """Focus the previous scrollable panel."""
        self.screen.focus_previous()

    def update_messages(self) -> None:
        """Update messages panel with new content and auto-scroll."""
        try:
            messages_panel = self.query_one("#messages", MessagesPanel)
            messages_panel.refresh_messages()
            messages_panel.scroll_end(animate=False)
        except Exception:
            pass  # Panel not mounted yet

        try:
            report_panel = self.query_one("#analysis", ReportPanel)
            report_panel.refresh_report()
            report_panel.scroll_end(animate=False)
        except Exception:
            pass  # Panel not mounted yet

    def update_report(self) -> None:
        """Update report panel with new content."""
        try:
            report_panel = self.query_one("#analysis", ReportPanel)
            report_panel.refresh_report()
            report_panel.scroll_end(animate=False)
        except Exception:
            pass  # Panel not mounted yet

    def update_all(self) -> None:
        """Update all panels."""
        self.update_messages()
        self.update_report()
