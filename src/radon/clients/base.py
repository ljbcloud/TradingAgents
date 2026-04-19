"""Graceful degradation utilities for optional data-client dependencies."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class ClientStatus(StrEnum):
    """Availability status of a data client."""

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


@dataclass
class ClientCheckResult:
    """Result of checking a data client's availability."""

    status: ClientStatus
    message: str
    error: Exception | None = None


def check_optional_dependency(module_name: str) -> bool:
    """Check whether an optional Python module is installed.

    Uses ``importlib.util.find_spec`` so that no ``ImportError`` is raised
    when the module is absent.
    """
    return importlib.util.find_spec(module_name) is not None


@runtime_checkable
class BaseDataClient(Protocol):
    """Protocol that every Radon data client must satisfy."""

    def check_availability(self) -> ClientCheckResult: ...
    def is_available(self) -> bool: ...


__all__ = [
    "BaseDataClient",
    "ClientCheckResult",
    "ClientStatus",
    "check_optional_dependency",
]
