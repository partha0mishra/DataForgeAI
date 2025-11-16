# Accelerator 1: Pipeline Automation

Intelligent data ingestion and transformation accelerator with Airflow, dbt, and Spark.

## Features

- **Airflow DAGs**: Orchestration of data pipelines
- **dbt Models**: SQL-based transformations with testing
- **Spark Jobs**: Distributed data processing
- **REST API**: Pipeline management and monitoring
- **Monitoring**: OpenTelemetry instrumentation

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
