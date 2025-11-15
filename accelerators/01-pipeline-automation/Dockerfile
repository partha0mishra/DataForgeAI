# Multi-stage Dockerfile for Pipeline Automation Accelerator

# Stage 1: Base image with common dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    AIRFLOW_HOME=/opt/airflow

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Airflow image
FROM base as airflow

# Install Apache Airflow
RUN pip install apache-airflow==2.7.3 \
    apache-airflow-providers-postgres==5.7.1 \
    apache-airflow-providers-amazon==8.8.0

# Install shared libraries
COPY shared/common /tmp/shared/common
COPY shared/connectors /tmp/shared/connectors
RUN cd /tmp/shared/common && pip install -e . && \
    cd /tmp/shared/connectors && pip install -e .

# Copy Airflow DAGs
COPY accelerators/01-pipeline-automation/airflow/dags ${AIRFLOW_HOME}/dags
COPY accelerators/01-pipeline-automation/airflow/plugins ${AIRFLOW_HOME}/plugins
COPY accelerators/01-pipeline-automation/airflow/config ${AIRFLOW_HOME}/config

# Create airflow user
RUN useradd -ms /bin/bash -d ${AIRFLOW_HOME} airflow && \
    chown -R airflow: ${AIRFLOW_HOME}

USER airflow
WORKDIR ${AIRFLOW_HOME}

# Initialize Airflow database
RUN airflow db init

EXPOSE 8080

CMD ["airflow", "webserver"]

# Stage 3: API image
FROM base as api

WORKDIR /app

# Install FastAPI and dependencies
COPY accelerators/01-pipeline-automation/api/requirements.txt .
RUN pip install -r requirements.txt

# Install shared libraries
COPY shared/common /tmp/shared/common
COPY shared/connectors /tmp/shared/connectors
RUN cd /tmp/shared/common && pip install -e . && \
    cd /tmp/shared/connectors && pip install -e .

# Copy API code
COPY accelerators/01-pipeline-automation/api/src /app/src

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
