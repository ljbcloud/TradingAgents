FROM docker.io/continuumio/miniconda3:latest

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml requirements.txt uv.lock ./

# Create conda environment with Python 3.13
SHELL ["/bin/bash", "-c"]
RUN conda create -n tradingagents python=3.13 -y && \
    echo "source /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate tradingagents" >> ~/.bashrc

# Install Python dependencies
RUN /bin/bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate tradingagents && pip install --no-cache-dir -r requirements.txt"

# Copy application code
COPY . /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser
WORKDIR /app

# Set environment variables
ENV PATH="/opt/conda/envs/tradingagents/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Copy entrypoint script
COPY --chown=appuser:appuser docker/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Expose port for Chainlit web UI
EXPOSE 8501

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command (can be overridden by APP_MODE env var)
CMD []
