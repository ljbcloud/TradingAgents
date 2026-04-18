"""Redis-backed job state manager for trading analysis jobs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import redis.asyncio

from api.config import settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "job:"


def _job_key(job_id: str) -> str:
    return f"{_KEY_PREFIX}{job_id}"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class JobManager:
    """Manages job lifecycle state in Redis hashes.

    Stores lightweight metadata (status, timestamps, ticker, error) per job.
    Actual analysis results are persisted separately via ResultStorage.
    """

    def __init__(self, redis: redis.asyncio.Redis) -> None:
        self._redis = redis

    async def create_job(self, job_id: str, ticker: str, trade_date: str) -> dict:
        """Create a new job record with status 'pending'.

        Returns the created job dict.
        """
        now = _now_iso()
        job: dict[str, str] = {
            "job_id": job_id,
            "ticker": ticker,
            "trade_date": trade_date,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        try:
            key = _job_key(job_id)
            for field, value in job.items():
                await self._redis.hset(key, field, value)
            await self._redis.expire(key, settings.job_ttl)
        except redis.exceptions.RedisError:
            logger.exception("Failed to create job %s", job_id)
        return job

    async def get_job(self, job_id: str) -> dict | None:
        """Retrieve a job dict by ID, or None if not found."""
        try:
            data = await self._redis.hgetall(_job_key(job_id))
        except redis.exceptions.RedisError:
            logger.exception("Failed to get job %s", job_id)
            return None
        if not data:
            return None
        return {
            k.decode() if isinstance(k, bytes) else k: v.decode()
            if isinstance(v, bytes)
            else v
            for k, v in data.items()
        }

    async def update_status(
        self, job_id: str, status: str, error: str | None = None
    ) -> None:
        """Update job status and updated_at timestamp."""
        fields: dict[str, str] = {
            "status": status,
            "updated_at": _now_iso(),
        }
        if error is not None:
            fields["error"] = error
        try:
            for field, value in fields.items():
                await self._redis.hset(_job_key(job_id), field, value)
        except redis.exceptions.RedisError:
            logger.exception("Failed to update status for job %s", job_id)

    async def store_result(self, job_id: str, result: dict) -> None:
        """Mark job as completed. Actual result payload is NOT stored in Redis."""
        await self.update_status(job_id, "completed")

    async def list_jobs(self, limit: int = 50) -> list[dict]:
        """Return recent jobs, scanning job:* keys."""
        jobs: list[dict] = []
        try:
            cursor: int | bytes = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor, match=f"{_KEY_PREFIX}*", count=limit
                )
                if isinstance(cursor, bytes):
                    cursor = int(cursor)
                for key in keys:
                    raw = await self._redis.hgetall(key)
                    if raw:
                        job = {
                            k.decode() if isinstance(k, bytes) else k: v.decode()
                            if isinstance(v, bytes)
                            else v
                            for k, v in raw.items()
                        }
                        jobs.append(job)
                if cursor == 0:
                    break
                if len(jobs) >= limit:
                    break
        except redis.exceptions.RedisError:
            logger.exception("Failed to list jobs")
        return jobs[:limit]

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job hash. Returns True if the job existed."""
        try:
            deleted = await self._redis.delete(_job_key(job_id))
        except redis.exceptions.RedisError:
            logger.exception("Failed to delete job %s", job_id)
            return False
        return deleted > 0
