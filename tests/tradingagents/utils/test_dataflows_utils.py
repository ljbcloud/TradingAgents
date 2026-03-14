from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from tradingagents.dataflows.utils import (
    decorate_all_methods,
    get_current_date,
    get_next_weekday,
    save_output,
)


def test_get_current_date_format():
    result = get_current_date()
    assert len(result) == 10
    assert result[4] == "-"
    assert result[7] == "-"


def test_get_current_date_is_today():
    result = get_current_date()
    today = datetime.now().strftime("%Y-%m-%d")
    assert result == today


def test_get_next_weekday_handles_friday():
    result = get_next_weekday("2024-01-12")
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 12


def test_get_next_weekday_handles_monday():
    result = get_next_weekday("2024-01-08")
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 8


def test_get_next_weekday_handles_sunday():
    result = get_next_weekday("2024-01-14")
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_get_next_weekday_handles_wednesday():
    result = get_next_weekday("2024-01-10")
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 10


def test_get_next_weekday_invalid_format():
    with pytest.raises(ValueError):
        get_next_weekday("2024-01-32")


def test_save_output_with_path(tmp_path, sample_stock_data):
    output_path = tmp_path / "test_output.csv"
    save_output(sample_stock_data, "test_tag", output_path)
    assert output_path.exists()
    saved = pd.read_csv(output_path)
    assert len(saved) == len(sample_stock_data)
    assert "close" in saved.columns
    assert "volume" in saved.columns


def test_save_output_without_path(sample_stock_data):
    result = save_output(sample_stock_data, "test_tag", None)
    assert result is None


def test_save_output_empty_dataframe(tmp_path):
    empty_df = pd.DataFrame()
    output_path = tmp_path / "empty.csv"
    save_output(empty_df, "empty_tag", output_path)
    assert output_path.exists()
