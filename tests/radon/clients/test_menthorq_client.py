"""Tests for radon.clients.menthorq_client module."""

from unittest.mock import MagicMock, patch

import pytest

from radon.clients.base import ClientStatus


@pytest.fixture
def mq_client_unavailable():
    from radon.clients.menthorq_client import MenthorQClient

    with (
        patch("radon.clients.menthorq_client.HAS_PLAYWRIGHT", False),
        patch.dict("os.environ", {}, clear=True),
    ):
        client = MenthorQClient.__new__(MenthorQClient)
        client._available = False
        client._headless = True
        client._storage_state_path = None
        client._username = None
        client._password = None
        client._api_key = None
        client._pw_context = None
        client._pw = None
        client._browser = None
        client._browser_context = None
        client._page = None
        return client


class TestMenthorQClientUnavailable:
    def test_instantiates_without_playwright(self, mq_client_unavailable):
        assert mq_client_unavailable is not None

    def test_is_available_returns_false(self, mq_client_unavailable):
        assert mq_client_unavailable.is_available() is False

    def test_check_availability_reports_unavailable(self, mq_client_unavailable):
        result = mq_client_unavailable.check_availability()
        assert result.status == ClientStatus.UNAVAILABLE
        assert "Playwright" in result.message

    def test_get_eod_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_eod("SPX", "2026-03-06") is None

    def test_get_cta_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_cta("2026-03-06") is None

    def test_get_screener_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_screener("options") is None

    def test_get_screener_category_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_screener_category("gamma", "test") is None

    def test_get_summary_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_summary("futures") is None

    def test_get_forex_levels_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_forex_levels() is None

    def test_get_dashboard_image_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_dashboard_image("eod") is None

    def test_get_intraday_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_intraday() is None

    def test_get_futures_list_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_futures_list() is None

    def test_get_futures_detail_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_futures_detail("ES") is None

    def test_get_futures_contracts_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_futures_contracts("ES", "2026-01-01") is None

    def test_get_forex_list_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_forex_list() is None

    def test_get_forex_detail_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_forex_detail("EURUSD") is None

    def test_get_crypto_list_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_crypto_list() is None

    def test_get_crypto_detail_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_crypto_detail("BTC") is None

    def test_discover_screener_cards_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.discover_screener_cards("gamma") is None

    def test_get_all_screener_data_returns_none(self, mq_client_unavailable):
        assert mq_client_unavailable.get_all_screener_data("gamma") is None


class TestMenthorQClientContextManager:
    def test_context_manager_returns_self(self, mq_client_unavailable):
        with mq_client_unavailable as client:
            assert client is mq_client_unavailable

    def test_close_is_safe_when_no_browser(self, mq_client_unavailable):
        mq_client_unavailable.close()
        assert mq_client_unavailable._browser is None
        assert mq_client_unavailable._pw_context is None


class TestMenthorQClientInit:
    @patch("radon.clients.menthorq_client.HAS_PLAYWRIGHT", False)
    def test_reads_username_from_env(self):
        from radon.clients.menthorq_client import MenthorQClient

        with patch.dict(
            "os.environ",
            {"MENTHORQ_USER": "user@test.com", "MENTHORQ_PASS": "pass123"},
            clear=False,
        ):
            client = MenthorQClient.__new__(MenthorQClient)
            client._available = False
            client._headless = True
            client._storage_state_path = None
            client._username = "user@test.com"
            client._password = "pass123"
            client._api_key = None
            client._pw_context = None
            client._pw = None
            client._browser = None
            client._browser_context = None
            client._page = None
            assert client._username == "user@test.com"
            assert client._password == "pass123"

    @patch("radon.clients.menthorq_client.HAS_PLAYWRIGHT", True)
    def test_raises_auth_error_without_credentials(self):
        from radon.clients.menthorq_client import MenthorQAuthError

        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(MenthorQAuthError, match="MENTHORQ_USER"),
        ):
            from radon.clients.menthorq_client import MenthorQClient

            MenthorQClient()

    @patch("radon.clients.menthorq_client.HAS_PLAYWRIGHT", True)
    def test_raises_auth_error_without_password(self):
        from radon.clients.menthorq_client import MenthorQAuthError

        with (
            patch.dict("os.environ", {"MENTHORQ_USER": "user@test.com"}, clear=True),
            pytest.raises(MenthorQAuthError, match="MENTHORQ_PASS"),
        ):
            from radon.clients.menthorq_client import MenthorQClient

            MenthorQClient()


class TestMenthorQClientAvailability:
    def test_check_availability_available(self):
        from radon.clients.menthorq_client import MenthorQClient

        with patch("radon.clients.menthorq_client.HAS_PLAYWRIGHT", False):
            client = MenthorQClient.__new__(MenthorQClient)
            client._available = True
            result = client.check_availability()
            assert result.status == ClientStatus.AVAILABLE

    def test_check_availability_unavailable(self, mq_client_unavailable):
        result = mq_client_unavailable.check_availability()
        assert result.status == ClientStatus.UNAVAILABLE


class TestMenthorQResolveApiKey:
    def test_resolves_anthropic_key(self):
        from radon.clients.menthorq_client import MenthorQClient

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "sk-test-123"},
            clear=False,
        ):
            key = MenthorQClient._resolve_api_key()
            assert key == "sk-test-123"

    def test_resolves_claude_code_key(self):
        import os

        from radon.clients.menthorq_client import MenthorQClient

        env = {"CLAUDE_CODE_API_KEY": "cc-test-456"}
        with patch.dict("os.environ", env, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            key = MenthorQClient._resolve_api_key()
            assert key is not None

    def test_returns_none_when_no_keys(self):
        from radon.clients.menthorq_client import MenthorQClient

        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            key = MenthorQClient._resolve_api_key()
            assert key is None


class TestMenthorQClientScreenerValidation:
    def test_screener_category_raises_on_invalid_category(self, mq_client_unavailable):
        from radon.clients.menthorq_client import MenthorQExtractionError

        mq_client_unavailable._available = True
        with pytest.raises(MenthorQExtractionError, match="Unknown screener category"):
            mq_client_unavailable.get_screener_category("invalid_cat", "some_slug")

    def test_screener_category_raises_on_invalid_slug(self, mq_client_unavailable):
        from radon.clients.menthorq_client import MenthorQExtractionError

        mq_client_unavailable._available = True
        with pytest.raises(MenthorQExtractionError, match="Unknown slug"):
            mq_client_unavailable.get_screener_category("gamma", "invalid_slug")

    def test_get_all_screener_data_raises_on_invalid_category(
        self, mq_client_unavailable
    ):
        from radon.clients.menthorq_client import MenthorQExtractionError

        mq_client_unavailable._available = True
        with pytest.raises(MenthorQExtractionError, match="Unknown screener category"):
            mq_client_unavailable.get_all_screener_data("nonexistent")

    def test_discover_screener_cards_raises_on_invalid_category(
        self, mq_client_unavailable
    ):
        from radon.clients.menthorq_client import MenthorQExtractionError

        mq_client_unavailable._available = True
        with pytest.raises(MenthorQExtractionError, match="Unknown screener category"):
            mq_client_unavailable.discover_screener_cards("invalid")


class TestMenthorQClientSummaryValidation:
    def test_summary_raises_on_invalid_category(self, mq_client_unavailable):
        from radon.clients.menthorq_client import MenthorQExtractionError

        mq_client_unavailable._available = True
        with pytest.raises(MenthorQExtractionError, match="Unknown summary category"):
            mq_client_unavailable.get_summary("invalid")

    def test_summary_accepts_futures(self, mq_client_unavailable):
        mq_client_unavailable._available = True
        mq_client_unavailable._navigate = MagicMock()
        with patch(
            "radon.clients.menthorq_client._scrape_tables",
            return_value=[],
        ):
            result = mq_client_unavailable.get_summary("futures")
            assert result == []

    def test_summary_accepts_cryptos(self, mq_client_unavailable):
        mq_client_unavailable._available = True
        mq_client_unavailable._navigate = MagicMock()
        with patch(
            "radon.clients.menthorq_client._scrape_tables",
            return_value=[],
        ):
            result = mq_client_unavailable.get_summary("cryptos")
            assert result == []


class TestMenthorQClientDashboardValidation:
    def test_dashboard_image_raises_on_invalid_command(self, mq_client_unavailable):
        from radon.clients.menthorq_client import MenthorQExtractionError

        mq_client_unavailable._available = True
        with pytest.raises(MenthorQExtractionError, match="Unknown dashboard command"):
            mq_client_unavailable.get_dashboard_image("invalid_cmd")

    def test_dashboard_image_raises_on_ticker_with_unsupported_command(
        self, mq_client_unavailable
    ):
        from radon.clients.menthorq_client import MenthorQExtractionError

        mq_client_unavailable._available = True
        with pytest.raises(
            MenthorQExtractionError, match="does not support ticker tabs"
        ):
            mq_client_unavailable.get_dashboard_image("cta", ticker="SPY")


class TestMenthorQClientGetEod:
    def test_get_eod_raises_on_empty_scrape(self, mq_client_unavailable):
        from radon.clients.menthorq_client import MenthorQExtractionError

        mq_client_unavailable._available = True
        mq_client_unavailable._navigate = MagicMock()
        with (
            patch(
                "radon.clients.menthorq_client._scrape_eod_fields",
                return_value={},
            ),
            pytest.raises(MenthorQExtractionError, match="EOD scrape"),
        ):
            mq_client_unavailable.get_eod("SPX", "2026-03-06")

    def test_get_eod_returns_data(self, mq_client_unavailable):
        mq_client_unavailable._available = True
        mq_client_unavailable._navigate = MagicMock()
        expected = {"last_price": 5500.0, "change_pct": 0.5}
        with patch(
            "radon.clients.menthorq_client._scrape_eod_fields",
            return_value=expected,
        ):
            result = mq_client_unavailable.get_eod("SPX", "2026-03-06")
            assert result == expected


class TestMenthorQClientGetCta:
    def test_get_cta_raises_without_api_key(self, mq_client_unavailable):
        from radon.clients.menthorq_client import MenthorQExtractionError

        mq_client_unavailable._available = True
        mq_client_unavailable._api_key = None
        with pytest.raises(MenthorQExtractionError, match="No Anthropic API key"):
            mq_client_unavailable.get_cta("2026-03-06")


class TestMenthorQSanitizeText:
    def test_collapse_whitespace(self):
        from radon.clients.menthorq_client import _sanitize_text

        assert _sanitize_text("  hello   world  ") == "hello world"

    def test_redacts_emails(self):
        from radon.clients.menthorq_client import _sanitize_text

        assert (
            _sanitize_text("contact user@example.com here")
            == "contact [redacted-email] here"
        )

    def test_truncates_long_text(self):
        from radon.clients.menthorq_client import _sanitize_text

        long_text = "a" * 500
        result = _sanitize_text(long_text)
        assert len(result) <= 220

    def test_returns_empty_for_non_string(self):
        from radon.clients.menthorq_client import _sanitize_text

        assert _sanitize_text(123) == ""

    def test_returns_empty_for_empty_string(self):
        from radon.clients.menthorq_client import _sanitize_text

        assert _sanitize_text("") == ""


class TestMenthorQParseForexText:
    def test_parses_single_pair(self):
        from radon.clients.menthorq_client import _parse_forex_text

        text = "$EURUSD: Call Resistance, 1.19602, Put Support, 1.16113"
        result = _parse_forex_text(text)
        assert len(result) == 1
        assert result[0]["pair"] == "EURUSD"
        assert result[0]["call_resistance"] == 1.19602
        assert result[0]["put_support"] == 1.16113

    def test_parses_multiple_pairs(self):
        from radon.clients.menthorq_client import _parse_forex_text

        text = "$EURUSD: Level, 1.19 $GBPUSD: Level, 1.35"
        result = _parse_forex_text(text)
        assert len(result) == 2
        assert result[0]["pair"] == "EURUSD"
        assert result[1]["pair"] == "GBPUSD"

    def test_returns_empty_for_empty_text(self):
        from radon.clients.menthorq_client import _parse_forex_text

        assert _parse_forex_text("") == []
        assert _parse_forex_text("   ") == []

    def test_skips_segments_without_colon(self):
        from radon.clients.menthorq_client import _parse_forex_text

        text = "$no_colon_segment $EURUSD: Val, 1.5"
        result = _parse_forex_text(text)
        assert len(result) == 1
        assert result[0]["pair"] == "EURUSD"


class TestMenthorQExceptionHierarchy:
    def test_base_error(self):
        from radon.clients.menthorq_client import MenthorQError

        err = MenthorQError("test")
        assert str(err) == "test"

    def test_auth_error_inherits(self):
        from radon.clients.menthorq_client import (
            MenthorQAuthError,
            MenthorQError,
        )

        err = MenthorQAuthError("auth fail")
        assert isinstance(err, MenthorQError)

    def test_not_found_error_inherits(self):
        from radon.clients.menthorq_client import (
            MenthorQError,
            MenthorQNotFoundError,
        )

        err = MenthorQNotFoundError("missing")
        assert isinstance(err, MenthorQError)

    def test_extraction_error_inherits(self):
        from radon.clients.menthorq_client import (
            MenthorQError,
            MenthorQExtractionError,
        )

        err = MenthorQExtractionError("parse fail")
        assert isinstance(err, MenthorQError)


class TestMenthorQConstants:
    def test_cta_slugs_has_expected_keys(self):
        from radon.clients.menthorq_client import CTA_SLUGS

        assert "main" in CTA_SLUGS
        assert "index" in CTA_SLUGS
        assert "commodity" in CTA_SLUGS
        assert "currency" in CTA_SLUGS

    def test_screener_slugs_has_expected_categories(self):
        from radon.clients.menthorq_client import SCREENER_SLUGS

        expected = {
            "gamma",
            "gamma_levels",
            "open_interest",
            "volatility",
            "volume",
            "qscore",
        }
        assert set(SCREENER_SLUGS.keys()) == expected

    def test_summary_categories(self):
        from radon.clients.menthorq_client import SUMMARY_CATEGORIES

        assert {"futures", "cryptos"} == SUMMARY_CATEGORIES

    def test_dashboard_commands(self):
        from radon.clients.menthorq_client import DASHBOARD_COMMANDS

        assert "eod" in DASHBOARD_COMMANDS
        assert "cta" in DASHBOARD_COMMANDS
        assert "vol" in DASHBOARD_COMMANDS
