#!/bin/bash
set -e

echo "Starting TradingAgents container..."

# Check APP_MODE environment variable
APP_MODE="${APP_MODE:-tui}"

echo "Application mode: $APP_MODE"

if [ "$APP_MODE" = "web" ]; then
    echo "Starting Chainlit web interface..."
    exec chainlit run cli/web.py --host 0.0.0.0 --port 8501
elif [ "$APP_MODE" = "tui" ]; then
    echo "Starting TUI interface..."
    exec python -m cli.main
else
    echo "Error: Invalid APP_MODE '$APP_MODE'. Valid values are 'tui' or 'web'."
    exit 1
fi
