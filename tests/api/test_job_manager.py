from __future__ import annotations

from api.services.job_manager import JobManager


async def test_create_and_get_job(fake_redis_async):
    mgr = JobManager(fake_redis_async)
    job = await mgr.create_job("j-1", "AAPL", "2024-01-15")

    assert job["job_id"] == "j-1"
    assert job["ticker"] == "AAPL"
    assert job["trade_date"] == "2024-01-15"
    assert job["status"] == "pending"

    fetched = await mgr.get_job("j-1")
    assert fetched is not None
    assert fetched["job_id"] == "j-1"
    assert fetched["ticker"] == "AAPL"
    assert fetched["trade_date"] == "2024-01-15"


async def test_get_nonexistent_job_returns_none(fake_redis_async):
    mgr = JobManager(fake_redis_async)
    assert await mgr.get_job("nope") is None


async def test_update_status(fake_redis_async):
    mgr = JobManager(fake_redis_async)
    await mgr.create_job("j-2", "MSFT", "2024-01-15")
    await mgr.update_status("j-2", "running")

    job = await mgr.get_job("j-2")
    assert job["status"] == "running"


async def test_update_status_with_error(fake_redis_async):
    mgr = JobManager(fake_redis_async)
    await mgr.create_job("j-3", "GOOG", "2024-01-15")
    await mgr.update_status("j-3", "failed", error="timeout")

    job = await mgr.get_job("j-3")
    assert job["status"] == "failed"
    assert job["error"] == "timeout"


async def test_store_result_marks_completed(fake_redis_async):
    mgr = JobManager(fake_redis_async)
    await mgr.create_job("j-4", "TSLA", "2024-01-15")
    await mgr.store_result("j-4", {"decision": "SELL"})

    job = await mgr.get_job("j-4")
    assert job["status"] == "completed"


async def test_list_jobs(fake_redis_async):
    mgr = JobManager(fake_redis_async)
    await mgr.create_job("lj-1", "AAPL", "2024-01-15")
    await mgr.create_job("lj-2", "MSFT", "2024-01-15")

    jobs = await mgr.list_jobs()
    ids = {j["job_id"] for j in jobs}
    assert "lj-1" in ids
    assert "lj-2" in ids


async def test_delete_job(fake_redis_async):
    mgr = JobManager(fake_redis_async)
    await mgr.create_job("del-1", "NVDA", "2024-01-15")

    assert await mgr.delete_job("del-1") is True
    assert await mgr.get_job("del-1") is None
    assert await mgr.delete_job("del-1") is False
