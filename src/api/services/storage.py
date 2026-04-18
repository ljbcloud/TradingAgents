"""Result storage abstraction layer with filesystem implementation."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import pathlib
from typing import Protocol

logger = logging.getLogger(__name__)


class ResultStorage(Protocol):
    """Async result storage contract for job results."""

    async def save(self, job_id: str, data: dict) -> None: ...

    async def load(self, job_id: str) -> dict | None: ...

    async def delete(self, job_id: str) -> None: ...

    async def exists(self, job_id: str) -> bool: ...


def _write_json(path: str, data: dict) -> None:
    with pathlib.Path(path).open("w", encoding="utf-8") as f:
        json.dump(data, f)


def _read_json(path: str) -> dict | None:
    try:
        with pathlib.Path(path).open(encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _remove_file(path: str) -> None:
    with contextlib.suppress(FileNotFoundError):
        pathlib.Path(path).unlink()


def _file_exists(path: str) -> bool:
    return pathlib.Path(path).exists()


class FilesystemResultStorage:
    """Stores results as JSON files in a configurable directory.

    All file I/O is offloaded to threads via asyncio.to_thread().
    """

    def __init__(self, results_dir: str) -> None:
        self.results_dir = results_dir
        pathlib.Path(results_dir).mkdir(exist_ok=True, parents=True)

    def _path(self, job_id: str) -> str:
        return os.path.join(self.results_dir, f"{job_id}.json")

    async def save(self, job_id: str, data: dict) -> None:
        await asyncio.to_thread(_write_json, self._path(job_id), data)

    async def load(self, job_id: str) -> dict | None:
        result = await asyncio.to_thread(_read_json, self._path(job_id))
        if result is None:
            logger.warning("Result not found for job_id=%s", job_id)
        return result

    async def delete(self, job_id: str) -> None:
        await asyncio.to_thread(_remove_file, self._path(job_id))

    async def exists(self, job_id: str) -> bool:
        return await asyncio.to_thread(_file_exists, self._path(job_id))
