# Pipeline Automation Examples

**10 production-ready pipeline examples demonstrating real-world data engineering patterns**

This directory contains complete, working implementations of data pipelines ranging from beginner to expert complexity. Each example is fully functional and includes all necessary code, configuration, and documentation.

---

## 📋 Quick Reference

| # | Example | Complexity | Use Case | Status |
|---|---------|------------|----------|--------|
| [01](#01-csv-to-warehouse) | CSV to Warehouse | ⭐ Beginner | Batch file ingestion | ✅ **Ready** |
| [02](#02-api-to-lakehouse) | API to Lakehouse | ⭐⭐ Intermediate | REST API incremental loads | ✅ **Ready** |
| [03](#03-oracle-to-snowflake) | Oracle to Snowflake | ⭐⭐ Intermediate | Legacy database migration | ✅ **Ready** |
| [04](#04-medallion-architecture) | Medallion Architecture | ⭐⭐⭐ Advanced | Multi-source lakehouse | ✅ **Ready** |
| [05](#05-real-time-streaming) | Real-time Streaming | ⭐⭐⭐ Advanced | Fraud detection | ✅ **Ready** |
| [06](#06-snowflake-native) | Snowflake Native | ⭐⭐ Intermediate | Snowpark + Dynamic Tables | ✅ **Ready** |
| [07](#07-bigquery--looker) | BigQuery + Looker | ⭐⭐ Intermediate | GA4 analytics | ✅ **Ready** |
| [08](#08-cost-optimized-serverless) | Cost-Optimized Serverless | ⭐⭐ Intermediate | AWS serverless | ✅ **Ready** |
| [09](#09-governed--secure) | Governed + Secure | ⭐⭐⭐ Advanced | Zero-trust security | ✅ **Ready** |
| [10](#10-ai-feature-store) | AI Feature Store | ⭐⭐⭐⭐ Expert | ML feature engineering | ✅ **Ready** |

---

## 🎯 Choose Your Example

### By Use Case

**I need to...**
- **Ingest files from S3/GCS** → [Example 01](#01-csv-to-warehouse)
- **Pull data from APIs (Shopify, Salesforce, etc.)** → [Example 02](#02-api-to-lakehouse)
- **Migrate from Oracle/SQL Server** → [Example 03](#03-oracle-to-snowflake)
- **Build a data lakehouse** → [Example 04](#04-medallion-architecture)
- **Detect fraud in real-time** → [Example 05](#05-real-time-streaming)
- **Use Snowflake native features** → [Example 06](#06-snowflake-native)
- **Analyze marketing data (GA4)** → [Example 07](#07-bigquery--looker)
- **Optimize cloud costs** → [Example 08](#08-cost-optimized-serverless)
- **Pass security audits** → [Example 09](#09-governed--secure)
- **Build ML features** → [Example 10](#10-ai-feature-store)

### By Platform

- **Snowflake**: Examples 01, 03, 06, 10
- **Databricks**: Examples 02, 04, 05
- **BigQuery**: Example 07
- **Azure Synapse**: Example 09
- **AWS**: Examples 02, 05, 08

### By Complexity

- **Beginner** (Start here): Example 01
- **Intermediate**: Examples 02, 03, 06, 07, 08
- **Advanced**: Examples 04, 05, 09
- **Expert**: Example 10

---

## 📦 What's Included in Each Example

Every example contains:

```
<example-name>/
├── README.md                  # Complete documentation
├── config.yaml               # Configuration template
├── <component-dirs>/         # Working code (Airflow DAGs, SQL, scripts, etc.)
│   └── *.py, *.sql, *.sh    # Production-ready implementations
└── sample_data/              # Test data (where applicable)
```

---

## 🚀 Getting Started

### Prerequisites

Before running any example, ensure you have:

1. **Python 3.11+** installed
2. **Base dependencies** (from accelerator root):
   ```bash
   cd ../../  # Go to accelerator root
   pip install -r requirements-api.txt -c ../../constraints.txt
   ```

3. **Shared libraries** (required for most examples):
   ```bash
   # From within an example directory (e.g., 01-csv-to-warehouse/)
   pip install -e ../../../../shared/common
   pip install -e ../../../../shared/connectors

   # Or from examples/ directory
   pip install -e ../../../shared/common
   pip install -e ../../../shared/connectors
   ```

4. **Platform-specific tools** (depending on example):
   - Airflow 2.7+ (Examples 01, 02, 03, 07, 09, 10)
   - dbt 1.7+ (Example 01)
   - Spark 3.5+ (Examples 04, 05)
   - Docker (for Airflow, Kafka, Redis)
   - Cloud CLI tools (aws, az, gcloud)

### Quick Start Guide

**Step 1:** Choose an example based on your use case

**Step 2:** Read the example's README.md for specific prerequisites

**Step 3:** Follow the installation instructions below

**Step 4:** Configure with your credentials

**Step 5:** Run the example!

---

## 📚 Detailed Example Guides

### 01. CSV to Warehouse

**What it does**: Ingests daily CSV files from S3 into Snowflake using Airflow + dbt

**Files**: 6 files, 1,337 lines
```
01-csv-to-warehouse/
├── airflow/sales_ingestion_dag.py       # Orchestration DAG
├── dbt/models/bronze/sales_raw.sql      # Bronze layer
├── dbt/models/silver/sales_clean.sql    # Silver layer (cleansed)
├── dbt/tests/sales_data_quality.sql     # Quality tests
├── sample_data/sales_2024_11.csv        # 100 sample records
└── scripts/setup.sh                     # Automated setup
```

**Installation**:
```bash
cd 01-csv-to-warehouse

# Install dependencies
pip install \
  apache-airflow==2.7.3 \
  apache-airflow-providers-amazon==8.8.0 \
  dbt-core==1.7.0 \
  dbt-snowflake==1.7.0

# Note: Airflow conflicts with shared libraries (see ../usage.md)
# Run in isolated environment

# Configure and run
./scripts/setup.sh \
  --s3-bucket your-bucket \
  --snowflake-account xy12345 \
  --snowflake-user etl_user \
  --snowflake-password your-password
```

**Usage**:
```bash
# Trigger DAG
airflow dags trigger sales_csv_to_snowflake

# Run dbt manually
cd dbt
dbt run --models sales_raw sales_clean
dbt test
```

**Learn more**: [01-csv-to-warehouse/README.md](01-csv-to-warehouse/README.md)

---

### 02. API to Lakehouse

**What it does**: Pulls data from Shopify API every 15 minutes into Delta Lake with incremental loading

**Files**: 4 files, 1,777 lines
```
02-api-to-lakehouse/
├── scripts/shopify_extractor.py         # API client with rate limiting
├── scripts/delta_merger.py              # Delta Lake merge logic
├── airflow/shopify_incremental_dag.py   # Orchestration
└── tests/test_api_client.py             # Unit tests
```

**Installation**:
```bash
cd 02-api-to-lakehouse

# Install dependencies
pip install \
  requests>=2.31.0 \
  delta-spark>=2.4.0 \
  pyspark>=3.5.0 \
  pyarrow>=13.0.0 \
  -c ../../../../constraints.txt

# Install shared libraries (from example directory)
pip install -e ../../../../shared/common
pip install -e ../../../../shared/connectors

# Run tests
pytest tests/ -v
```

**Usage**:
```bash
# Set environment variables
export SHOPIFY_API_KEY="your-api-key"
export SHOPIFY_API_SECRET="your-secret"
export SHOPIFY_STORE="your-store.myshopify.com"

# Run extractor
python scripts/shopify_extractor.py

# Or trigger via Airflow
airflow dags trigger shopify_orders_incremental
```

**Learn more**: [02-api-to-lakehouse/README.md](02-api-to-lakehouse/README.md)

---

### 03. Oracle to Snowflake

**What it does**: Migrates Oracle tables to Snowflake using CDC (Change Data Capture)

**Files**: 5 files, 2,471 lines
```
03-oracle-to-snowflake/
├── scripts/schema_discovery.py          # Auto-discover Oracle schemas
├── scripts/cdc_processor.py             # CDC extraction
├── airflow/oracle_cdc_dag.py            # Migration orchestration
├── sql/oracle_cdc_setup.sql             # Oracle configuration
└── sql/snowflake_target_ddl.sql         # Target schema
```

**Installation**:
```bash
cd 03-oracle-to-snowflake

# Install dependencies
pip install \
  cx_Oracle>=8.3.0 \
  snowflake-connector-python>=3.6.0 \
  pyarrow>=13.0.0 \
  -c ../../../../constraints.txt

# Setup Oracle (run as DBA)
sqlplus / as sysdba @sql/oracle_cdc_setup.sql

# Create Snowflake target
snowsql -f sql/snowflake_target_ddl.sql
```

**Usage**:
```bash
# Discover Oracle schema
python scripts/schema_discovery.py \
  --host oracle-db \
  --service-name ORCL \
  --schemas HR FINANCE

# Run CDC extraction
python scripts/cdc_processor.py \
  --schema HR \
  --table EMPLOYEES \
  --mode incremental

# Or use Airflow
airflow dags trigger oracle_to_snowflake_cdc
```

**Learn more**: [03-oracle-to-snowflake/README.md](03-oracle-to-snowflake/README.md)

---

### 04. Medallion Architecture

**What it does**: Implements bronze/silver/gold lakehouse architecture with Delta Live Tables

**Files**: 5 files, 2,332 lines
```
04-medallion-architecture/
├── databricks/dlt_pipeline.py           # Delta Live Tables
├── databricks/notebook_bronze_silver_gold.py  # Alternative (no DLT)
├── kafka/mock_producer.py               # IoT event generator
├── monitoring/data_quality_checks.py    # Quality monitoring
└── config.yaml                          # DLT configuration
```

**Installation**:
```bash
cd 04-medallion-architecture

# Install dependencies
pip install \
  pyspark>=3.5.0 \
  delta-spark>=2.4.0 \
  kafka-python>=2.0.0 \
  -c ../../../../constraints.txt

# Start Kafka (Docker)
docker run -d --name kafka \
  -p 9092:9092 \
  apache/kafka:latest

# Generate mock data
python kafka/mock_producer.py --rate 100
```

**Usage**:
```bash
# Deploy DLT pipeline (Databricks)
databricks pipelines create --settings config.yaml

# OR run notebook version (any Spark cluster)
spark-submit databricks/notebook_bronze_silver_gold.py full

# Monitor quality
python monitoring/data_quality_checks.py --layer all
```

**Learn more**: [04-medallion-architecture/README.md](04-medallion-architecture/README.md)

---

### 05. Real-time Streaming

**What it does**: Real-time fraud detection using Spark Structured Streaming + Redis + Kinesis

**Files**: 5 files, 2,366 lines
```
05-realtime-streaming/
├── spark/streaming_fraud_detection.py   # Main streaming job
├── redis/customer_risk_loader.py        # Load risk scores
├── alerts/slack_notifier.py             # Slack alerts
├── scripts/transaction_generator.py     # Mock transactions
└── config.yaml                          # Configuration
```

**Installation**:
```bash
cd 05-realtime-streaming

# Install dependencies
pip install \
  pyspark>=3.5.0 \
  delta-spark>=2.4.0 \
  redis>=5.0.0 \
  boto3>=1.28.0 \
  -c ../../../../constraints.txt

# Start Redis
docker run -d --name redis -p 6379:6379 redis:latest

# Load customer risk data
python redis/customer_risk_loader.py --source csv --file customers.csv
```

**Usage**:
```bash
# Generate test transactions
python scripts/transaction_generator.py \
  --stream transactions \
  --rate 100

# Run fraud detection
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  spark/streaming_fraud_detection.py
```

**Learn more**: [05-realtime-streaming/README.md](05-realtime-streaming/README.md)

---

### 06. Snowflake Native

**What it does**: Snowpark Python + Dynamic Tables for native Snowflake pipelines

**Files**: 3 files, 1,552 lines
```
06-snowflake-native/
├── snowpark/pii_masking_udf.py          # UDFs for PII masking
├── snowpark/dynamic_table_pipeline.py   # Data pipeline
└── sql/dynamic_tables.sql               # Dynamic table DDL
```

**Installation**:
```bash
cd 06-snowflake-native

# Install dependencies
pip install snowflake-snowpark-python>=1.11.0

# Set environment variables
export SNOWFLAKE_ACCOUNT="xy12345"
export SNOWFLAKE_USER="your-user"
export SNOWFLAKE_PASSWORD="your-password"
```

**Usage**:
```bash
# Register UDFs
python snowpark/pii_masking_udf.py

# Run pipeline
python snowpark/dynamic_table_pipeline.py

# Or deploy dynamic tables
snowsql -f sql/dynamic_tables.sql
```

**Learn more**: [06-snowflake-native/README.md](06-snowflake-native/README.md)

---

### 07. BigQuery + Looker

**What it does**: GA4 analytics pipeline with BigQuery + Looker dashboard refresh

**Files**: 4 files, 2,290 lines
```
07-bigquery-looker/
├── bigquery/scheduled_queries.sql       # GA4 + Ads queries
├── bigquery/partitioning_setup.sql      # Table setup
├── airflow/ga4_to_looker_dag.py         # Orchestration
└── looker/refresh_dashboard.py          # Looker API client
```

**Installation**:
```bash
cd 07-bigquery-looker

# Install dependencies
pip install \
  google-cloud-bigquery>=3.11.0 \
  apache-airflow-providers-google>=10.0.0 \
  looker-sdk>=23.0.0 \
  -c ../../../../constraints.txt

# Authenticate with GCP
gcloud auth application-default login
```

**Usage**:
```bash
# Create tables
bq query --use_legacy_sql=false < bigquery/partitioning_setup.sql

# Run scheduled query
bq query --use_legacy_sql=false < bigquery/scheduled_queries.sql

# Refresh Looker dashboard
python looker/refresh_dashboard.py --dashboard-id 123

# Or use Airflow
airflow dags trigger ga4_to_looker_pipeline
```

**Learn more**: [07-bigquery-looker/README.md](07-bigquery-looker/README.md)

---

### 08. Cost-Optimized Serverless

**What it does**: Event-driven serverless pipeline (AWS Glue + Athena + Step Functions)

**Files**: 4 files, 1,892 lines
```
08-cost-optimized-serverless/
├── glue/spark_job.py                    # Glue ETL script
├── step_functions/orchestration.json    # State machine
├── terraform/infrastructure.tf          # Complete IaC (814 lines)
└── cost_analysis/estimate.md            # Cost breakdown
```

**Installation**:
```bash
cd 08-cost-optimized-serverless

# Install Terraform
brew install terraform  # or download from terraform.io

# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure
```

**Usage**:
```bash
# Deploy infrastructure
cd terraform
terraform init
terraform apply

# Upload test data (triggers pipeline automatically)
aws s3 cp test_data.csv s3://your-input-bucket/

# Query results with Athena
aws athena start-query-execution \
  --query-string "SELECT * FROM processed_data LIMIT 10"
```

**Cost**: ~$642/month for 10TB (optimizable to $192)

**Learn more**: [08-cost-optimized-serverless/README.md](08-cost-optimized-serverless/README.md)

---

### 09. Governed + Secure

**What it does**: Enterprise security with Azure AD, encryption, RLS, audit logging

**Files**: 5 files, 2,702 lines
```
09-governed-secure/
├── airflow/secure_synapse_dag.py        # Azure AD pipeline
├── security/column_encryption.sql       # Always Encrypted
├── security/rls_policies.sql            # Row-level security
├── compliance/audit_log_queries.sql     # Compliance reports
└── security/azure_ad_setup.md           # Setup guide
```

**Installation**:
```bash
cd 09-governed-secure

# Install dependencies
pip install \
  azure-identity>=1.15.0 \
  azure-keyvault-secrets>=4.7.0 \
  pyodbc>=5.0.0 \
  -c ../../../../constraints.txt

# Follow Azure AD setup guide
cat security/azure_ad_setup.md
```

**Usage**:
```bash
# Set up encryption
sqlcmd -S synapse-workspace.sql.azuresynapse.net \
  -d analytics -i security/column_encryption.sql

# Apply RLS policies
sqlcmd -S synapse-workspace.sql.azuresynapse.net \
  -d analytics -i security/rls_policies.sql

# Run secure pipeline
airflow dags trigger secure_synapse_etl

# Generate compliance reports
sqlcmd -i compliance/audit_log_queries.sql -o audit_report.txt
```

**Learn more**: [09-governed-secure/README.md](09-governed-secure/README.md)

---

### 10. AI Feature Store

**What it does**: ML feature engineering with Feast + Snowflake Cortex AI + MLflow

**Files**: 6 files, 1,594 lines + notebook
```
10-ai-feature-store/
├── airflow/feature_engineering_dag.py   # Feature pipeline
├── feature_store/feast_repo/features.py # 30+ features
├── feature_store/feast_repo/feature_store.yaml  # Feast config
├── feature_store/embeddings_generator.py # Text embeddings
├── ml/churn_model_training.py           # XGBoost + MLflow
└── notebooks/feature_exploration.ipynb   # Interactive analysis
```

**Installation**:
```bash
cd 10-ai-feature-store

# Install dependencies
pip install \
  feast[snowflake]>=0.35.0 \
  mlflow>=2.9.0 \
  xgboost>=2.0.0 \
  scikit-learn>=1.3.0 \
  pandas>=2.0.0 \
  numpy>=1.24.0 \
  openai>=1.0.0 \
  matplotlib>=3.7.0 \
  seaborn>=0.12.0 \
  -c ../../../../constraints.txt

# Initialize Feast
cd feature_store/feast_repo
feast apply

# Start Redis for online store
docker run -d --name feast-redis -p 6379:6379 redis:latest
```

**Usage**:
```bash
# Run feature engineering
airflow dags trigger feature_engineering_pipeline

# Generate embeddings
python feature_store/embeddings_generator.py

# Train model
python ml/churn_model_training.py

# Explore features
jupyter notebook notebooks/feature_exploration.ipynb

# Online serving (production)
from feast import FeatureStore
store = FeatureStore("feature_store/feast_repo")
features = store.get_online_features(...)
```

**Learn more**: [10-ai-feature-store/README.md](10-ai-feature-store/README.md)

---

## 🔧 Dependency Management

### Important Notes

1. **Airflow Conflict** (Example 01, 02, 03, 07, 09, 10):
   - Apache Airflow 2.7.3 requires Pydantic v1 and SQLAlchemy 1.4.x
   - Shared libraries require Pydantic v2 and SQLAlchemy 2.0+
   - **Solution**: Deploy Airflow examples in isolated environments (separate virtualenv or Docker)
   - See [../usage.md](usage.md) for detailed deployment modes

2. **Shared Libraries**:
   ```bash
   # Install from correct paths (from within an example directory)
   pip install -e ../../../../shared/common
   pip install -e ../../../../shared/connectors
   pip install -e ../../../../shared/data-contracts  # For example 02
   ```

3. **Constraints File**:
   ```bash
   # Use constraints for version compatibility
   pip install -r requirements.txt -c ../../../../constraints.txt
   ```

### Dependency Matrix

| Example | Requires Airflow? | Requires Shared Libs? | Conflicts? |
|---------|-------------------|-----------------------|------------|
| 01 | ✅ Yes | ❌ No | ⚠️ Airflow conflict |
| 02 | ✅ Yes | ✅ Yes | ⚠️ Airflow conflict |
| 03 | ✅ Yes | ✅ Yes | ⚠️ Airflow conflict |
| 04 | ❌ No | ✅ Yes | ✅ Compatible |
| 05 | ❌ No | ✅ Yes | ✅ Compatible |
| 06 | ❌ No | ❌ No | ✅ Compatible |
| 07 | ✅ Yes | ✅ Yes | ⚠️ Airflow conflict |
| 08 | ❌ No | ❌ No | ✅ Compatible |
| 09 | ✅ Yes | ✅ Yes | ⚠️ Airflow conflict |
| 10 | ✅ Yes | ✅ Yes | ⚠️ Airflow conflict |

---

## 🧪 Testing Your Installation

After installing an example, verify it works:

```bash
# 1. Check Python environment
python --version  # Should be 3.11+

# 2. Verify dependencies
pip list | grep -E "airflow|snowflake|pyspark|feast"

# 3. Run tests (if available)
pytest tests/ -v

# 4. Validate configuration
python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"

# 5. Dry run (for supported examples)
./scripts/setup.sh --dry-run  # Example 01
python scripts/shopify_extractor.py --dry-run  # Example 02
```

---

## 📖 Learning Path

**Recommended progression for learning data engineering:**

### Week 1: Batch Basics
- **Day 1-2**: Example 01 (CSV to Warehouse)
- **Day 3-4**: Example 03 (Oracle to Snowflake)
- **Day 5**: Review dbt models and data quality

### Week 2: APIs and Incremental
- **Day 1-3**: Example 02 (API to Lakehouse)
- **Day 4-5**: Understand Delta Lake merge operations

### Week 3: Advanced Patterns
- **Day 1-3**: Example 04 (Medallion Architecture)
- **Day 4-5**: Example 06 (Snowflake Native)

### Week 4: Real-time and Streaming
- **Day 1-3**: Example 05 (Real-time Streaming)
- **Day 4-5**: Understand watermarking and windowing

### Week 5: Cloud and Security
- **Day 1-2**: Example 08 (Cost-Optimized Serverless)
- **Day 3-5**: Example 09 (Governed + Secure)

### Week 6: ML and Advanced
- **Day 1-5**: Example 10 (AI Feature Store)

---

## 🆘 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Problem: ModuleNotFoundError: No module named 'dataforge_common'
# Solution: Install shared libraries (from example directory)
pip install -e ../../../../shared/common -e ../../../../shared/connectors
```

**2. Airflow Dependency Conflicts**
```bash
# Problem: ERROR: pip's dependency resolver does not currently take into account all the packages...
# Solution: Use isolated environment for Airflow examples
python -m venv venv-airflow
source venv-airflow/bin/activate
pip install -r requirements-airflow.txt  # Example 01
```

**3. Path Issues**
```bash
# Problem: FileNotFoundError: [Errno 2] No such file or directory
# Solution: Ensure you're in the correct directory
cd accelerators/01-pipeline-automation/examples/<example-name>
ls ../../../../shared/  # Should show: common, connectors, data-contracts, ai-core
```

**4. Permission Denied**
```bash
# Problem: Permission denied: './scripts/setup.sh'
# Solution: Make script executable
chmod +x scripts/setup.sh
```

**5. Cloud Authentication**
```bash
# AWS
aws configure

# Azure
az login

# GCP
gcloud auth application-default login

# Snowflake
# Use environment variables or connection profiles
```

---

## 💡 Tips and Best Practices

1. **Start Simple**: Begin with Example 01, then progress to more complex examples

2. **Use Virtual Environments**: Create separate venvs for Airflow vs non-Airflow examples
   ```bash
   python -m venv venv-example01
   source venv-example01/bin/activate
   ```

3. **Read the README**: Each example has detailed documentation - read it first!

4. **Test with Sample Data**: Most examples include sample data for immediate testing

5. **Check Logs**: When things fail, check logs:
   - Airflow: `$AIRFLOW_HOME/logs/`
   - Spark: `spark.driver.extraJavaOptions=-Dlog4j.configuration=...`
   - General: Python's `logging` module output

6. **Use Dry Run**: Many scripts support `--dry-run` to validate without execution

---

## 🤝 Contributing

Found a bug? Want to add a new example? See [CONTRIBUTING.md](../../../CONTRIBUTING.md)

---

## 📚 Additional Resources

- **Main Accelerator README**: [../../README.md](../../README.md)
- **Dependency Guide**: [../../../docs/DEPENDENCIES.md](../../../docs/DEPENDENCIES.md)
- **Usage Guide**: [usage.md](usage.md)
- **Constraints File**: [../../../constraints.txt](../../../constraints.txt)

---

## 📝 Summary

You now have **10 production-ready pipeline examples** covering:
- ✅ Batch ingestion (CSV, databases)
- ✅ API integration (REST, incremental)
- ✅ Streaming (real-time, windowing)
- ✅ Data warehouses (Snowflake, BigQuery, Synapse)
- ✅ Lakehouses (Delta Lake, medallion architecture)
- ✅ Security (encryption, RLS, auditing)
- ✅ ML (feature stores, model training)
- ✅ Cost optimization (serverless)

**Total Code**: 43 files, 20,884 lines, fully functional

**Start exploring and building!** 🚀
