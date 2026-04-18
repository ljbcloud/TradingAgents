from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from api.models.schemas import HealthResponse
from api.services.job_manager import JobManager

router = APIRouter(tags=["health"])


def get_job_manager(request: Request) -> JobManager:
    return request.app.state.job_manager


JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]


@router.get("/health", response_model=HealthResponse)
async def health_check(job_manager: JobManagerDep) -> HealthResponse:
    redis_status = "connected"
    try:
        await job_manager._redis.ping()
    except Exception:
        redis_status = "disconnected"
    return HealthResponse(status="healthy", version="0.1.0", redis=redis_status)
