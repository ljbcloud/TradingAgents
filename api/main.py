"""FastAPI application entry point with lifespan-managed services."""

from __future__ import annotations

from contextlib import asynccontextmanager

import redis.asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import analyze, health, jobs
from api.services.analysis_runner import AnalysisRunner
from api.services.job_manager import JobManager
from api.services.storage import FilesystemResultStorage


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = redis.asyncio.ConnectionPool.from_url(settings.redis_url)
    redis_client = redis.asyncio.Redis(connection_pool=pool)
    job_manager = JobManager(redis_client)
    storage = FilesystemResultStorage(results_dir=settings.results_dir)
    runner = AnalysisRunner(job_manager, storage, max_workers=settings.max_workers)
    app.state.job_manager = job_manager
    app.state.runner = runner
    app.state.storage = storage
    yield
    await pool.aclose()


app = FastAPI(title="TradingAgents API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(health.router, prefix="/api")
