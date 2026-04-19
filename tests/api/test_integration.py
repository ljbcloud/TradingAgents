from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from api.services.job_manager import JobManager


async def test_full_flow_analyze_poll_result(client):
    mock_tag = MagicMock()
    mock_tag.propagate.return_value = ({"final_trade_decision": "BUY"}, "BUY")
    with patch("graph.trading_graph.TradingAgentsGraph", return_value=mock_tag):
        analyze_resp = await client.post(
            "/api/analyze",
            json={"ticker": "MSFT", "asset_type": "stock", "trade_date": "2024-01-15"},
        )
        assert analyze_resp.status_code == 202
        job_id = analyze_resp.json()["job_id"]
        assert analyze_resp.json()["trade_date"] == "2024-01-15"

        mgr: JobManager = client._transport.app.state.job_manager

        for _ in range(20):
            await asyncio.sleep(0.05)
            job = await mgr.get_job(job_id)
            if job and job["status"] in {"completed", "failed"}:
                break

        status_resp = await client.get(f"/api/jobs/{job_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["job_id"] == job_id

        result_resp = await client.get(f"/api/jobs/{job_id}/result")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"] == "completed"
        assert data["result"]["decision"] == "BUY"


async def test_sse_stream_flow(client):
    mock_tag = MagicMock()
    mock_tag.propagate.return_value = ({"final_trade_decision": "SELL"}, "SELL")
    mock_tag.propagator.create_initial_state.return_value = {"ticker": "GOOG"}
    mock_tag.propagator.get_graph_args.return_value = {}
    mock_tag.graph.stream.return_value = iter([
        {"market_report": "bearish", "final_trade_decision": "SELL"},
    ])

    analyze_resp = await client.post(
        "/api/analyze", json={"ticker": "GOOG", "trade_date": "2024-01-15"}
    )
    assert analyze_resp.status_code == 202
    job_id = analyze_resp.json()["job_id"]

    with patch("graph.trading_graph.TradingAgentsGraph", return_value=mock_tag):
        stream_resp = await client.get(f"/api/jobs/{job_id}/stream")
    assert stream_resp.status_code == 200

    body = stream_resp.text
    assert "data:" in body or "data: " in body
