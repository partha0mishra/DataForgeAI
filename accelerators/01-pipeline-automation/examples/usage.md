# How to Use Accelerator 01: Pipeline Automation

## ⚠️ CRITICAL: Dependency Conflict Notice

This accelerator has **TWO INCOMPATIBLE deployment modes** due to Apache Airflow's dependency requirements:

1. **AIRFLOW MODE** - Full orchestration (requires Pydantic v1, SQLAlchemy 1.4.x)
2. **API-ONLY MODE** - Management API only (requires Pydantic v2, SQLAlchemy 2.0+)

**You cannot run both modes in the same Python environment.**

See [Deployment Modes](#deployment-modes) for details.

## Deployment Modes

### Mode 1: Airflow Orchestration (Isolated Environment)

**Use when:** You need full Airflow DAG orchestration capabilities

**Requirements:**
- Separate Python environment or Docker container
- Cannot use with dataforge-common or dataforge-connectors
- Incompatible with other DataForge accelerators

**Installation:**

```bash
# Option A: Separate Virtual Environment
python -m venv venv-airflow
source venv-airflow/bin/activate  # On Windows: venv-airflow\Scripts\activate
cd accelerators/01-pipeline-automation
pip install -r requirements-airflow.txt

# Option B: Docker (Recommended)
docker build -t dataforge-airflow .
docker run -d -p 8080:8080 dataforge-airflow
```

**What you get:**
- ✅ Apache Airflow UI and scheduler
- ✅ DAG orchestration and scheduling
- ✅ dbt transformation workflows
- ✅ Spark job execution
- ❌ DataForge shared libraries (incompatible)
- ❌ Integration with other accelerators

### Mode 2: API-Only (Compatible with Platform)

**Use when:** You only need the pipeline management API

**Requirements:**
- Compatible with dataforge shared libraries
- Can be deployed with other accelerators
- No Airflow DAG orchestration

**Installation:**

```bash
# Navigate to the accelerator directory
cd accelerators/01-pipeline-automation

# Install API-only dependencies
pip install -r requirements-api.txt -c ../../constraints.txt

# Install shared DataForge libraries
pip install -e ../../shared/common
pip install -e ../../shared/connectors
```

**What you get:**
- ✅ FastAPI management API
- ✅ Pipeline CRUD operations
- ✅ Run tracking and monitoring
- ✅ DataForge shared libraries
- ✅ Integration with other accelerators
- ❌ Airflow orchestration (use API to trigger external Airflow)

## Usage Examples

### Using Airflow Mode

#### 1. Start Airflow Components

```bash
# Using Docker Compose (recommended)
cd accelerators/01-pipeline-automation
docker-compose up -d

# Access Airflow UI
open http://localhost:8080
# Default credentials: admin/admin
```

#### 2. Configure Data Sources

Set Airflow variables for your data sources:

```bash
# Using Airflow CLI
airflow variables set source_db_host "your-postgres-host"
airflow variables set source_db_name "your-database"
airflow variables set source_table "your_table"
airflow variables set dest_db_host "your-dest-host"
airflow variables set dest_db_name "your-dest-database"
airflow variables set dest_table "your_dest_table"

# Database credentials (use Airflow connections instead for production)
airflow variables set source_db_user "your-user"
airflow variables set source_db_password "your-password"
airflow variables set dest_db_user "your-dest-user"
airflow variables set dest_db_password "your-dest-password"
```

#### 3. Customize DAGs

Copy and customize the template DAGs:

```bash
# Copy ingestion template
cp airflow/dags/ingestion_template.py airflow/dags/my_ingestion.py

# Edit the DAG
# - Update DAG name (line 107)
# - Customize extract_data() function (lines 26-62)
# - Customize load_data() function (lines 65-102)
# - Set schedule (line 110)
```

**Key customization points in `ingestion_template.py`:**
- Lines 36-41: Source database configuration
- Line 46: Source table name
- Lines 84-90: Destination database configuration
- Line 96: Destination table name
- Line 110: Schedule interval (`@daily`, `@hourly`, cron expression)

#### 4. Run dbt Transformations

```bash
# In Airflow environment
cd accelerators/01-pipeline-automation/dbt

# Run transformations
dbt run

# Run tests
dbt test

# Full refresh
dbt run --full-refresh
```

#### 5. Execute Spark Jobs

```bash
# Ingest from CSV
spark-submit spark/jobs/ingestion.py \
  csv \
  s3://my-bucket/input/*.csv \
  s3://my-bucket/output/

# Ingest from database
spark-submit \
  --jars /path/to/postgresql-jdbc.jar \
  spark/jobs/ingestion.py \
  jdbc \
  "jdbc:postgresql://host:5432/db?table=users" \
  s3://my-bucket/output/
```

### Using API-Only Mode

#### 1. Start the API Server

```bash
cd accelerators/01-pipeline-automation/api
uvicorn src.main:app --reload --port 8000
```

#### 2. Create a Pipeline

```bash
curl -X POST http://localhost:8000/pipelines \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer-data-ingestion",
    "description": "Daily customer data from production DB to warehouse",
    "schedule": "@daily",
    "config": {
      "source": "production_db",
      "destination": "warehouse"
    }
  }'

# Response:
# {
#   "pipeline_id": "pipe-1",
#   "name": "customer-data-ingestion",
#   "status": "active",
#   "created_at": "2025-11-19T10:00:00Z"
# }
```

#### 3. List Pipelines

```bash
curl http://localhost:8000/pipelines

# Response:
# [
#   {
#     "pipeline_id": "pipe-1",
#     "name": "customer-data-ingestion",
#     "description": "Daily customer data...",
#     "status": "active",
#     ...
#   }
# ]
```

#### 4. Trigger a Pipeline Run

```bash
curl -X POST http://localhost:8000/pipelines/pipe-1/runs

# Response:
# {
#   "run_id": "run-1",
#   "pipeline_id": "pipe-1",
#   "status": "running",
#   "start_time": "2025-11-19T10:05:00Z"
# }
```

#### 5. Check Run Status

```bash
# Get specific run
curl http://localhost:8000/runs/run-1

# List all runs for a pipeline
curl http://localhost:8000/runs?pipeline_id=pipe-1
```

#### 6. Get Metrics

```bash
curl http://localhost:8000/metrics

# Response:
# {
#   "total_pipelines": 5,
#   "total_runs": 42,
#   "active_runs": 2,
#   "timestamp": "2025-11-19T10:10:00Z"
# }
```

## Hybrid Deployment (Recommended for Production)

For production, use **both modes in separate environments**:

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Airflow for orchestration (isolated environment)
  airflow-webserver:
    build:
      context: .
      dockerfile: Dockerfile.airflow
    environment:
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
    ports:
      - "8080:8080"
    depends_on:
      - airflow-scheduler

  airflow-scheduler:
    build:
      context: .
      dockerfile: Dockerfile.airflow
    command: scheduler

  # API for management (compatible with platform)
  pipeline-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    environment:
      - AIRFLOW_URL=http://airflow-webserver:8080
    ports:
      - "8000:8000"
```

**How it works:**
1. Airflow runs in isolated container for orchestration
2. API runs in platform-compatible container
3. API calls Airflow REST API to trigger DAGs
4. Both share metadata database

## Configuration

### Airflow Configuration

Edit `airflow/airflow.cfg` or set environment variables:

```bash
# Executor
AIRFLOW__CORE__EXECUTOR=LocalExecutor  # or CeleryExecutor for scale

# Database
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://user:pass@host/db

# Webserver
AIRFLOW__WEBSERVER__WEB_SERVER_PORT=8080

# Security
AIRFLOW__WEBSERVER__SECRET_KEY=your-secret-key
```

### API Configuration

Edit environment variables:

```bash
# FastAPI
DATAFORGE_ENV=production
LOG_LEVEL=INFO

# Database (for API state)
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=your-password

# Airflow connection (if using hybrid mode)
AIRFLOW_URL=http://localhost:8080
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin
```

### dbt Configuration

Edit `dbt/profiles.yml`:

```yaml
pipeline_automation:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: dbt_user
      password: "{{ env_var('DBT_PASSWORD') }}"
      port: 5432
      dbname: analytics
      schema: dbt_dev
    
    prod:
      type: postgres
      host: prod-host
      user: dbt_prod
      password: "{{ env_var('DBT_PROD_PASSWORD') }}"
      port: 5432
      dbname: analytics
      schema: dbt_prod
```

## Deployment to Kubernetes

### Airflow on Kubernetes

```bash
# Using Helm
helm repo add apache-airflow https://airflow.apache.org
helm install airflow apache-airflow/airflow \
  --set executor=KubernetesExecutor \
  --set images.airflow.repository=dataforge/pipeline-airflow \
  --set images.airflow.tag=latest

# Or use provided manifests
kubectl apply -f k8s/airflow/
```

### API on Kubernetes

```bash
# Build and push image
docker build -f Dockerfile.api -t dataforge/pipeline-api:latest .
docker push dataforge/pipeline-api:latest

# Deploy
kubectl apply -f k8s/api/deployment.yaml

# Access
kubectl port-forward svc/pipeline-api 8000:80 -n dataforge
```

## API Endpoints Reference

- `GET /` - API information
- `GET /health` - Health check
- `POST /pipelines` - Create pipeline
- `GET /pipelines` - List all pipelines
- `GET /pipelines/{id}` - Get pipeline details
- `POST /pipelines/{id}/runs` - Trigger pipeline run
- `GET /runs` - List runs (optionally filtered by pipeline_id)
- `GET /runs/{id}` - Get run details
- `GET /metrics` - System metrics

## Example Use Cases

### Daily Customer Data Sync

1. **Create DAG** from `ingestion_template.py`
2. **Configure** source (production DB) and destination (warehouse)
3. **Set schedule** to `@daily` at 2 AM
4. **Add quality checks** using dbt tests
5. **Monitor** via Airflow UI or API

### Real-time Streaming to Batch

1. **Use Spark jobs** for batch processing of streaming data
2. **Trigger via Airflow** on schedule or sensor
3. **Store results** in data lake
4. **Transform** with dbt
5. **Track progress** via API

### Multi-source Consolidation

1. **Create multiple DAGs** (one per source)
2. **Use XCom** to pass data between tasks
3. **Consolidate** in final task
4. **Apply quality checks**
5. **Load** to destination

## Troubleshooting

### Airflow DAG Not Appearing

**Check:**
```bash
# Verify DAG syntax
python airflow/dags/your_dag.py

# Check DAG folder
echo $AIRFLOW_HOME/dags

# List DAGs
airflow dags list

# Check logs
docker logs airflow-scheduler
```

### Dependency Conflict Errors

**Error:** `ERROR: Cannot install packages due to conflicting dependencies`

**Solution:**
- ✅ Are you mixing Airflow and API dependencies? → Use separate environments
- ✅ Use the correct requirements file:
  - `requirements-airflow.txt` for Airflow mode
  - `requirements-api.txt` for API mode
- ✅ Create fresh virtual environment

### API Connection Errors

**Error:** `Connection refused` or database errors

**Check:**
```bash
# Verify database is running
docker ps | grep postgres

# Check environment variables
env | grep POSTGRES

# Test database connection
psql -h localhost -U your_user -d your_db

# Review API logs
docker logs pipeline-api
```

### Spark Job Failures

**Error:** `ClassNotFoundException: org.postgresql.Driver`

**Solution:**
```bash
# Add JDBC driver to classpath
spark-submit --jars /path/to/postgresql-42.6.0.jar \
  spark/jobs/ingestion.py ...

# Or set in spark-defaults.conf
spark.jars /path/to/postgresql-42.6.0.jar
```

**Error:** Out of memory

**Solution:**
```bash
# Increase driver/executor memory
spark-submit \
  --driver-memory 4g \
  --executor-memory 4g \
  spark/jobs/ingestion.py ...
```

## Performance Tuning

### Airflow

```python
# In airflow.cfg or environment
AIRFLOW__CORE__PARALLELISM=32  # Max parallel tasks
AIRFLOW__CORE__DAG_CONCURRENCY=16  # Max tasks per DAG
AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG=3  # Concurrent DAG runs
```

### Spark

```bash
# Optimize for your cluster
spark-submit \
  --num-executors 10 \
  --executor-cores 4 \
  --executor-memory 8g \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.sql.adaptive.coalescePartitions.enabled=true \
  spark/jobs/ingestion.py ...
```

### dbt

```bash
# Parallel model execution
dbt run --threads 4

# Incremental models for large tables
# In your model:
{{ config(materialized='incremental') }}
```

## Next Steps

After setting up the pipeline accelerator:

1. **Add Data Quality** - Integrate with accelerator 02 (Data Quality & Governance)
2. **Create Dashboards** - Use accelerator 06 (BI Dashboarding) to visualize pipeline metrics
3. **Implement Governance** - Apply policies from accelerator 12 (Data Governance)
4. **Set up Monitoring** - Use accelerator 14 (Data Observability) for advanced monitoring
5. **Enable MLOps** - Integrate with accelerator 15 (MLOps Automation) for ML pipelines

## Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [dbt Documentation](https://docs.getdbt.com/)
- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [DataForge Dependency Guide](../../docs/DEPENDENCIES.md)

---

## 📚 Example Pipelines

This accelerator includes **10 production-ready example pipelines** that demonstrate real-world use cases. Each example is a complete, working implementation with detailed documentation.

### Examples Overview

| # | Example | Use Case | Complexity | Status |
|---|---------|----------|------------|--------|
| **01** | [CSV to Warehouse](01-csv-to-warehouse/) | Classic batch file ingestion | ⭐ Beginner | ✅ Ready |
| **02** | [API to Lakehouse](02-api-to-lakehouse/) | REST API incremental loads | ⭐⭐ Intermediate | 🚧 Coming Soon |
| **03** | [Oracle to Snowflake](03-oracle-to-snowflake/) | Legacy database migration | ⭐⭐ Intermediate | 🚧 Coming Soon |
| **04** | [Medallion Architecture](04-medallion-architecture/) | Multi-source lakehouse | ⭐⭐⭐ Advanced | 🚧 Coming Soon |
| **05** | [Real-time Streaming](05-realtime-streaming/) | Fraud detection with windowing | ⭐⭐⭐ Advanced | 🚧 Coming Soon |
| **06** | [Snowflake Native](06-snowflake-native/) | Snowpark + Dynamic Tables | ⭐⭐ Intermediate | 🚧 Coming Soon |
| **07** | [BigQuery + Looker](07-bigquery-looker/) | GA4 to Looker pipeline | ⭐⭐ Intermediate | 🚧 Coming Soon |
| **08** | [Cost-Optimized Serverless](08-cost-optimized-serverless/) | AWS Glue serverless architecture | ⭐⭐ Intermediate | 🚧 Coming Soon |
| **09** | [Governed + Secure](09-governed-secure/) | Zero-trust security pipeline | ⭐⭐⭐ Advanced | 🚧 Coming Soon |
| **10** | [AI Feature Store](10-ai-feature-store/) | ML feature engineering at scale | ⭐⭐⭐⭐ Expert | 🚧 Coming Soon |

### Quick Start by Use Case

**I need to:**
- **Ingest files from S3/GCS** → Start with Example 01
- **Pull data from APIs** → Start with Example 02
- **Migrate from Oracle/SQL Server** → Start with Example 03
- **Build a data lakehouse** → Start with Example 04
- **Detect fraud in real-time** → Start with Example 05
- **Use Snowflake native features** → Start with Example 06
- **Analyze marketing data** → Start with Example 07
- **Optimize costs** → Start with Example 08
- **Pass security audits** → Start with Example 09
- **Build ML features** → Start with Example 10

### Example Structure

Each example includes:
- 📖 **README.md** - Complete documentation with architecture diagrams
- ⚙️ **config.yaml** - Customizable configuration file
- 💻 **Working Code** - Airflow DAGs, Spark jobs, SQL, etc.
- 📊 **Sample Data** - Test data to run immediately (where applicable)
- ✅ **Tests** - Data quality checks and validation
- 🔧 **Setup Scripts** - One-command deployment

### Learning Path

**Beginner → Advanced:**
1. Start with **Example 01** (CSV to Warehouse) - Learn the basics
2. Try **Example 02** (API to Lakehouse) - Add incremental logic
3. Explore **Example 04** (Medallion) - Understand architecture patterns
4. Master **Example 10** (Feature Store) - Advanced ML pipelines

### Contributing Examples

Have a great pipeline pattern? We welcome contributions!
See [CONTRIBUTING.md](../../../../CONTRIBUTING.md) for guidelines.

---
