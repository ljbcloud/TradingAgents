from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from api.models.schemas import AnalyzeRequest, JobResponse, JobStatus
from api.services.analysis_runner import AnalysisRunner
from api.services.job_manager import JobManager

router = APIRouter(tags=["analyze"])


def get_job_manager(request: Request) -> JobManager:
    return request.app.state.job_manager


def get_runner(request: Request) -> AnalysisRunner:
    return request.app.state.runner


JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
RunnerDep = Annotated[AnalysisRunner, Depends(get_runner)]


@router.post("/analyze", response_model=JobResponse, status_code=202)
async def create_analysis(
    body: AnalyzeRequest,
    request: Request,
    job_manager: JobManagerDep,
    runner: RunnerDep,
) -> JobResponse:
    job_id = str(uuid.uuid4())
    await job_manager.create_job(job_id, body.ticker, body.trade_date)

    # Store reference to prevent garbage collection of the background task
    request.state.background_task = asyncio.create_task(
        runner.start_analysis(job_id, body.ticker, body.trade_date)
    )

    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=datetime.now(tz=timezone.utc),
        ticker=body.ticker,
        trade_date=body.trade_date,
    )
