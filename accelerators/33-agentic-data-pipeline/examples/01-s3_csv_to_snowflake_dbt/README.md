# S3 CSV to Snowflake with dbt - Pipeline Example

## Overview

This example demonstrates a classic batch ETL pipeline that ingests CSV files from Amazon S3, loads them into Snowflake's bronze layer, and transforms them through to a silver layer using dbt (Data Build Tool) with medallion architecture.

**Business Use Case:** Daily sales data ingestion from operational systems that export to S3, with data quality validation and cleansing before making available to analysts.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│   S3 CSV    │────▶│   Airflow    │────▶│  Snowflake  │────▶│   dbt       │
│   Bucket    │     │   Sensor +   │     │   Bronze    │     │  Silver     │
│             │     │   COPY INTO  │     │   Layer     │     │  Transform  │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
```

## Key Features

- ✅ **Medallion Architecture**: Bronze (raw) → Silver (cleansed) layers
- ✅ **Incremental Processing**: Only processes new data using watermarks
- ✅ **Data Quality**: dbt tests for uniqueness, nullability, and range checks
- ✅ **Error Handling**: Continues on error with logging to separate error table
- ✅ **Cost Optimized**: Uses Snowflake's COPY INTO for efficient bulk loading
- ✅ **Idempotent**: Safe to re-run without duplicating data

## Generated Prompt

```
Ingest daily CSV sales files from S3, apply basic cleansing (dedupe, fix dates,
add load timestamp), and load into Snowflake sales.bronze.sales_raw then
sales.silver.sales_clean using dbt.
```

## Technology Stack

- **Cloud Storage**: Amazon S3
- **Data Warehouse**: Snowflake
- **Orchestration**: Apache Airflow 2.8+
- **Transformation**: dbt 1.7+ with dbt-snowflake
- **Data Quality**: dbt tests + dbt-expectations

## Estimated Costs

- **Snowflake**: ~$50-100/month (assuming 10GB data, daily loads, XS warehouse)
- **Airflow**: $20-50/month (if using managed service like Astronomer)
- **S3**: ~$5/month (100GB storage + data transfer)

**Total**: ~$75-155/month

## Prerequisites

1. AWS account with S3 bucket access
2. Snowflake account (trial accounts work!)
3. Airflow 2.8+ deployment (local, Astronomer, MWAA, Cloud Composer)
4. Python 3.10+

## Quick Start

### 1. Set Up Snowflake

```sql
-- Create database and schemas
CREATE DATABASE IF NOT EXISTS sales;
CREATE SCHEMA IF NOT EXISTS sales.bronze;
CREATE SCHEMA IF NOT EXISTS sales.silver;

-- Create storage integration (replace with your IAM role)
CREATE OR REPLACE STORAGE INTEGRATION s3_sales_integration
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::YOUR_ACCOUNT:role/SnowflakeS3Access'
  STORAGE_ALLOWED_LOCATIONS = ('s3://your-bucket/raw/sales/');

-- Create external stage
CREATE OR REPLACE STAGE sales.bronze.s3_sales_stage
  STORAGE_INTEGRATION = s3_sales_integration
  URL = 's3://your-bucket/raw/sales/'
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

-- Create bronze table
CREATE OR REPLACE TABLE sales.bronze.sales_raw (
  sale_id VARCHAR,
  sale_date VARCHAR,
  customer_id VARCHAR,
  product_id VARCHAR,
  quantity VARCHAR,
  amount VARCHAR,
  region VARCHAR,
  _metadata$filename VARCHAR,
  _metadata$file_row_number NUMBER,
  loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

### 2. Configure Airflow Connections

```bash
# Snowflake connection
airflow connections add 'snowflake_default' \
    --conn-type 'snowflake' \
    --conn-login 'YOUR_USER' \
    --conn-password 'YOUR_PASSWORD' \
    --conn-schema 'sales' \
    --conn-extra '{"account": "xy12345.us-east-1", "warehouse": "COMPUTE_WH", "database": "sales", "role": "SYSADMIN"}'

# AWS connection
airflow connections add 'aws_default' \
    --conn-type 'aws' \
    --conn-extra '{"aws_access_key_id": "YOUR_KEY", "aws_secret_access_key": "YOUR_SECRET"}'
```

### 3. Install Dependencies

```bash
pip install apache-airflow==2.8.0
pip install apache-airflow-providers-snowflake==5.2.0
pip install apache-airflow-providers-amazon==8.15.0
pip install dbt-snowflake==1.7.0
pip install dbt-expectations==0.10.0
```

### 4. Deploy

```bash
# Copy DAG
cp dags/s3_to_snowflake_dag.py $AIRFLOW_HOME/dags/

# Set up dbt project
cp -r dbt/ $AIRFLOW_HOME/
cd $AIRFLOW_HOME/dbt
dbt deps  # Install dbt packages

# Create profiles.yml for dbt
cat > ~/.dbt/profiles.yml << EOF
snowflake_sales:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: YOUR_ACCOUNT
      user: YOUR_USER
      password: YOUR_PASSWORD
      role: SYSADMIN
      database: sales
      warehouse: COMPUTE_WH
      schema: silver
      threads: 4
EOF

# Test dbt connection
dbt debug --profiles-dir ~/.dbt
```

### 5. Upload Sample Data

```bash
# Create sample CSV
cat > sales_2025-01-01.csv << EOF
sale_id,sale_date,customer_id,product_id,quantity,amount,region
1001,2025-01-01,C001,P100,2,150.00,US-WEST
1002,2025-01-01,C002,P101,1,75.50,US-EAST
EOF

# Upload to S3
aws s3 cp sales_2025-01-01.csv s3://your-bucket/raw/sales/2025-01-01/
```

### 6. Run the Pipeline

```bash
# Test the DAG
airflow dags test s3_csv_to_snowflake_dbt 2025-01-01

# Trigger manually
airflow dags trigger s3_csv_to_snowflake_dbt

# Enable for scheduled runs (daily at 2 AM)
airflow dags unpause s3_csv_to_snowflake_dbt
```

## Monitoring

### Check Data Loaded

```sql
-- Check bronze layer
SELECT
    COUNT(*) as total_rows,
    MAX(loaded_at) as last_load_time,
    COUNT(DISTINCT _metadata$filename) as files_processed
FROM sales.bronze.sales_raw;

-- Check silver layer
SELECT
    COUNT(*) as total_rows,
    MAX(transformed_at) as last_transform_time,
    SUM(amount) as total_sales
FROM sales.silver.sales_clean;
```

### View dbt Test Results

```bash
# Run dbt tests
cd $AIRFLOW_HOME/dbt
dbt test --models silver.sales_clean

# Generate and view documentation
dbt docs generate
dbt docs serve
```

## Customization

### Add More dbt Tests

Edit `dbt/models/silver/schema.yml`:

```yaml
- name: amount
  tests:
    - not_null
    - dbt_expectations.expect_column_values_to_be_between:
        min_value: 0
        max_value: 1000000
    - dbt_expectations.expect_column_mean_to_be_between:
        min_value: 50
        max_value: 500
```

### Add Data Quality Alerts

Edit the Airflow DAG to add email alerts:

```python
from airflow.operators.email import EmailOperator

send_alert = EmailOperator(
    task_id='send_quality_alert',
    to='data-team@company.com',
    subject='Data Quality Issue in Sales Pipeline',
    html_content='...'
)
```

## Troubleshooting

### Issue: COPY INTO fails with "File not found"

**Solution**: Check S3 path and IAM role permissions. Verify with:
```sql
LIST @sales.bronze.s3_sales_stage;
```

### Issue: dbt tests failing on freshness

**Solution**: Adjust the `updated_at` column configuration in `schema.yml`:
```yaml
freshness:
  warn_after: {count: 24, period: hour}
  error_after: {count: 48, period: hour}
```

## Next Steps

- Add Gold layer for business metrics (daily/monthly aggregations)
- Implement SCD Type 2 for customer dimension tracking
- Add Great Expectations for advanced data validation
- Set up dbt Cloud for scheduled runs and documentation hosting
- Implement data lineage tracking with dbt + Snowflake

## Support

For issues or questions:
- Check Airflow logs: `$AIRFLOW_HOME/logs/`
- Check dbt logs: `$AIRFLOW_HOME/dbt/logs/`
- Snowflake query history: https://app.snowflake.com → History
