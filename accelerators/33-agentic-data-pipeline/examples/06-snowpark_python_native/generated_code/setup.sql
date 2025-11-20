-- Snowpark Python Native Pipeline Setup
-- This script creates all required objects in Snowflake

-- Create databases and schemas
CREATE DATABASE IF NOT EXISTS ANALYTICS;
CREATE SCHEMA IF NOT EXISTS ANALYTICS.RAW;
CREATE SCHEMA IF NOT EXISTS ANALYTICS.CLEAN;
CREATE SCHEMA IF NOT EXISTS ANALYTICS.METRICS;
CREATE SCHEMA IF NOT EXISTS ANALYTICS.PROCEDURES;
CREATE SCHEMA IF NOT EXISTS ANALYTICS.STAGES;

-- Create S3 external stage
CREATE OR REPLACE STAGE ANALYTICS.STAGES.S3_SALES_STAGE
  URL = 's3://your-bucket/sales-data/'
  CREDENTIALS = (AWS_KEY_ID = 'your-key' AWS_SECRET_KEY = 'your-secret')
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

-- Create stage for Python code
CREATE OR REPLACE STAGE ANALYTICS.STAGES.PYTHON_CODE;

-- Create raw sales table
CREATE OR REPLACE TABLE ANALYTICS.RAW.SALES (
    sale_id VARCHAR(50),
    sale_date VARCHAR(50),
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    quantity INTEGER,
    unit_price DECIMAL(10, 2),
    total_amount DECIMAL(10, 2),
    region VARCHAR(50),
    store_id VARCHAR(50),
    payment_method VARCHAR(50),
    ingested_at TIMESTAMP_NTZ,
    execution_date DATE,
    source_file VARCHAR(200)
);

-- Create clean sales table
CREATE OR REPLACE TRANSIENT TABLE ANALYTICS.CLEAN.SALES (
    sale_id VARCHAR(50),
    sale_date DATE,
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    quantity INTEGER,
    unit_price DECIMAL(10, 2),
    total_amount DECIMAL(10, 2),
    discount_rate DECIMAL(5, 2),
    discount_amount DECIMAL(10, 2),
    final_amount DECIMAL(10, 2),
    region VARCHAR(50),
    store_id VARCHAR(50),
    payment_method VARCHAR(50),
    payment_category VARCHAR(20),
    quality_flag VARCHAR(20),
    execution_date DATE,
    transformed_at TIMESTAMP_NTZ
);

-- Create metrics tables
CREATE OR REPLACE TABLE ANALYTICS.METRICS.DAILY_OVERALL (
    total_transactions INTEGER,
    total_revenue DECIMAL(18, 2),
    avg_transaction_value DECIMAL(10, 2),
    min_transaction_value DECIMAL(10, 2),
    max_transaction_value DECIMAL(10, 2),
    unique_customers INTEGER,
    unique_products INTEGER,
    total_units_sold INTEGER,
    total_discounts DECIMAL(18, 2),
    metric_date DATE,
    calculated_at TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE ANALYTICS.METRICS.DAILY_BY_REGION (
    region VARCHAR(50),
    transactions INTEGER,
    revenue DECIMAL(18, 2),
    avg_value DECIMAL(10, 2),
    unique_customers INTEGER,
    metric_date DATE,
    metric_type VARCHAR(20),
    calculated_at TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE ANALYTICS.METRICS.DAILY_BY_PAYMENT (
    payment_category VARCHAR(20),
    transactions INTEGER,
    revenue DECIMAL(18, 2),
    avg_value DECIMAL(10, 2),
    metric_date DATE,
    metric_type VARCHAR(20),
    calculated_at TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE ANALYTICS.METRICS.DAILY_BY_PRODUCT (
    product_id VARCHAR(50),
    transactions INTEGER,
    units_sold INTEGER,
    revenue DECIMAL(18, 2),
    avg_price DECIMAL(10, 2),
    metric_date DATE,
    metric_type VARCHAR(20),
    calculated_at TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE ANALYTICS.METRICS.DAILY_BY_STORE (
    store_id VARCHAR(50),
    region VARCHAR(50),
    transactions INTEGER,
    revenue DECIMAL(18, 2),
    unique_customers INTEGER,
    metric_date DATE,
    metric_type VARCHAR(20),
    calculated_at TIMESTAMP_NTZ
);

-- Upload Python procedures to stage
-- PUT file://procedures/ingest_sales_data.py @ANALYTICS.STAGES.PYTHON_CODE;
-- PUT file://procedures/transform_sales_data.py @ANALYTICS.STAGES.PYTHON_CODE;
-- PUT file://procedures/aggregate_metrics.py @ANALYTICS.STAGES.PYTHON_CODE;

-- Create stored procedures
CREATE OR REPLACE PROCEDURE ANALYTICS.PROCEDURES.INGEST_SALES_DATA(execution_date STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
IMPORTS = ('@ANALYTICS.STAGES.PYTHON_CODE/ingest_sales_data.py')
AS $$
# Code is imported from the uploaded file
$$;

CREATE OR REPLACE PROCEDURE ANALYTICS.PROCEDURES.TRANSFORM_SALES_DATA(execution_date STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
IMPORTS = ('@ANALYTICS.STAGES.PYTHON_CODE/transform_sales_data.py')
AS $$
# Code is imported from the uploaded file
$$;

CREATE OR REPLACE PROCEDURE ANALYTICS.PROCEDURES.AGGREGATE_METRICS(execution_date STRING)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
IMPORTS = ('@ANALYTICS.STAGES.PYTHON_CODE/aggregate_metrics.py')
AS $$
# Code is imported from the uploaded file
$$;

-- Create Snowflake Tasks
CREATE OR REPLACE TASK ANALYTICS.PROCEDURES.INGEST_SALES_TASK
  WAREHOUSE = 'COMPUTE_WH'
  SCHEDULE = 'USING CRON 0 2 * * * America/Los_Angeles'
AS
  CALL ANALYTICS.PROCEDURES.INGEST_SALES_DATA(TO_VARCHAR(CURRENT_DATE(), 'YYYY-MM-DD'));

CREATE OR REPLACE TASK ANALYTICS.PROCEDURES.TRANSFORM_SALES_TASK
  WAREHOUSE = 'COMPUTE_WH'
  AFTER ANALYTICS.PROCEDURES.INGEST_SALES_TASK
AS
  CALL ANALYTICS.PROCEDURES.TRANSFORM_SALES_DATA(TO_VARCHAR(CURRENT_DATE(), 'YYYY-MM-DD'));

CREATE OR REPLACE TASK ANALYTICS.PROCEDURES.AGGREGATE_METRICS_TASK
  WAREHOUSE = 'COMPUTE_WH'
  AFTER ANALYTICS.PROCEDURES.TRANSFORM_SALES_TASK
AS
  CALL ANALYTICS.PROCEDURES.AGGREGATE_METRICS(TO_VARCHAR(CURRENT_DATE(), 'YYYY-MM-DD'));

-- Enable tasks (run manually)
-- ALTER TASK ANALYTICS.PROCEDURES.AGGREGATE_METRICS_TASK RESUME;
-- ALTER TASK ANALYTICS.PROCEDURES.TRANSFORM_SALES_TASK RESUME;
-- ALTER TASK ANALYTICS.PROCEDURES.INGEST_SALES_TASK RESUME;

-- Test procedures manually
-- CALL ANALYTICS.PROCEDURES.INGEST_SALES_DATA('2025-01-15');
-- CALL ANALYTICS.PROCEDURES.TRANSFORM_SALES_DATA('2025-01-15');
-- CALL ANALYTICS.PROCEDURES.AGGREGATE_METRICS('2025-01-15');
