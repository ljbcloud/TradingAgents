from __future__ import annotations

from unittest.mock import MagicMock, patch

from api.services.analysis_runner import AnalysisRunner
from api.services.job_manager import JobManager
from api.services.storage import FilesystemResultStorage


async def test_start_analysis_success(fake_redis_async, tmp_results_dir):
    mgr = JobManager(fake_redis_async)
    storage = FilesystemResultStorage(results_dir=str(tmp_results_dir))
    runner = AnalysisRunner(mgr, storage, max_workers=1)

    await mgr.create_job("run-1", "AAPL", "2024-01-15")

    mock_tag = MagicMock()
    mock_tag.propagate.return_value = ({"final_trade_decision": "BUY"}, "BUY")
    with patch("graph.trading_graph.TradingAgentsGraph", return_value=mock_tag):
        await runner.start_analysis("run-1", "AAPL", "2024-01-15")

    job = await mgr.get_job("run-1")
    assert job["status"] == "completed"

    result = await storage.load("run-1")
    assert result is not None
    assert result["decision"] == "BUY"


async def test_start_analysis_failure(fake_redis_async, tmp_results_dir):
    mgr = JobManager(fake_redis_async)
    storage = FilesystemResultStorage(results_dir=str(tmp_results_dir))
    runner = AnalysisRunner(mgr, storage, max_workers=1)

    await mgr.create_job("run-2", "MSFT", "2024-01-15")

    mock_tag = MagicMock()
    mock_tag.propagate.side_effect = RuntimeError("LLM unavailable")
    with patch("graph.trading_graph.TradingAgentsGraph", return_value=mock_tag):
        await runner.start_analysis("run-2", "MSFT", "2024-01-15")

    job = await mgr.get_job("run-2")
    assert job["status"] == "failed"


async def test_job_status_transitions(fake_redis_async, tmp_results_dir):
    mgr = JobManager(fake_redis_async)
    await mgr.create_job("trans-1", "GOOG", "2024-01-15")

    job = await mgr.get_job("trans-1")
    assert job["status"] == "pending"

    await mgr.update_status("trans-1", "running")
    job = await mgr.get_job("trans-1")
    assert job["status"] == "running"

    await mgr.update_status("trans-1", "completed")
    job = await mgr.get_job("trans-1")
    assert job["status"] == "completed"
