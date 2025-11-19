# How to Use Accelerator 01: Pipeline Automation

This guide provides practical instructions for using the Pipeline Automation accelerator.

## Installation & Setup

```bash
# Navigate to the accelerator directory
cd accelerators/01-pipeline-automation

# Install dependencies
pip install -r requirements.txt

# Install shared DataForge libraries
pip install -e ../../shared/dataforge-common
pip install -e ../../shared/dataforge-connectors
```

## Three Ways to Use It

### A. Via FastAPI (Easiest for Testing)

Start the API server locally:

```bash
cd api
uvicorn src.main:app --reload --port 8000
```

Then interact via REST API:

```bash
# Create a pipeline
curl -X POST http://localhost:8000/pipelines \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-data-pipeline",
    "description": "Ingest customer data daily",
    "schedule": "@daily",
    "config": {}
  }'

# List pipelines
curl http://localhost:8000/pipelines

# Trigger a pipeline run
curl -X POST http://localhost:8000/pipelines/pipe-1/runs

# Check metrics
curl http://localhost:8000/metrics
```

### B. Via Airflow (Production Orchestration)

The accelerator provides template DAGs in `airflow/dags/`:

**ingestion_template.py** - Customize for your data source:
- Lines 36-41: Configure your source database connection
- Lines 46: Specify source table
- Lines 84-90: Configure destination database
- Lines 96: Specify destination table

To use Airflow:

```bash
# Set Airflow variables for database connections
airflow variables set source_db_host "your-db-host"
airflow variables set source_db_name "your-db-name"
airflow variables set source_table "your_table"
airflow variables set dest_db_host "your-dest-host"
airflow variables set dest_db_name "your-dest-name"
airflow variables set dest_table "your_dest_table"
airflow variables set source_db_user "your-user"
airflow variables set source_db_password "your-password"
airflow variables set dest_db_user "your-dest-user"
airflow variables set dest_db_password "your-dest-password"

# Copy/customize the DAG
cp airflow/dags/ingestion_template.py ~/airflow/dags/my_ingestion.py

# DAG will appear in Airflow UI at http://localhost:8080
```

### C. Via Spark (Large-Scale Processing)

For big data workloads, use the Spark job:

```bash
# Ingest from CSV
spark-submit spark/jobs/ingestion.py \
  csv \
  s3://my-bucket/input/*.csv \
  s3://my-bucket/output/

# Ingest from database (customize the JDBC logic)
spark-submit \
  --jars postgresql-jdbc.jar \
  spark/jobs/ingestion.py \
  jdbc \
  "jdbc:postgresql://host:5432/db?table=users" \
  s3://my-bucket/output/
```

## Deploy to Kubernetes

For production deployment:

```bash
# Build Docker image
docker build -t dataforge/pipeline-api:latest .

# Deploy to Kubernetes
kubectl apply -f k8s/deployment.yaml

# Access the API
kubectl port-forward svc/pipeline-api 8000:80 -n dataforge
```

## Customize for Your Use Case

The accelerator is a **template** - customize these components:

1. **airflow/dags/ingestion_template.py:26-62** - Modify `extract_data()` for your source
2. **airflow/dags/ingestion_template.py:65-102** - Modify `load_data()` for your destination
3. **spark/jobs/ingestion.py** - Add custom transformations and new source types
4. **dbt/** - Add your SQL transformation models

## Key Configuration Points

- **Database credentials**: Set via Airflow variables or environment variables
- **Schedule**: Line 110 in DAG files (e.g., `@daily`, `@hourly`, cron expressions)
- **Retry logic**: Lines 21-22 in DAG files
- **Resources**: Lines 41-46 in k8s/deployment.yaml

## API Endpoints Reference

- `POST /pipelines` - Create new pipeline
- `GET /pipelines` - List all pipelines
- `GET /pipelines/{id}` - Get pipeline details
- `POST /pipelines/{id}/runs` - Trigger pipeline execution
- `GET /runs` - View pipeline run history
- `GET /runs/{id}` - Get run details
- `GET /metrics` - Pipeline statistics
- `GET /health` - Health check

## Example Use Cases

### Daily Customer Data Ingestion

1. Customize `ingestion_template.py` to extract from your customer database
2. Configure Airflow variables with your database credentials
3. Set schedule to `@daily`
4. Deploy and monitor via Airflow UI

### Real-time Streaming with Batch Processing

1. Use Spark jobs for batch processing of accumulated streaming data
2. Trigger Spark jobs via Airflow on a schedule
3. Store results in data lake (S3/GCS)
4. Use dbt for downstream transformations

### Multi-source Data Consolidation

1. Create multiple DAGs (one per source)
2. Use XCom to pass data between tasks
3. Consolidate in final loading task
4. Apply data quality checks before final load

## Troubleshooting

### Airflow DAG not appearing
- Check DAG syntax: `python airflow/dags/your_dag.py`
- Verify DAG is in correct folder: `~/airflow/dags/` or `$AIRFLOW_HOME/dags/`
- Check Airflow logs: `airflow dags list`

### API connection errors
- Verify database credentials in environment variables
- Check network connectivity to data sources
- Review logs: `docker logs <container-id>`

### Spark job failures
- Check Spark driver logs
- Verify JDBC driver is in classpath
- Ensure sufficient memory allocation

## Next Steps

After setting up the pipeline:
1. Add data quality checks (see Accelerator 02)
2. Set up monitoring dashboards (see Accelerator 06)
3. Implement data governance policies (see Accelerator 12)
