FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y gcc g++ libpq-dev && rm -rf /var/lib/apt/lists/*

FROM base AS builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM base AS runtime
RUN useradd -m -u 1000 portability && mkdir -p /app /app/logs && chown -R portability:portability /app
COPY --from=builder /root/.local /home/portability/.local
COPY --chown=portability:portability . /app/
ENV PATH=/home/portability/.local/bin:$PATH
USER portability
EXPOSE 8024
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8024 --workers 2"]
