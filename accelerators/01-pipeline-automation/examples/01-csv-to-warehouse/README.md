# Example 01: Classic File-to-Warehouse Batch Load

**The "Hello World" demo – 2-minute win**

## Overview

This example demonstrates a foundational batch data pipeline pattern: ingesting daily CSV sales files from S3, applying basic cleansing (deduplication, date fixes, adding load timestamps), and landing the data in Snowflake using the medallion architecture (bronze → silver) with dbt transformations.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌────────────────┐
│   S3 Bucket │────▶│ Airflow DAG  │────▶│ Snowflake      │────▶│ dbt Models     │
│ sales/*.csv │     │ (Orchestrate)│     │ sales.bronze.  │     │ bronze → silver│
└─────────────┘     └──────────────┘     │ sales_raw      │     └────────────────┘
                                          └────────────────┘
                                                  │
                                                  ▼
                                          ┌────────────────┐
                                          │ sales.silver.  │
                                          │ sales_clean    │
                                          └────────────────┘
```

## Use Case

Every data team needs to ingest files into a warehouse. This example shows:
- Scheduled file ingestion from cloud storage
- Basic data quality checks
- Idempotent loads (can rerun safely)
- Medallion architecture best practices
- dbt for SQL transformations

## Prerequisites

- **Airflow:** Running instance (see main [usage.md](../usage.md) for setup)
- **Snowflake Account:** With database and schema created
- **AWS S3 Bucket:** With sample CSV files (or use provided sample data)
- **Credentials:** Snowflake connection configured in Airflow

## Quick Start

### 1. Configure Connections

```bash
# Set Airflow variables
airflow variables set s3_bucket "your-bucket-name"
airflow variables set s3_prefix "sales/"

# Create Snowflake connection in Airflow UI or CLI
airflow connections add 'snowflake_default' \
    --conn-type 'snowflake' \
    --conn-login 'your_user' \
    --conn-password 'your_password' \
    --conn-schema 'sales' \
    --conn-extra '{"account": "your_account", "warehouse": "COMPUTE_WH", "database": "ANALYTICS", "role": "ANALYST"}'
```

### 2. Upload Sample Data

```bash
# Upload sample CSV to S3
aws s3 cp sample_data/sales_2024_11.csv s3://your-bucket/sales/

# Or use the setup script
./scripts/setup.sh
```

### 3. Deploy DAG

```bash
# Copy DAG to Airflow dags folder
cp airflow/sales_ingestion_dag.py $AIRFLOW_HOME/dags/

# Trigger the DAG
airflow dags trigger sales_csv_to_snowflake
```

### 4. Run dbt Transformations

```bash
# Navigate to dbt project
cd dbt/

# Run models
dbt run --models sales

# Run tests
dbt test --models sales
```

## Expected Results

After running the pipeline:

1. **Bronze Layer** (`sales.bronze.sales_raw`):
   - Raw CSV data loaded as-is
   - Load timestamp added
   - All records preserved (including duplicates)

2. **Silver Layer** (`sales.silver.sales_clean`):
   - Duplicates removed
   - Date formats standardized
   - Invalid records filtered out
   - Ready for analytics

## What You'll Learn

- ✅ Airflow DAG creation and scheduling
- ✅ S3 sensor for file detection
- ✅ Snowflake bulk loading with COPY INTO
- ✅ dbt models for transformations
- ✅ dbt tests for data quality
- ✅ Medallion architecture patterns
- ✅ Idempotent pipeline design

## File Structure

```
01-csv-to-warehouse/
├── README.md                         # This file
├── config.yaml                       # Configuration
├── airflow/
│   └── sales_ingestion_dag.py       # Airflow DAG
├── dbt/
│   ├── models/
│   │   ├── bronze/
│   │   │   └── sales_raw.sql        # Bronze layer model
│   │   └── silver/
│   │       └── sales_clean.sql      # Silver layer model
│   └── tests/
│       └── sales_data_quality.sql   # Data quality tests
├── sample_data/
│   └── sales_2024_11.csv            # Sample data
└── scripts/
    └── setup.sh                      # Setup automation
```

## Configuration

Edit `config.yaml` to customize:

```yaml
# S3 source
s3_bucket: "your-bucket"
s3_prefix: "sales/"
file_pattern: "sales_*.csv"

# Snowflake target
snowflake_database: "ANALYTICS"
snowflake_schema: "sales"
bronze_table: "bronze.sales_raw"
silver_table: "silver.sales_clean"

# Schedule
schedule_interval: "@daily"  # Run daily at midnight
```

## Customization Guide

### Change Data Source

Replace S3 with other sources:
- **Local files:** Use `FileSensor` instead of `S3KeySensor`
- **SFTP:** Use `SFTPSensor` and `SFTPOperator`
- **GCS:** Use `GCSObjectExistenceSensor`

### Change Target Warehouse

Adapt for other warehouses:
- **Redshift:** Change connection type and use COPY command
- **BigQuery:** Use `BigQueryInsertJobOperator`
- **Databricks:** Use Databricks SQL connector

### Add Data Quality Checks

In `dbt/tests/sales_data_quality.sql`:
```sql
-- Check for future dates
SELECT * FROM {{ ref('sales_clean') }}
WHERE sale_date > CURRENT_DATE

-- Check for negative amounts
SELECT * FROM {{ ref('sales_clean') }}
WHERE amount < 0
```

## Troubleshooting

### DAG Not Appearing

**Issue:** DAG doesn't show in Airflow UI

**Solution:**
```bash
# Check DAG syntax
python airflow/sales_ingestion_dag.py

# Verify it's in the dags folder
ls $AIRFLOW_HOME/dags/ | grep sales

# Check Airflow logs
airflow dags list-import-errors
```

### Snowflake Connection Failed

**Issue:** `snowflake.connector.errors.DatabaseError`

**Solution:**
- Verify credentials in Airflow connection
- Check network connectivity to Snowflake
- Ensure role has necessary privileges:
  ```sql
  GRANT USAGE ON DATABASE ANALYTICS TO ROLE ANALYST;
  GRANT USAGE ON SCHEMA sales TO ROLE ANALYST;
  GRANT CREATE TABLE ON SCHEMA sales TO ROLE ANALYST;
  ```

### S3 File Not Found

**Issue:** S3KeySensor times out

**Solution:**
```bash
# Verify file exists
aws s3 ls s3://your-bucket/sales/

# Check IAM permissions
aws s3 cp s3://your-bucket/sales/test.csv - --dryrun

# Review Airflow connection for S3
airflow connections get aws_default
```

### dbt Run Fails

**Issue:** `dbt run` fails with relation not found

**Solution:**
```bash
# Verify target is set correctly
dbt debug

# Check profile configuration
cat ~/.dbt/profiles.yml

# Ensure bronze table exists first
dbt run --models bronze.sales_raw
```

## Performance Tuning

### For Large Files (> 1 GB)

```python
# In Airflow DAG, increase timeout
s3_sensor = S3KeySensor(
    timeout=3600,  # 1 hour
    poke_interval=300  # Check every 5 minutes
)

# In Snowflake, use larger warehouse
ALTER WAREHOUSE COMPUTE_WH SET WAREHOUSE_SIZE = 'LARGE';
```

### For Many Small Files

```sql
-- In bronze model, use PATTERN instead of loading individually
COPY INTO sales.bronze.sales_raw
FROM @sales_stage
PATTERN = 'sales_.*\.csv'
FILE_FORMAT = (TYPE = CSV);
```

## Next Steps

After mastering this example:

1. **Add incrementality** - Track which files have been processed
2. **Add data validation** - Use Great Expectations (see accelerator 02)
3. **Add notifications** - Send alerts on failure
4. **Scale to multiple sources** - Replicate pattern for other datasets
5. **Try Example 02** - API to Lakehouse for near-real-time ingestion

## Resources

- [Airflow S3 Operators](https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/operators/s3.html)
- [Snowflake COPY INTO](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table.html)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
- [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)

## Support

For issues specific to this example, please include:
- Airflow task logs
- dbt run output
- Configuration files (with credentials redacted)
