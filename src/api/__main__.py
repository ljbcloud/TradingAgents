"""Entry point for ``python -m api``."""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",  # noqa: S104  # nosec B104
        port=8000,
        reload=True,
    )
