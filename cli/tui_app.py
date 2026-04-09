"""Textual TUI application for TradingAgents."""

from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from cli.main import MessageBuffer
from cli.tui_widgets import MessagesPanel, ReportPanel

# Status colours for Radon validation display
_RADON_STATUS_COLORS: dict[str, str] = {
    "PASS": "green",
    "FAIL": "red",
    "SKIP": "yellow",
    "ERROR": "red",
    "UNAVAILABLE": "dim",
}


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
        self.radon_validation_result: str = ""
        self.radon_validation_details: dict = {}

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

    def set_radon_validation(self, result: str, details: dict) -> None:
        """Store radon validation state and refresh the display.

        Args:
            result: Validation status string (PASS, FAIL, SKIP, ERROR,
                UNAVAILABLE, or empty).
            details: Dict with milestone results, gates, decision, and
                summary information.
        """
        self.radon_validation_result = result
        self.radon_validation_details = details
        self._refresh_radon_validation()

    def _refresh_radon_validation(self) -> None:
        """Render the radon validation section inside the analysis panel."""
        try:
            report_panel = self.query_one("#analysis", ReportPanel)
        except Exception:
            return

        result = self.radon_validation_result
        if not result:
            report_panel.refresh_report()
            return

        color = _RADON_STATUS_COLORS.get(result, "white")

        lines: list[str] = [
            "## Radon Validation",
            f"**Status:** [{color}]{result}[/{color}]",
        ]

        details = self.radon_validation_details
        if isinstance(details, dict):
            summary = details.get("summary")
            if summary:
                lines.append(f"**Summary:** {summary}")

            decision = details.get("decision")
            if decision:
                lines.append(f"**Decision:** {decision}")

            milestones = details.get("milestones", [])
            if milestones:
                passed = sum(1 for m in milestones if m.get("passed"))
                lines.append(f"**Milestones:** {passed}/{len(milestones)} passed")
                for m in milestones:
                    icon = "\u2713" if m.get("passed") else "\u2717"
                    name = m.get("milestone", "Unknown")
                    reason = m.get("reason", "")
                    lines.append(f"- {icon} {name}: {reason}")

            gates = details.get("gates", [])
            if gates:
                for g in gates:
                    gate_status = g.get("status", "unknown")
                    gate_name = g.get("name", "Gate")
                    lines.append(f"- Gate **{gate_name}**: {gate_status}")
        elif isinstance(details, str) and details:
            lines.append(details)

        radon_section = "\n\n".join(lines)

        existing_report = self.message_buffer.final_report or ""
        combined = (
            f"{existing_report}\n\n---\n\n{radon_section}"
            if existing_report
            else radon_section
        )

        try:
            existing = report_panel.query_one("#report-content", Static)
            existing.remove()
        except Exception:
            pass

        report_panel.mount(Static(Markdown(combined), id="report-content"))
