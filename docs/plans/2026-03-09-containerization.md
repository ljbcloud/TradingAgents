# Containerization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Containerize TradingAgents with dual-mode support (TUI and Web UI), multi-stage builds, and Docker Compose orchestration.

**Architecture:** Multi-stage Dockerfile using Miniconda base, separate Redis service, environment-based configuration, dual interface modes via entrypoint script.

**Tech Stack:** Docker, Docker Compose, Python 3.13, Conda, Chainlit, Redis 7.2 Alpine

---

## Prerequisites

### Task 0: Verify Environment

**Files:**
- Check: `pyproject.toml`, `requirements.txt`, `README.md`

**Step 1: Verify Python version and dependencies**

Read `README.md` lines 110-116 to confirm Python 3.13 requirement.
Read `pyproject.toml` to verify project configuration.

**Step 2: Verify existing CLI structure**

Read `cli/main.py` to understand current TUI implementation.
Check `requirements.txt` for current dependencies.

**Step 3: Add chainlit dependency**

Edit `requirements.txt`, add at end:

```text
chainlit>=1.0.0
```

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add chainlit dependency for web UI"
```

---

## Task 1: Create Web UI Wrapper

**Files:**
- Create: `cli/web.py`
- Reference: `cli/main.py:1-50`, `tradingagents/graph/trading_graph.py`

**Step 1: Write web UI skeleton**

Create `cli/web.py`:

```python
import chainlit as cl
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
import os
from dotenv import load_dotenv

load_dotenv()

config = DEFAULT_CONFIG.copy()

@cl.on_chat_start
async def start():
    msg = cl.Message(content="Welcome to TradingAgents Web UI!")
    await msg.send()
```

**Step 2: Run to verify it loads**

```bash
python -m cli.web
```

Expected: Chainlit starts without errors

**Step 3: Add configuration UI**

Replace content with:

```python
import chainlit as cl
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients.constants import LLMProvider
import os
from dotenv import load_dotenv

load_dotenv()

async def get_config():
    """Get configuration from user input"""
    ticker = await cl.AskUserMessage(
        content="Enter stock ticker (e.g., NVDA)",
        timeout=300
    ).send()
    
    date = await cl.AskUserMessage(
        content="Enter analysis date (YYYY-MM-DD)",
        timeout=300
    ).send()
    
    provider = await cl.AskOptionMessage(
        content="Select LLM provider",
        options=[
            cl.Option("openai", "OpenAI (GPT)"),
            cl.Option("google", "Google (Gemini)"),
            cl.Option("anthropic", "Anthropic (Claude)"),
            cl.Option("xai", "xAI (Grok)"),
            cl.Option("openrouter", "OpenRouter"),
            cl.Option("ollama", "Ollama (local)"),
        ],
        timeout=300
    ).send()
    
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = provider.get("value")
    
    return {
        "ticker": ticker.get("output"),
        "date": date.get("output"),
        "config": config
    }

@cl.on_message
async def main(message: cl.Message):
    """Main analysis handler"""
    config_data = await get_config()
    
    # Show configuration
    await cl.Message(
        content=f"**Configuration:**\n"
        f"- Ticker: {config_data['ticker']}\n"
        f"- Date: {config_data['date']}\n"
        f"- Provider: {config_data['config']['llm_provider']}"
    ).send()
    
    # Create graph
    ta = TradingAgentsGraph(debug=False, config=config_data["config"])
    
    # Run analysis
    with cl.Step(name="Running analysis") as step:
        try:
            result, decision = ta.propagate(
                config_data["ticker"],
                config_data["date"]
            )
            step.output = "Analysis complete!"
        except Exception as e:
            step.output = f"Error: {str(e)}"
            await cl.Message(content=f"Error: {str(e)}").send()
            return
    
    # Display results
    await cl.Message(
        content=f"**Decision:** {decision}"
    ).send()

@cl.on_chat_start
async def start():
    msg = cl.Message(
        content="# TradingAgents Web UI\n\n"
        "Enter a stock ticker to start analysis."
    )
    await msg.send()
```

**Step 4: Test web UI locally**

```bash
chainlit run cli/web.py --host 0.0.0.0 --port 8501
```

Expected: Web UI accessible at http://localhost:8501

**Step 5: Commit**

```bash
git add cli/web.py
git commit -m "feat: add Chainlit web UI wrapper"
```

---

## Task 2: Create Docker Entry Point

**Files:**
- Create: `docker/docker-entrypoint.sh`

**Step 1: Create entry point script**

Create `docker/docker-entrypoint.sh`:

```bash
#!/bin/bash
set -e

# Function to handle signals
cleanup() {
    echo "Shutting down..."
    exit 0
}

trap cleanup SIGTERM SIGINT

# Determine mode based on APP_MODE variable
if [ "$APP_MODE" = "web" ]; then
    echo "Starting Web UI mode..."
    exec chainlit run cli/web.py --host 0.0.0.0 --port 8501
else
    echo "Starting TUI mode..."
    exec python -m cli.main
fi
```

**Step 2: Make script executable**

```bash
chmod +x docker/docker-entrypoint.sh
```

**Step 3: Commit**

```bash
git add docker/docker-entrypoint.sh
git commit -m "chore: add Docker entry point script with mode selection"
```

---

## Task 3: Create Multi-Stage Dockerfile

**Files:**
- Create: `docker/Dockerfile`
- Reference: `README.md:110-116`, `pyproject.toml`

**Step 1: Create base stage**

Create `docker/Dockerfile`:

```dockerfile
# Base stage with conda environment
FROM condaforge/miniconda3:latest AS base

WORKDIR /app

# Copy dependency files
COPY pyproject.toml requirements.txt uv.lock ./

# Create conda environment with Python 3.13
RUN conda create -n tradingagents python=3.13 -y && \
    echo "source activate tradingagents" > ~/.bashrc

# Activate environment and install dependencies
SHELL ["conda", "run", "-n", "tradingagents", "/bin/bash", "-c"]
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM base AS runtime

WORKDIR /app

# Copy conda environment from base stage
COPY --from=base /opt/conda /opt/conda

# Copy application code
COPY . /app

# Copy entry point script
COPY docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /opt/conda

# Set up environment
ENV PATH="/opt/conda/envs/tradingagents/bin:$PATH"
ENV CONDA_DEFAULT_ENV=tradingagents

# Switch to non-root user
USER appuser
WORKDIR /app

# Expose web UI port
EXPOSE 8501

# Set entry point
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
```

**Step 2: Test Docker build**

```bash
cd docker && docker build -f Dockerfile -t tradingagents:test .
```

Expected: Build completes successfully

**Step 3: Verify TUI mode works**

```bash
docker run --rm -it tradingagents:test
```

Expected: TUI starts in interactive mode

**Step 4: Verify web mode works**

```bash
docker run --rm -e APP_MODE=web -p 8501:8501 tradingagents:test
```

Expected: Web UI accessible at http://localhost:8501

**Step 5: Commit**

```bash
git add docker/Dockerfile
git commit -m "feat: add multi-stage Dockerfile with Python 3.13 conda"
```

---

## Task 4: Create Docker Compose Configuration

**Files:**
- Create: `docker/docker-compose.yml`

**Step 1: Create docker-compose file**

Create `docker/docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7.2-alpine
    container_name: tradingagents-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - tradingagents-network

  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: tradingagents-app
    environment:
      - APP_MODE=${APP_MODE:-tui}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - XAI_API_KEY=${XAI_API_KEY:-}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
      - ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY:-}
    ports:
      - "8501:8501"
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "nc -z localhost 8501 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - tradingagents-network
    stdin_open: true
    tty: true

networks:
  tradingagents-network:
    driver: bridge
```

**Step 2: Test TUI mode with compose**

```bash
cd docker && docker compose run --rm app
```

Expected: TUI starts with Redis connection available

**Step 3: Test web mode with compose**

```bash
cd docker && APP_MODE=web docker compose up
```

Expected: Web UI accessible at http://localhost:8501

**Step 4: Test health checks**

```bash
docker compose ps
```

Expected: Both services show "healthy" status

**Step 5: Commit**

```bash
git add docker/docker-compose.yml
git commit -m "feat: add Docker Compose configuration with Redis service"
```

---

## Task 5: Create Docker Ignore File

**Files:**
- Create: `docker/.dockerignore`

**Step 1: Create dockerignore file**

Create `docker/.dockerignore`:

```text
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Environment
.env
.envrc
.venv
env/
venv/
ENV/

# Development
.git/
.gitignore
docs/
reports/
results/
.vscode/
.idea/
*.log

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Tests
.pytest_cache/
.coverage
htmlcov/
.tox/

# Cache
*.rdb
*.aof
**/data_cache/

# Lock files (optional - include if you want reproducible builds)
# uv.lock
```

**Step 2: Verify build size reduction**

```bash
docker images | grep tradingagents
```

Expected: Image size < 2GB

**Step 3: Commit**

```bash
git add docker/.dockerignore
git commit -m "chore: add dockerignore to reduce build context"
```

---

## Task 6: Create Environment Variables Example

**Files:**
- Create: `docker/docker.env.example`

**Step 1: Create example env file**

Create `docker/docker.env.example`:

```bash
# Application Mode
# tui: Terminal UI for local development
# web: Web UI for production
APP_MODE=web

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# LLM Provider API Keys
# Set only the provider(s) you intend to use
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
XAI_API_KEY=your_xai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Data Source API Key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
```

**Step 2: Commit**

```bash
git add docker/docker.env.example
git commit -m "chore: add example environment variables file"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `README.md`
- Create: `docs/CONTAINERIZATION.md`

**Step 1: Add containerization section to README**

Edit `README.md`, add after "Installation and CLI" section (after line 160):

```markdown
## Containerization

### Quick Start

Build and run with Docker Compose:

```bash
# Web UI mode
cd docker
APP_MODE=web docker compose up

# TUI mode
docker compose run --rm app
```

### Building the Container

```bash
cd docker
docker build -f Dockerfile -t tradingagents:latest ..
```

### Configuration

Copy the example environment file and configure your API keys:

```bash
cd docker
cp docker.env.example docker.env
# Edit docker.env with your API keys
```

Load environment variables:

```bash
set -a
source docker.env
set +a
```

### Environment Variables

- `APP_MODE`: Interface mode (`tui` or `web`)
- `REDIS_HOST`: Redis host (default: `redis`)
- `REDIS_PORT`: Redis port (default: `6379`)
- LLM API keys: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.
- `ALPHA_VANTAGE_API_KEY`: Data source key

See `docker/docker.env.example` for all available variables.

### Development with Hot Reload

For development with code hot-reload, modify `docker-compose.yml` to mount source:

```yaml
volumes:
  - ../:/app
```

Then rebuild and restart.
```

**Step 2: Create detailed containerization guide**

Create `docs/CONTAINERIZATION.md`:

```markdown
# Containerization Guide

## Overview

TradingAgents supports containerized deployment with both TUI and Web UI modes.

## Architecture

- **Multi-stage build**: Minimizes production image size
- **Dual mode**: TUI for development, Web UI for production
- **Separate Redis**: Caching and state management
- **Environment-based**: All configuration via environment variables

## Quick Start

### Web UI Mode

```bash
cd docker
export OPENAI_API_KEY=your_key
export ALPHA_VANTAGE_API_KEY=your_key
APP_MODE=web docker compose up
```

Access at: http://localhost:8501

### TUI Mode

```bash
cd docker
export OPENAI_API_KEY=your_key
export ALPHA_VANTAGE_API_KEY=your_key
docker compose run --rm app
```

## Configuration

### Using Environment File

```bash
cd docker
cp docker.env.example .env
# Edit .env with your keys
docker compose up
```

### Using Shell Variables

```bash
export APP_MODE=web
export OPENAI_API_KEY=sk-...
export ALPHA_VANTAGE_API_KEY=...
docker compose up
```

## Development

### Hot Reload

For development with code hot-reload, add to `docker-compose.yml`:

```yaml
volumes:
  - ../:/app
```

### Debug Mode

Enable debug logging:

```bash
docker compose run --rm -e DEBUG=true app
```

### Running Tests

```bash
docker compose run --rm app pytest
```

## Production

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

### Health Checks

Health checks are configured for both services:

- App: Checks port 8501
- Redis: Checks `redis-cli ping`

View status:

```bash
docker compose ps
```

### Scaling

Redis can be scaled horizontally. App state is externalized to Redis.

## Troubleshooting

### Container won't start

Check logs:

```bash
docker compose logs app
docker compose logs redis
```

### Redis connection failed

Ensure Redis is healthy:

```bash
docker compose ps redis
```

### Web UI not accessible

Check port binding:

```bash
netstat -tlnp | grep 8501
```

### Large image size

Check `.dockerignore` is excluding unnecessary files.

## Security

- Non-root user in app container
- No .env files in container
- Use secrets management in production
- Regular base image updates

## Maintenance

### Update base images

```bash
docker compose pull
docker compose up -d --build
```

### Clean up

```bash
docker compose down
docker system prune -a
```
```

**Step 3: Update main README navigation**

Edit `README.md`, add to navigation section (line 50):

```markdown
🚀 [TradingAgents](#tradingagents-framework) | ⚡ [Installation & CLI](#installation-and-cli) | 📦 [Package Usage](#tradingagents-package) | 🐳 [Containerization](#containerization) | 🤝 [Contributing](#contributing) | 📄 [Citation](#citation)
```

**Step 4: Commit**

```bash
git add README.md docs/CONTAINERIZATION.md
git commit -m "docs: add containerization documentation and update README"
```

---

## Task 8: Create Docker Workflow Files (Optional)

**Files:**
- Create: `.github/workflows/docker-build.yml`

**Step 1: Create Docker build workflow**

Create `.github/workflows/docker-build.yml`:

```yaml
name: Docker Build and Test

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'docker/**'
      - 'cli/**'
      - 'tradingagents/**'
      - 'pyproject.toml'
      - 'requirements.txt'
  pull_request:
    branches: [ main, develop ]
    paths:
      - 'docker/**'
      - 'cli/**'
      - 'tradingagents/**'
      - 'pyproject.toml'
      - 'requirements.txt'

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Build Docker image
      run: |
        cd docker
        docker build -f Dockerfile -t tradingagents:test ..
    
    - name: Test TUI mode
      run: |
        docker run --rm tradingagents:test python -c "import tradingagents; print('Import successful')"
    
    - name: Test Web mode
      run: |
        docker run --rm -e APP_MODE=web tradingagents:test python -c "import chainlit; print('Chainlit imported successfully')"
```

**Step 2: Commit**

```bash
git add .github/workflows/docker-build.yml
git commit -m "ci: add Docker build workflow"
```

---

## Task 9: Final Testing and Verification

**Files:**
- All created files
- Reference: `docs/plans/2026-03-09-container-design.md`

**Step 1: Full integration test - TUI**

```bash
cd docker
export OPENAI_API_KEY=test_key
export ALPHA_VANTAGE_API_KEY=test_key
docker compose run --rm app
```

Expected: TUI starts and displays menu

**Step 2: Full integration test - Web UI**

```bash
cd docker
export OPENAI_API_KEY=test_key
export ALPHA_VANTAGE_API_KEY=test_key
APP_MODE=web docker compose up
```

Expected: Web UI accessible at http://localhost:8501

**Step 3: Verify health checks**

```bash
docker compose ps
```

Expected: Both services show "healthy"

**Step 4: Test environment variables**

```bash
docker compose run --rm app env | grep APP_MODE
```

Expected: Output shows `APP_MODE=tui`

**Step 5: Test Redis connectivity**

```bash
docker compose run --rm app python -c "import redis; r = redis.Redis(host='redis', port=6379); r.ping(); print('Redis connected')"
```

Expected: Output shows "Redis connected"

**Step 6: Verify image size**

```bash
docker images | grep tradingagents
```

Expected: Image size < 2GB

**Step 7: Clean up**

```bash
docker compose down
```

**Step 8: Commit final cleanup**

```bash
git add -A
git commit -m "test: verify containerization implementation"
```

---

## Task 10: Create Usage Examples

**Files:**
- Create: `docker/examples/README.md`

**Step 1: Create examples directory**

```bash
mkdir -p docker/examples
```

**Step 2: Create examples documentation**

Create `docker/examples/README.md`:

```markdown
# Docker Usage Examples

## Local Development

### TUI Mode

```bash
cd docker
docker compose run --rm app
```

### Web UI Mode

```bash
cd docker
APP_MODE=web docker compose up
```

## Production Deployment

### With Environment File

```bash
cd docker
cp docker.env.example .env
# Edit .env
docker compose up -d
```

### With Environment Variables

```bash
export APP_MODE=web
export OPENAI_API_KEY=sk-...
docker compose up -d
```

## Advanced Usage

### Custom LLM Provider

```bash
docker compose run --rm app \
  -e LLM_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=sk-ant-...
```

### Debug Mode

```bash
docker compose run --rm -e DEBUG=true app
```

### Scale Redis

```bash
docker compose up -d --scale redis=3
```

## Monitoring

### View Logs

```bash
docker compose logs -f app
docker compose logs -f redis
```

### Check Health

```bash
docker compose ps
```

### Container Stats

```bash
docker stats
```

## Troubleshooting

### Rebuild Everything

```bash
docker compose down
docker compose build --no-cache
docker compose up
```

### Inspect Container

```bash
docker compose run --rm app /bin/bash
```

### Check Environment Variables

```bash
docker compose run --rm app env
```
```

**Step 3: Commit**

```bash
git add docker/examples/
git commit -m "docs: add Docker usage examples"
```

---

## Completion Checklist

- [ ] All tasks completed
- [ ] TUI mode works in container
- [ ] Web UI mode works in container
- [ ] Redis service starts and is healthy
- [ ] Environment variables properly injected
- [ ] Health checks passing
- [ ] Documentation complete
- [ ] Examples provided
- [ ] Image size optimized
- [ ] Security best practices followed

---

## Success Criteria

- Container builds successfully from `docker/Dockerfile`
- Both TUI and Web UI modes work with `docker compose`
- Redis service is healthy and accessible
- All configuration via environment variables
- Image size < 2GB
- Health checks passing for both services
- Documentation covers all usage scenarios
- Examples provided for common use cases
