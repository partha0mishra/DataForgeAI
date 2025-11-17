# Multi-stage Dockerfile for AI Explainability Accelerator
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Builder stage - install Python dependencies
FROM base AS builder

COPY requirements.txt .

# Install Python dependencies to /root/.local
RUN pip install --user -r requirements.txt

# Runtime stage
FROM base AS runtime

# Create non-root user
RUN useradd -m -u 1000 explainai && \
    mkdir -p /app /app/logs && \
    chown -R explainai:explainai /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/explainai/.local

# Copy application code
COPY --chown=explainai:explainai . /app/

# Update PATH
ENV PATH=/home/explainai/.local/bin:$PATH

# Switch to non-root user
USER explainai

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8023/health')"

# Expose port
EXPOSE 8023

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8023 --workers 2"]
