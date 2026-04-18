from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import StreamingResponse

from api.models.schemas import JobResponse, JobResult, JobStatus
from api.services.analysis_runner import AnalysisRunner
from api.services.job_manager import JobManager
from api.services.storage import FilesystemResultStorage

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

router = APIRouter(tags=["jobs"])


def get_job_manager(request: Request) -> JobManager:
    return request.app.state.job_manager


def get_runner(request: Request) -> AnalysisRunner:
    return request.app.state.runner


def get_storage(request: Request) -> FilesystemResultStorage:
    return request.app.state.storage


JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
RunnerDep = Annotated[AnalysisRunner, Depends(get_runner)]
StorageDep = Annotated[FilesystemResultStorage, Depends(get_storage)]


def _job_not_found(job_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Job {job_id} not found")


def _build_job_response(job: dict) -> JobResponse:
    return JobResponse(
        job_id=job["job_id"],
        status=JobStatus(job["status"]),
        created_at=datetime.fromisoformat(job["created_at"]),
        ticker=job["ticker"],
        trade_date=job["trade_date"],
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    job_manager: JobManagerDep,
) -> JobResponse:
    job = await job_manager.get_job(job_id)
    if job is None:
        raise _job_not_found(job_id)
    return _build_job_response(job)


@router.get("/jobs/{job_id}/result", response_model=JobResult)
async def get_job_result(
    job_id: str,
    job_manager: JobManagerDep,
    storage: StorageDep,
) -> JobResult:
    job = await job_manager.get_job(job_id)
    if job is None:
        raise _job_not_found(job_id)

    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is {job['status']}, not completed",
        )

    result = await storage.load(job_id)
    return JobResult(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        result=result,
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job(
    job_id: str,
    job_manager: JobManagerDep,
    runner: RunnerDep,
) -> StreamingResponse:
    job = await job_manager.get_job(job_id)
    if job is None:
        raise _job_not_found(job_id)

    if job["status"] == "completed":
        final_event = json.dumps({
            "node": "complete",
            "status": "completed",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })

        async def _single_event() -> AsyncGenerator[str, None]:  # noqa: RUF029
            yield f"data: {final_event}\n\n"

        return StreamingResponse(_single_event(), media_type="text/event-stream")

    return StreamingResponse(
        runner.stream_analysis(job_id, job["ticker"], job["trade_date"]),
        media_type="text/event-stream",
    )
