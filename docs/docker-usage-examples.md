# Docker Usage Examples

This document provides practical examples for using TradingAgents with Docker.

## Table of Contents

1. [Quick Start](#quick-start)
2. [TUI Mode Examples](#tui-mode-examples)
3. [Web UI Mode Examples](#web-ui-mode-examples)
4. [Development Workflow](#development-workflow)
5. [Production Deployment](#production-deployment)
6. [Troubleshooting](#troubleshooting)

## Quick Start

### Build the Docker Image

```bash
# From the project root
docker build -f docker/Dockerfile -t tradingagents:latest .
```

### Start Redis Service

```bash
cd docker
docker compose up -d redis
```

## TUI Mode Examples

### Interactive TUI Session

```bash
# Run TUI mode interactively
docker run --rm -it \
  -e APP_MODE=tui \
  -e OPENAI_API_KEY=your_key_here \
  -e ALPHA_VANTAGE_API_KEY=your_key_here \
  --add-host host.docker.internal:host-gateway \
  tradingagents:latest
```

### TUI with Docker Compose

```bash
cd docker

# Create .env file with your API keys
cat > .env << EOF
APP_MODE=tui
OPENAI_API_KEY=your_key_here
ALPHA_VANTAGE_API_KEY=your_key_here
EOF

# Run interactively
docker compose run --rm -it app
```

### Non-Interactive TUI (Scripting)

```bash
docker run --rm \
  -e APP_MODE=tui \
  -e OPENAI_API_KEY=your_key_here \
  -e ALPHA_VANTAGE_API_KEY=your_key_here \
  tradingagents:latest \
  python -m cli.main --ticker AAPL --date 2026-03-09
```

## Web UI Mode Examples

### Start Web UI

```bash
cd docker

# Set environment variables
export APP_MODE=web
export OPENAI_API_KEY=your_key_here
export ALPHA_VANTAGE_API_KEY=your_key_here

# Start all services
docker compose up -d

# Access at http://localhost:8501
```

### Web UI with Docker Compose

```bash
cd docker

# Create .env file
cat > .env << EOF
APP_MODE=web
OPENAI_API_KEY=your_key_here
ALPHA_VANTAGE_API_KEY=your_key_here
EOF

# Start all services
docker compose up

# Access at http://localhost:8501
```

### Custom Port for Web UI

```bash
cd docker

# Modify docker-compose.yml ports or use port mapping
docker compose run --rm -p 8080:8501 app
```

### Detached Mode

```bash
# Run in background
docker compose up -d

# View logs
docker compose logs -f app

# Stop services
docker compose down
```

## Development Workflow

### Hot-Reload Development

Uncomment volumes section in `docker/docker-compose.yml`:

```yaml
volumes:
  - ../:/app
  - /app/.git
  - /app/tradingagents/__pycache__
  - /app/tradingagents/**/__pycache__
```

Then:

```bash
cd docker
APP_MODE=web docker compose up

# Make code changes - they'll be reflected immediately
```

### Debugging with Shell Access

```bash
# Open a shell in the container
docker run --rm -it \
  -e APP_MODE=tui \
  tradingagents:latest \
  /bin/bash

# From inside the container
source /opt/conda/etc/profile.d/conda.sh
conda activate tradingagents
python -m cli.main
```

### Testing Different LLM Providers

```bash
# Using Google Gemini
docker run --rm -it \
  -e APP_MODE=tui \
  -e GOOGLE_API_KEY=your_key_here \
  -e ALPHA_VANTAGE_API_KEY=your_key_here \
  tradingagents:latest

# Using Anthropic Claude
docker run --rm -it \
  -e APP_MODE=tui \
  -e ANTHROPIC_API_KEY=your_key_here \
  -e ALPHA_VANTAGE_API_KEY=your_key_here \
  tradingagents:latest

# Using xAI Grok
docker run --rm -it \
  -e APP_MODE=tui \
  -e XAI_API_KEY=your_key_here \
  -e ALPHA_VANTAGE_API_KEY=your_key_here \
  tradingagents:latest
```

## Production Deployment

### Production with Docker Compose

```bash
cd docker

# Create production .env file
cat > .env << EOF
APP_MODE=web
OPENAI_API_KEY=your_production_key
ALPHA_VANTAGE_API_KEY=your_production_key
REDIS_HOST=redis
REDIS_PORT=6379
EOF

# Enable persistence in docker-compose.yml
# Uncomment the volumes section for redis-data

# Start services
APP_MODE=web docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Production with Docker Swarm

```bash
# Deploy to swarm
docker stack deploy -c docker/docker-compose.yml tradingagents

# Scale services
docker service scale tradingagents_app=3

# View services
docker service ls
```

### Production with Kubernetes

```bash
# Build and push image
docker build -f docker/Dockerfile -t your-registry/tradingagents:latest .
docker push your-registry/tradingagents:latest

# Apply kubernetes manifests
kubectl apply -f k8s/
```

### Health Checks

```bash
# Check container health
docker ps --filter name=tradingagents-app

# Check health endpoint (when web UI is running)
curl http://localhost:8501
```

## Troubleshooting

### Common Issues

**Issue: Container exits immediately**

```bash
# Check logs
docker logs tradingagents-app

# Common cause: Missing API keys
# Solution: Ensure all required environment variables are set
```

**Issue: Can't access localhost services from container**

```bash
# Use host.docker.internal (Mac/Windows) or host-gateway (Linux)
docker run --rm --add-host host.docker.internal:host-gateway ...
```

**Issue: Permission errors with volumes**

```bash
# Fix file ownership
sudo chown -R 1000:1000 ./results ./reports
```

**Issue: Port already in use**

```bash
# Check what's using the port
lsof -i :8501

# Kill the process or change port mapping in docker-compose.yml
```

### Debug Commands

```bash
# View detailed logs
docker compose logs --tail=100 -f app

# Enter container for debugging
docker compose exec app /bin/bash

# Check resource usage
docker stats tradingagents-app

# Clean up old images
docker system prune -a
```

### Network Issues

```bash
# Inspect network
docker network inspect docker_tradingagents-network

# Test connectivity
docker compose exec app ping redis

# Check DNS
docker compose exec app nslookup redis
```

## Advanced Examples

### Custom Configuration

```bash
docker run --rm -it \
  -e APP_MODE=tui \
  -e OPENAI_API_KEY=your_key_here \
  -e ALPHA_VANTAGE_API_KEY=your_key_here \
  -e REDIS_HOST=custom.redis.host \
  -e REDIS_PORT=6380 \
  tradingagents:latest
```

### Multiple Instances

```bash
# Run multiple instances with different configurations
docker run --rm -it -p 8501:8501 \
  -e APP_MODE=web \
  -e OPENAI_API_KEY=key1 \
  tradingagents:latest

docker run --rm -it -p 8502:8501 \
  -e APP_MODE=web \
  -e OPENAI_API_KEY=key2 \
  tradingagents:latest
```

### Resource Limits

```bash
# Modify docker-compose.yml to add limits
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Security Best Practices

1. **Never commit API keys** - Use environment variables or secrets management
2. **Use non-root user** - Already configured in Dockerfile
3. **Scan images for vulnerabilities**
   ```bash
   docker scan tradingagents:latest
   ```
4. **Use specific image tags** - Avoid `:latest` in production
5. **Enable content trust**
   ```bash
   export DOCKER_CONTENT_TRUST=1
   ```
6. **Read-only filesystem** (advanced):
   ```bash
   docker run --read-only ... tradingagents:latest
   ```

## Cleanup

```bash
# Stop and remove containers
docker compose down

# Remove images
docker rmi tradingagents:test tradingagents:latest

# Remove volumes
docker volume rm docker_redis-data

# Full cleanup
docker system prune -a --volumes
```

## Next Steps

- Read the [main README](../README.md) for more information
- Check [Implementation Plan](../docs/plans/2026-03-09-containerization.md) for technical details
- Review [Container Design](../docs/plans/2026-03-09-container-design.md) for architecture decisions
