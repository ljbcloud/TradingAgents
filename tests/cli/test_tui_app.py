"""Tests for Textual TUI application."""

import pytest  # noqa: F401 - Used in future test implementations


class TestTUIAppExists:
    def test_tui_app_module_importable(self):
        """Verify tui_app module can be imported."""
        from cli import tui_app

        assert hasattr(tui_app, "TradingAgentsApp")
