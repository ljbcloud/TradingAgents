from __future__ import annotations

import pathlib  # noqa: TC003
from unittest.mock import MagicMock

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def fake_redis() -> fakeredis.FakeRedis:
    """Synchronous FakeRedis instance for unit testing the job manager."""
    return fakeredis.FakeRedis()


@pytest.fixture
def fake_redis_async() -> fakeredis.aioredis.FakeRedis:
    """Async FakeRedis instance for integration tests."""
    return fakeredis.aioredis.FakeRedis()


@pytest.fixture
def tmp_results_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Temporary results directory for FilesystemResultStorage tests."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    return results_dir


@pytest.fixture
async def client(fake_redis_async, tmp_results_dir):
    """Async HTTP test client wired to fake Redis and tmp storage."""
    from api.main import app
    from api.services.analysis_runner import AnalysisRunner
    from api.services.job_manager import JobManager
    from api.services.storage import FilesystemResultStorage

    job_manager = JobManager(fake_redis_async)
    storage = FilesystemResultStorage(results_dir=str(tmp_results_dir))
    runner = AnalysisRunner(job_manager, storage, max_workers=1)

    app.state.job_manager = job_manager
    app.state.runner = runner
    app.state.storage = storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_job_id() -> str:
    """Consistent test job ID across API tests."""
    return "test-job-123"


@pytest.fixture
def sample_analyze_request() -> dict:
    """Sample analysis request payload."""
    return {"ticker": "AAPL", "asset_type": "stock", "trade_date": "2024-01-15"}


@pytest.fixture
def mock_tag():
    """Mock TradingAgentsGraph that returns a successful result."""
    tag = MagicMock()
    tag.propagate.return_value = ({"final_trade_decision": "BUY"}, "BUY")
    tag.propagator.create_initial_state.return_value = {"ticker": "AAPL"}
    return tag


@pytest.fixture
def mock_tag_stream():
    """Mock TradingAgentsGraph with stream support."""
    tag = MagicMock()
    tag.propagate.return_value = ({"final_trade_decision": "BUY"}, "BUY")
    tag.propagator.create_initial_state.return_value = {"ticker": "AAPL"}
    tag.propagator.get_graph_args.return_value = {}
    tag.graph.stream.return_value = iter([
        {"market_report": "bullish", "final_trade_decision": "BUY"},
    ])
    return tag
