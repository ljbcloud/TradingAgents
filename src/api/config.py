from __future__ import annotations

import os


class Settings:
    """API configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.results_dir: str = os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results")
        self.max_workers: int = int(os.getenv("API_MAX_WORKERS", "3"))
        self.job_ttl: int = int(os.getenv("API_JOB_TTL", "86400"))


settings = Settings()
