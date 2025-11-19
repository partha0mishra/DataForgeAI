# Accelerator 1: Pipeline Automation

**Purpose**: Intelligent data ingestion and transformation accelerator for building production-ready automated data pipelines.

## Overview

This accelerator provides a comprehensive framework for building automated data pipelines with modern best practices like orchestration, testing, and observability built-in. It's designed to be deployed on Kubernetes and integrates with the common DataForge authentication and monitoring infrastructure.

## Core Technology Stack

- **Apache Airflow** - Workflow orchestration and scheduling
- **dbt (data build tool)** - SQL-based transformations and testing
- **Apache Spark** - Distributed data processing for large-scale workloads
- **FastAPI** - RESTful API for pipeline management and monitoring
- **OpenTelemetry** - Observability and instrumentation

## Key Features

### 1. Workflow Orchestration
- **Pre-built Airflow DAGs**: Ready-to-use templates for common patterns
- **Generic Ingestion Template**: Extract-Load pattern with customizable sources
- **Transformation Pipeline**: dbt integration for SQL transformations
- **Data Quality Checks**: Automated validation workflows

### 2. Data Transformation
- **Staged Transformation Layers**: Staging → Intermediate → Marts architecture
- **Reusable SQL Macros**: DRY principle for SQL code
- **Built-in Testing Framework**: Data quality tests and assertions
- **Version Control**: All transformations in Git

### 3. API-Driven Management
- **Pipeline CRUD Operations**: Create, read, update pipeline definitions
- **Run Management**: Trigger and monitor pipeline executions
- **Metrics & Monitoring**: Real-time pipeline statistics
- **Health Checks**: System health and readiness probes

### 4. Monitoring & Observability
- **OpenTelemetry Integration**: Distributed tracing and metrics
- **Duration Tracking**: Performance monitoring for all operations
- **Structured Logging**: JSON-formatted logs for analysis
- **Custom Metrics**: Counter and gauge metrics for business KPIs

## Components

### Airflow
- `dags/ingestion_template.py` - Generic data ingestion DAG
- `dags/transformation_template.py` - dbt transformation DAG
- `dags/quality_checks_dag.py` - Data quality validation DAG
- `plugins/` - Custom operators and hooks

### dbt
- `models/staging/` - Raw data models
- `models/intermediate/` - Business logic layer
- `models/marts/` - Analytics-ready datasets
- `macros/` - Reusable SQL macros
- `tests/` - Data tests

### Spark
- `jobs/ingestion.py` - Data ingestion with Spark
- `jobs/transformation.py` - Complex transformations

### API
- FastAPI application for pipeline management
- Endpoints: `/pipelines`, `/runs`, `/logs`, `/metrics`

## Main API Endpoints

- `POST /pipelines` - Create new pipeline
- `GET /pipelines` - List all pipelines
- `GET /pipelines/{id}` - Get pipeline details
- `POST /pipelines/{id}/runs` - Trigger pipeline execution
- `GET /runs` - View pipeline run history
- `GET /runs/{id}` - Get run details
- `GET /metrics` - Pipeline statistics
- `GET /health` - Health check endpoint

## Usage Guide

For detailed usage instructions, examples, and troubleshooting, see [examples/usage.md](examples/usage.md).

## Quick Start

### Local Development

```bash
# Start Airflow (requires docker-compose)
cd deployments/local
docker-compose up airflow-webserver airflow-scheduler

# Access Airflow UI
open http://localhost:8080

# Run dbt
cd accelerators/01-pipeline-automation/dbt
dbt run
dbt test

# Start API
cd accelerators/01-pipeline-automation/api
uvicorn src.main:app --reload
```

### Deploy to Kubernetes

```bash
kubectl apply -f k8s/
```

## Configuration

Edit `config/pipeline_config.yaml` to configure:
- Data sources
- Transformations
- Quality checks
- Alerts

## Testing

```bash
pytest tests/
```
