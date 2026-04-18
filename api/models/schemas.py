from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalyzeRequest(BaseModel):
    ticker: str = Field(min_length=1, description="Stock or crypto ticker symbol")
    asset_type: Literal["stock", "crypto"] = "stock"
    trade_date: str = Field(
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Analysis date in YYYY-MM-DD format",
    )


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    ticker: str
    trade_date: str


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    result: dict | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    redis: str = "connected"
