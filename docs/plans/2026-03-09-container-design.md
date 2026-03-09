# Container Design for TradingAgents

**Date:** 2026-03-09
**Status:** Approved
**Approach:** Multi-stage Dockerfile + Docker Compose

## Overview

This document outlines the containerization strategy for TradingAgents, supporting both local development (TUI) and production deployments (Web UI) with a unified container image.

## Requirements

- Support both local development and production deployments with the same container
- Web interface support via Chainlit
- Separate Redis container for caching/state management
- Configuration via environment variables (no .env files in container)
- Python 3.13 with Conda (per README)
- Multi-stage build for optimization
- Exclusive interface modes (TUI or Web UI, not both simultaneously)

## Architecture

### Services

#### 1. App Service
Multi-stage Python 3.13 container built with Miniconda.

**Stages:**
- **Base Stage:** Miniconda base, create conda environment with Python 3.13, install dependencies
- **Runtime Stage:** Copy conda environment and application code, non-root user, expose port 8501

**Entry Point:** `docker/docker-entrypoint.sh`
- Checks `APP_MODE` environment variable
- `tui` → Runs `python -m cli.main`
- `web` → Runs `chainlit run cli/web.py --host 0.0.0.0 --port 8501`

#### 2. Redis Service
Official Redis 7.2 Alpine image for caching and state management.

### Directory Structure

```
TradingAgents/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-entrypoint.sh
│   ├── .dockerignore
│   └── docker.env.example
├── cli/
│   ├── main.py (existing TUI)
│   └── web.py (new Chainlit wrapper)
└── ... (existing files)
```

## Implementation Details

### Multi-Stage Build

**Stage 1: Base**
```dockerfile
FROM condaforge/miniconda3:latest AS base
WORKDIR /app
COPY pyproject.toml requirements.txt uv.lock ./
RUN conda create -n tradingagents python=3.13 && \
    conda run -n tradingagents pip install -r requirements.txt
```

**Stage 2: Runtime**
```dockerfile
FROM base AS runtime
COPY --from=base /opt/conda /opt/conda
COPY . /app
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
WORKDIR /app
ENV PATH="/opt/conda/envs/tradingagents/bin:$PATH"
```

### Docker Compose Configuration

**App Service:**
- Build from `docker/Dockerfile`
- Environment: `APP_MODE`, `REDIS_HOST`, `REDIS_PORT`, API keys
- Ports: 8501:8501 (Web UI)
- Depends on: redis
- Health check: Port 8501 listening check
- Volumes: Optional for development (code hot-reload)
- Networks: Custom network

**Redis Service:**
- Image: `redis:7.2-alpine`
- Ports: 6379:6379 (local dev access)
- Networks: Custom network

### Web UI Implementation

**New File:** `cli/web.py`
- Wraps existing `TradingAgentsGraph` class
- Chainlit chat interface for:
  - Ticker selection
  - Date input
  - Model configuration
  - Result display (tables, charts, markdown)
- Shares configuration logic with TUI

### Environment Variables

**Required:**
- `APP_MODE` (tui/web) - Controls interface launch
- `REDIS_HOST` (default: redis)
- `REDIS_PORT` (default: 6379)
- `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `OPENROUTER_API_KEY`
- `ALPHA_VANTAGE_API_KEY`

### Health Check

Implemented via Docker Compose health check:
```yaml
healthcheck:
  test: ["CMD", "nc", "-z", "localhost", "8501"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Usage Examples

### Local Development (TUI)
```bash
docker compose run --rm -it app
```

### Local Development (Web UI)
```bash
APP_MODE=web docker compose up
```

### Production
```bash
APP_MODE=web docker compose -f docker/docker-compose.yml up -d
```

## Security Considerations

- Non-root user for app container
- No .env files in container (environment variables only)
- Minimal base images (Miniconda, Redis Alpine)
- Health checks for monitoring
- Proper signal handling

## New Files Required

1. `docker/Dockerfile` - Multi-stage build definition
2. `docker/docker-compose.yml` - Service orchestration
3. `docker/docker-entrypoint.sh` - Mode selection script
4. `cli/web.py` - Chainlit web UI wrapper
5. `docker/.dockerignore` - Exclude unnecessary files
6. `docker/docker.env.example` - Example environment variables

## Benefits

- **Dual mode support** - TUI for development, Web UI for production
- **Optimized builds** - Multi-stage for minimal production images
- **Clean architecture** - Separate Redis service
- **Environment-based configuration** - No .env files in container
- **Compliant with README** - Python 3.13 with Conda
- **Organized structure** - Docker files in `docker/` subdirectory
