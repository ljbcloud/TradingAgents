"""Unit tests for dataflows common utilities."""

import pytest

from dataflows.common import (
    extract_article_data,
    find_column_index,
    parse_csv_data,
    validate_and_parse_date,
)
from dataflows.exceptions import ValidationError


class TestParseCsvData:
    """Tests for CSV parsing utility."""

    def test_parse_simple_csv(self):
        """parse_csv_data should parse simple CSV data."""
        header, rows = parse_csv_data("a,b\n1,2\n3,4")
        assert header == ["a", "b"]
        assert len(rows) == 2
        assert rows[0] == ["1", "2"]
        assert rows[1] == ["3", "4"]

    def test_parse_empty_csv_raises(self):
        """parse_csv_data should raise for empty input."""
        with pytest.raises(ValidationError):
            parse_csv_data("")

    def test_parse_csv_with_header_only(self):
        """parse_csv_data should return empty rows for header-only CSV."""
        header, rows = parse_csv_data("a,b,c")
        assert header == ["a", "b", "c"]
        assert rows == []

    def test_parse_csv_with_multiline(self):
        """parse_csv_data should handle multiline data."""
        header, rows = parse_csv_data("a,b\nc,d\ne,f")
        assert header == ["a", "b"]
        assert len(rows) == 2


class TestFindColumnIndex:
    """Tests for column index finder."""

    def test_find_existing_column(self):
        """find_column_index should return index of existing column."""
        headers = ["time", "open", "high", "low", "close"]
        idx = find_column_index(headers, "close")
        assert idx == 4

    def test_find_missing_column_raises(self):
        """find_column_index should raise ValidationError for missing column."""
        headers = ["time", "value"]
        with pytest.raises(ValidationError, match="not found"):
            find_column_index(headers, "missing")

    def test_find_with_different_case_insensitive(self):
        """find_column_index should find column case-insensitively."""
        headers = ["TIME", "Value"]
        idx = find_column_index(headers, "time", case_sensitive=False)
        assert idx == 0

    def test_find_with_case_sensitive(self):
        """find_column_index should respect case-sensitive search."""
        headers = ["TIME", "time"]
        idx = find_column_index(headers, "time", case_sensitive=True)
        assert idx == 1

    def test_find_returns_first_match(self):
        """find_column_index should return first match for duplicates."""
        headers = ["value", "value", "other"]
        idx = find_column_index(headers, "value")
        assert idx == 0


class TestExtractArticleData:
    """Tests for article data extractor."""

    def test_extract_simple_article(self):
        """extract_article_data should extract basic fields."""
        article = {
            "title": "Test",
            "summary": "Summary",
            "link": "http://example.com",
        }
        result = extract_article_data(article)
        assert result["title"] == "Test"
        assert result["summary"] == "Summary"

    def test_extract_with_content_wrapper(self):
        """extract_article_data should handle content wrapper."""
        article = {"content": {"title": "Nested", "summary": "Nested summary"}}
        result = extract_article_data(article)
        assert result["title"] == "Nested"

    def test_extract_missing_fields_returns_defaults(self):
        """extract_article_data should provide defaults for missing fields."""
        article = {}
        result = extract_article_data(article)
        assert result["title"] == "No title"
        assert result["publisher"] == "Unknown"

    def test_extract_with_nested_content_url(self):
        """extract_article_data should extract URL from nested content."""
        article = {
            "content": {
                "title": "Test",
                "canonicalUrl": {"url": "http://example.com/article"},
            }
        }
        result = extract_article_data(article)
        assert result["link"] == "http://example.com/article"


class TestValidateAndParseDate:
    """Tests for date validation and parsing."""

    def test_valid_iso_date(self):
        """validate_and_parse_date should parse ISO format dates."""
        from datetime import datetime, timezone

        result = validate_and_parse_date("2024-01-15")
        assert result == datetime(2024, 1, 15, tzinfo=timezone.utc).replace(tzinfo=None)

    def test_invalid_format_raises_validation_error(self):
        """validate_and_parse_date should raise ValidationError for invalid format."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_and_parse_date("01/15/2024")

    def test_invalid_date_raises_validation_error(self):
        """validate_and_parse_date should raise ValidationError for invalid date."""
        with pytest.raises(ValidationError):
            validate_and_parse_date("2024-13-45")

    def test_custom_format(self):
        """validate_and_parse_date should accept custom format string."""
        from datetime import datetime, timezone

        result = validate_and_parse_date("15-01-2024", format="%d-%m-%Y")
        assert result == datetime(2024, 1, 15, tzinfo=timezone.utc).replace(tzinfo=None)

    def test_empty_string_raises_validation_error(self):
        """validate_and_parse_date should raise ValidationError for empty string."""
        with pytest.raises(ValidationError):
            validate_and_parse_date("")
