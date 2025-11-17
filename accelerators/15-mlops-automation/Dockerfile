# Multi-stage Dockerfile for MLOps Automation Accelerator
# Stage 1: Base Python image with system dependencies
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


# Stage 2: Build dependencies
FROM base AS builder

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-warn-script-location -r requirements.txt


# Stage 3: Runtime
FROM base AS runtime

# Create non-root user
RUN useradd -m -u 1000 mlops && \
    mkdir -p /app && \
    chown -R mlops:mlops /app

# Copy Python dependencies from builder
COPY --from=builder --chown=mlops:mlops /root/.local /home/mlops/.local

# Update PATH
ENV PATH=/home/mlops/.local/bin:$PATH

# Switch to non-root user
USER mlops

# Copy application code
COPY --chown=mlops:mlops . .

# Expose port
EXPOSE 8015

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8015/health')" || exit 1

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8015"]
