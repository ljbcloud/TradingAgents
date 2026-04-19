"""Analysis runner that executes TradingAgents in a bounded thread pool."""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from api.services.storage import FilesystemResultStorage

logger = logging.getLogger(__name__)


class AnalysisRunner:
    """Runs TradingAgents analysis jobs in a thread pool.

    Each analysis invocation creates a fresh TradingAgentsGraph instance
    and runs propagate() in a worker thread so the async event loop
    stays responsive.
    """

    def __init__(
        self,
        job_manager,
        storage: FilesystemResultStorage,
        max_workers: int = 3,
    ) -> None:
        # job_manager is injected (duck-typed) — expected interface:
        #   async update_status(job_id, status, error=None)
        self._job_manager = job_manager
        self._storage = storage
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def start_analysis(self, job_id: str, ticker: str, trade_date: str) -> None:
        """Kick off analysis for *ticker* and update job status on completion."""
        await self._job_manager.update_status(job_id, "running")

        loop = asyncio.get_running_loop()
        try:
            final_state, decision = await loop.run_in_executor(
                self._executor,
                self._run_analysis,
                job_id,
                ticker,
                trade_date,
            )
            await self._storage.save(
                job_id, {"final_state": final_state, "decision": decision}
            )
            await self._job_manager.update_status(job_id, "completed")
        except Exception:
            logger.exception("Analysis failed for job_id=%s ticker=%s", job_id, ticker)
            await self._job_manager.update_status(
                job_id, "failed", error="Analysis failed unexpectedly"
            )

    def _run_analysis(
        self, job_id: str, ticker: str, trade_date: str
    ) -> tuple[dict, str]:
        """Synchronous wrapper executed in the thread pool."""
        # Lazy import — TradingAgentsGraph triggers heavy module loading
        from graph.trading_graph import TradingAgentsGraph

        logger.info("Starting analysis job_id=%s ticker=%s", job_id, ticker)
        ta = TradingAgentsGraph()
        result = ta.propagate(ticker, trade_date)
        logger.info("Analysis complete job_id=%s ticker=%s", job_id, ticker)
        return result

    async def stream_analysis(
        self, job_id: str, ticker: str, trade_date: str
    ) -> AsyncGenerator[str, None]:
        """Stream analysis events as SSE-formatted strings.

        Runs ``graph.stream()`` in a worker thread, yielding lightweight
        progress events (``data: {json}\\n\\n``) as each graph node completes.

        On success the final state is persisted via storage and the job is
        marked *completed*.  On failure an error event is yielded and the job
        is marked *failed*.  ``asyncio.CancelledError`` (client disconnect)
        also marks the job as *failed*.
        """
        await self._job_manager.update_status(job_id, "running")

        from graph.trading_graph import TradingAgentsGraph

        ta = TradingAgentsGraph()
        init_state = ta.propagator.create_initial_state(ticker, trade_date)
        args = ta.propagator.get_graph_args()

        queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

        def _run_stream() -> None:
            try:
                last: object = None
                for chunk in ta.graph.stream(init_state, **args):
                    queue.put_nowait(("chunk", chunk))
                    last = chunk
                queue.put_nowait(("done", last))
            except Exception as exc:
                queue.put_nowait(("error", exc))

        stream_task = asyncio.create_task(asyncio.to_thread(_run_stream))

        def _raise_if_error(exc: object) -> None:
            """Re-raise an exception queued from the worker thread."""
            if isinstance(exc, BaseException):
                raise exc

        report_fields = [
            "market_report",
            "sentiment_report",
            "news_report",
            "fundamentals_report",
        ]
        seen_reports: set[str] = set()

        try:
            while True:
                kind, payload = await queue.get()

                if kind == "done":
                    break
                if kind == "error":
                    _raise_if_error(payload)

                state = payload if isinstance(payload, dict) else {}
                node_name = "unknown"
                report_name: str | None = None

                for field in report_fields:
                    if state.get(field) and field not in seen_reports:
                        report_name = field
                        seen_reports.add(field)
                        node_name = field.replace("_report", "")
                        break

                event = {
                    "node": node_name,
                    "status": "completed",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "report_name": report_name,
                }
                yield f"data: {json.dumps(event)}\n\n"

            # Persist result
            if isinstance(payload, dict):
                await self._storage.save(
                    job_id,
                    {
                        "final_state": payload,
                        "decision": payload.get("final_trade_decision", ""),
                    },
                )

            # Final completion event
            final_event = {
                "node": "complete",
                "status": "completed",
                "timestamp": datetime.now(UTC).isoformat(),
                "report_name": None,
            }
            yield f"data: {json.dumps(final_event)}\n\n"
            await self._job_manager.update_status(job_id, "completed")

        except asyncio.CancelledError:
            logger.info("Client disconnected for job_id=%s", job_id)
            stream_task.cancel()
            await self._job_manager.update_status(
                job_id, "failed", error="Client disconnected"
            )

        except Exception:
            logger.exception("Stream failed for job_id=%s ticker=%s", job_id, ticker)
            error_event = {
                "node": "error",
                "status": "failed",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": "Analysis failed unexpectedly",
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            await self._job_manager.update_status(
                job_id, "failed", error="Analysis failed unexpectedly"
            )
