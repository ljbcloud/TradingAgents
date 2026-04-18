from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.models.schemas import (
    AnalyzeRequest,
    HealthResponse,
    JobResponse,
    JobResult,
    JobStatus,
)


def test_valid_analyze_request():
    req = AnalyzeRequest(ticker="AAPL", asset_type="stock", trade_date="2024-01-15")
    assert req.ticker == "AAPL"
    assert req.asset_type == "stock"
    assert req.trade_date == "2024-01-15"


def test_analyze_request_default_asset_type():
    req = AnalyzeRequest(ticker="MSFT", trade_date="2024-01-15")
    assert req.asset_type == "stock"


def test_analyze_request_empty_ticker_rejected():
    with pytest.raises(ValidationError):
        AnalyzeRequest(ticker="", trade_date="2024-01-15")


def test_analyze_request_invalid_asset_type_rejected():
    with pytest.raises(ValidationError):
        AnalyzeRequest(ticker="AAPL", asset_type="bond", trade_date="2024-01-15")


def test_analyze_request_invalid_trade_date_rejected():
    with pytest.raises(ValidationError):
        AnalyzeRequest(ticker="AAPL", trade_date="01-15-2024")


def test_analyze_request_missing_trade_date_rejected():
    with pytest.raises(ValidationError):
        AnalyzeRequest(ticker="AAPL")


def test_analyze_request_trade_date_format():
    req = AnalyzeRequest(ticker="AAPL", trade_date="2025-06-30")
    assert req.trade_date == "2025-06-30"


def test_job_status_enum_values():
    assert JobStatus.PENDING == "pending"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert len(JobStatus) == 4


def test_health_response_defaults():
    resp = HealthResponse(version="1.0")
    assert resp.status == "healthy"
    assert resp.redis == "connected"
    assert resp.version == "1.0"


def test_job_response_serialization():
    from datetime import datetime, timezone

    now = datetime.now(tz=timezone.utc)
    resp = JobResponse(
        job_id="abc",
        status=JobStatus.PENDING,
        created_at=now,
        ticker="TSLA",
        trade_date="2024-01-15",
    )
    data = resp.model_dump()
    assert data["job_id"] == "abc"
    assert data["status"] == JobStatus.PENDING
    assert data["ticker"] == "TSLA"
    assert data["trade_date"] == "2024-01-15"


def test_job_result_with_optional_fields():
    result = JobResult(job_id="x", status=JobStatus.COMPLETED)
    assert result.result is None
    assert result.error is None

    result_full = JobResult(
        job_id="y",
        status=JobStatus.FAILED,
        error="something broke",
    )
    assert result_full.error == "something broke"
    assert result_full.result is None
