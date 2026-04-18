from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from api.services.job_manager import JobManager
    from api.services.storage import FilesystemResultStorage


async def test_health_endpoint_returns_200(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert data["redis"] == "connected"


async def test_analyze_creates_job_returns_202(client):
    mock_tag = MagicMock()
    mock_tag.propagate.return_value = ({"final_trade_decision": "BUY"}, "BUY")
    with patch(
        "tradingagents.graph.trading_graph.TradingAgentsGraph", return_value=mock_tag
    ):
        resp = await client.post(
            "/api/analyze", json={"ticker": "AAPL", "trade_date": "2024-01-15"}
        )

    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    assert data["ticker"] == "AAPL"
    assert data["trade_date"] == "2024-01-15"


async def test_analyze_rejects_empty_ticker(client):
    resp = await client.post(
        "/api/analyze", json={"ticker": "", "trade_date": "2024-01-15"}
    )
    assert resp.status_code == 422


async def test_get_job_status_200(client):
    mgr: JobManager = client._transport.app.state.job_manager
    await mgr.create_job("status-ok", "AAPL", "2024-01-15")

    resp = await client.get("/api/jobs/status-ok")
    assert resp.status_code == 200
    assert resp.json()["job_id"] == "status-ok"
    assert resp.json()["trade_date"] == "2024-01-15"


async def test_get_job_status_404(client):
    resp = await client.get("/api/jobs/nonexistent")
    assert resp.status_code == 404


async def test_get_job_result_200(client, fake_redis_async, tmp_results_dir):
    mgr: JobManager = client._transport.app.state.job_manager
    storage: FilesystemResultStorage = client._transport.app.state.storage

    await mgr.create_job("res-ok", "AAPL", "2024-01-15")
    await mgr.update_status("res-ok", "completed")
    await storage.save("res-ok", {"decision": "BUY"})

    resp = await client.get("/api/jobs/res-ok/result")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["result"]["decision"] == "BUY"


async def test_get_job_result_409(client):
    mgr: JobManager = client._transport.app.state.job_manager
    await mgr.create_job("res-run", "AAPL", "2024-01-15")
    await mgr.update_status("res-run", "running")

    resp = await client.get("/api/jobs/res-run/result")
    assert resp.status_code == 409


async def test_get_job_result_404(client):
    resp = await client.get("/api/jobs/no-result/result")
    assert resp.status_code == 404


async def test_stream_job_returns_event_stream(client):
    mgr: JobManager = client._transport.app.state.job_manager
    await mgr.create_job("stream-1", "AAPL", "2024-01-15")

    mock_tag = MagicMock()
    mock_tag.propagate.return_value = ({"final_trade_decision": "BUY"}, "BUY")
    mock_tag.propagator.create_initial_state.return_value = {"ticker": "AAPL"}
    mock_tag.propagator.get_graph_args.return_value = {}
    mock_tag.graph.stream.return_value = iter([
        {"market_report": "bullish", "final_trade_decision": "BUY"},
    ])

    with patch(
        "tradingagents.graph.trading_graph.TradingAgentsGraph", return_value=mock_tag
    ):
        resp = await client.get("/api/jobs/stream-1/stream")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


async def test_stream_job_404(client):
    resp = await client.get("/api/jobs/no-stream/stream")
    assert resp.status_code == 404
