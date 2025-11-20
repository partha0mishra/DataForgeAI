/*
 * Snowflake Dynamic Tables DDL
 *
 * This script demonstrates Snowflake Dynamic Tables for automated data pipeline refresh.
 * Dynamic Tables automatically and incrementally refresh based on changes in upstream data.
 *
 * Features:
 * - External stage configuration for S3/Azure/GCS
 * - File format definitions
 * - Bronze/Silver/Gold layered architecture
 * - Incremental refresh with configurable target lag
 * - Dependency chain management
 * - Near-real-time data availability
 *
 * Prerequisites:
 * - Snowflake account with Dynamic Tables feature enabled
 * - ACCOUNTADMIN or appropriate privileges
 * - External cloud storage configured (S3/Azure/GCS)
 * - PII masking UDFs registered (from pii_masking_udf.py)
 *
 * Usage:
 *   snowsql -f dynamic_tables.sql
 *   OR
 *   Execute in Snowflake worksheet
 */

-- ============================================================================
-- SETUP: Database, Schema, and Warehouse
-- ============================================================================

USE ROLE ACCOUNTADMIN;

CREATE DATABASE IF NOT EXISTS ANALYTICS
    COMMENT = 'Analytics database for dynamic table pipeline';

CREATE SCHEMA IF NOT EXISTS ANALYTICS.SALES
    COMMENT = 'Sales data pipeline schema';

USE DATABASE ANALYTICS;
USE SCHEMA SALES;

CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
    WITH WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    COMMENT = 'Compute warehouse for data processing';

USE WAREHOUSE COMPUTE_WH;

-- ============================================================================
-- EXTERNAL STAGE CONFIGURATION
-- ============================================================================

-- Create file format for CSV files
CREATE OR REPLACE FILE FORMAT CSV_FORMAT
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    NULL_IF = ('NULL', 'null', '')
    EMPTY_FIELD_AS_NULL = TRUE
    COMPRESSION = AUTO
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE
    DATE_FORMAT = 'YYYY-MM-DD'
    TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS'
    COMMENT = 'CSV file format for sales data';

-- Create external stage pointing to S3 (update with your credentials)
-- For S3:
CREATE OR REPLACE STAGE sales_csvs
    URL = 's3://my-bucket/sales/'
    CREDENTIALS = (
        AWS_KEY_ID = 'your_aws_key_id'
        AWS_SECRET_KEY = 'your_aws_secret_key'
    )
    FILE_FORMAT = CSV_FORMAT
    COMMENT = 'External stage for sales CSV files from S3';

-- Alternative: For Azure Blob Storage
/*
CREATE OR REPLACE STAGE sales_csvs
    URL = 'azure://myaccount.blob.core.windows.net/mycontainer/sales/'
    CREDENTIALS = (
        AZURE_SAS_TOKEN = 'your_sas_token'
    )
    FILE_FORMAT = CSV_FORMAT
    COMMENT = 'External stage for sales CSV files from Azure';
*/

-- Alternative: For Google Cloud Storage
/*
CREATE OR REPLACE STAGE sales_csvs
    URL = 'gcs://my-bucket/sales/'
    STORAGE_INTEGRATION = gcs_integration
    FILE_FORMAT = CSV_FORMAT
    COMMENT = 'External stage for sales CSV files from GCS';
*/

-- List files in the stage to verify connectivity
-- LIST @sales_csvs;

-- ============================================================================
-- BRONZE LAYER: Raw Data Ingestion
-- ============================================================================

-- Bronze table: Raw data from external stage
-- This is a regular table that serves as the base for dynamic tables
CREATE OR REPLACE TABLE SALES_BRONZE (
    TRANSACTION_ID VARCHAR(50),
    CUSTOMER_ID INTEGER,
    CUSTOMER_NAME VARCHAR(100),
    CUSTOMER_EMAIL VARCHAR(100),
    CUSTOMER_SSN VARCHAR(11),
    PRODUCT_ID INTEGER,
    PRODUCT_NAME VARCHAR(200),
    QUANTITY INTEGER,
    UNIT_PRICE DECIMAL(10, 2),
    TOTAL_AMOUNT DECIMAL(10, 2),
    TRANSACTION_DATE DATE,
    PAYMENT_METHOD VARCHAR(50),
    CREDIT_CARD VARCHAR(19),
    REGION VARCHAR(50),
    STORE_ID INTEGER,
    METADATA VARIANT,
    LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE VARCHAR(500)
)
COMMENT = 'Bronze layer: Raw sales data from external stage';

-- Alternative: Load from external stage using COPY INTO
-- This would typically be scheduled or triggered by Snowpipe
/*
COPY INTO SALES_BRONZE
FROM @sales_csvs
FILE_FORMAT = CSV_FORMAT
PATTERN = '.*sales_.*\.csv'
ON_ERROR = 'CONTINUE'
FORCE = FALSE;
*/

-- For demonstration, insert sample data
INSERT INTO SALES_BRONZE (
    TRANSACTION_ID, CUSTOMER_ID, CUSTOMER_NAME, CUSTOMER_EMAIL, CUSTOMER_SSN,
    PRODUCT_ID, PRODUCT_NAME, QUANTITY, UNIT_PRICE, TOTAL_AMOUNT,
    TRANSACTION_DATE, PAYMENT_METHOD, CREDIT_CARD, REGION, STORE_ID,
    SOURCE_FILE
)
VALUES
    ('TXN001', 1, 'John Doe', 'john.doe@email.com', '123-45-6789', 101, 'Laptop', 1, 1200.00, 1200.00, '2024-01-15', 'Credit Card', '1234-5678-9012-3456', 'West', 1, 'sales_2024_01_15.csv'),
    ('TXN002', 2, 'Jane Smith', 'jane.smith@company.com', '987-65-4321', 102, 'Mouse', 2, 25.00, 50.00, '2024-01-15', 'Credit Card', '9876-5432-1098-7654', 'East', 2, 'sales_2024_01_15.csv'),
    ('TXN003', 3, 'Bob Johnson', 'bob.j@test.com', '456-78-9012', 103, 'Keyboard', 1, 75.00, 75.00, '2024-01-16', 'Debit Card', '4567890123456789', 'West', 1, 'sales_2024_01_16.csv'),
    ('TXN004', 1, 'John Doe', 'john.doe@email.com', '123-45-6789', 104, 'Monitor', 2, 300.00, 600.00, '2024-01-16', 'Credit Card', '1234-5678-9012-3456', 'West', 3, 'sales_2024_01_16.csv'),
    ('TXN005', 4, 'Alice Williams', 'alice.williams@example.org', '321-54-9876', 105, 'Desk', 1, 450.00, 450.00, '2024-01-17', 'Credit Card', '3210-9876-5432-1098', 'North', 4, 'sales_2024_01_17.csv'),
    ('TXN006', 2, 'Jane Smith', 'jane.smith@company.com', '987-65-4321', 106, 'Chair', 1, 200.00, 200.00, '2024-01-17', 'PayPal', NULL, 'East', 2, 'sales_2024_01_17.csv'),
    ('TXN007', 5, 'Charlie Brown', 'cb@domain.com', '654-32-1098', 107, 'Webcam', 1, 80.00, 80.00, '2024-01-18', 'Credit Card', '6543-2109-8765-4321', 'South', 5, 'sales_2024_01_18.csv'),
    ('TXN008', 3, 'Bob Johnson', 'bob.j@test.com', '456-78-9012', 108, 'Headphones', 1, 120.00, 120.00, '2024-01-18', 'Debit Card', '4567890123456789', 'West', 1, 'sales_2024_01_18.csv'),
    ('TXN009', 4, 'Alice Williams', 'alice.williams@example.org', '321-54-9876', 109, 'USB Hub', 3, 15.00, 45.00, '2024-01-19', 'Credit Card', '3210-9876-5432-1098', 'North', 4, 'sales_2024_01_19.csv'),
    ('TXN010', 1, 'John Doe', 'john.doe@email.com', '123-45-6789', 110, 'Cable', 5, 8.00, 40.00, '2024-01-19', 'Credit Card', '1234-5678-9012-3456', 'West', 3, 'sales_2024_01_19.csv');

-- ============================================================================
-- SILVER LAYER: Cleaned and Masked Data (Dynamic Table)
-- ============================================================================

-- Silver dynamic table: Cleaned data with PII masking
-- Automatically refreshes every 5 minutes when bronze data changes
-- NOTE: PII masking UDFs must be created first (run pii_masking_udf.py)
CREATE OR REPLACE DYNAMIC TABLE SALES_SILVER
    TARGET_LAG = '5 MINUTES'
    WAREHOUSE = COMPUTE_WH
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    COMMENT = 'Silver layer: Cleaned and PII-masked sales data with 5-minute refresh'
AS
SELECT
    TRANSACTION_ID,
    CUSTOMER_ID,
    CUSTOMER_NAME,
    -- Apply PII masking UDFs (ensure these are created first)
    TRY_CAST(MASK_EMAIL(CUSTOMER_EMAIL) AS VARCHAR(100)) AS CUSTOMER_EMAIL,
    TRY_CAST(MASK_SSN(CUSTOMER_SSN) AS VARCHAR(11)) AS CUSTOMER_SSN,
    PRODUCT_ID,
    PRODUCT_NAME,
    QUANTITY,
    UNIT_PRICE,
    TOTAL_AMOUNT,
    TRANSACTION_DATE,
    PAYMENT_METHOD,
    -- Mask credit card, handling NULL values
    CASE
        WHEN CREDIT_CARD IS NOT NULL THEN TRY_CAST(MASK_CREDIT_CARD(CREDIT_CARD) AS VARCHAR(19))
        ELSE NULL
    END AS CREDIT_CARD,
    REGION,
    STORE_ID,
    LOADED_AT,
    SOURCE_FILE,
    CURRENT_TIMESTAMP() AS PROCESSED_AT
FROM SALES_BRONZE
WHERE TRANSACTION_ID IS NOT NULL
  AND CUSTOMER_ID IS NOT NULL
  AND TOTAL_AMOUNT IS NOT NULL
  AND QUANTITY > 0
  AND UNIT_PRICE > 0
  AND TOTAL_AMOUNT > 0;

-- ============================================================================
-- GOLD LAYER: Aggregated Analytics (Dynamic Tables)
-- ============================================================================

-- Gold dynamic table 1: Daily sales summary
-- Refreshes every 10 minutes, depends on silver layer
CREATE OR REPLACE DYNAMIC TABLE SALES_GOLD_DAILY
    TARGET_LAG = '10 MINUTES'
    WAREHOUSE = COMPUTE_WH
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    COMMENT = 'Gold layer: Daily sales aggregations with 10-minute refresh'
AS
SELECT
    TRANSACTION_DATE,
    REGION,
    COUNT(DISTINCT CUSTOMER_ID) AS UNIQUE_CUSTOMERS,
    COUNT(*) AS TOTAL_TRANSACTIONS,
    SUM(QUANTITY) AS TOTAL_ITEMS_SOLD,
    SUM(TOTAL_AMOUNT) AS TOTAL_REVENUE,
    AVG(TOTAL_AMOUNT) AS AVG_TRANSACTION_VALUE,
    MIN(TOTAL_AMOUNT) AS MIN_TRANSACTION_VALUE,
    MAX(TOTAL_AMOUNT) AS MAX_TRANSACTION_VALUE,
    -- Payment method breakdown
    COUNT(CASE WHEN PAYMENT_METHOD = 'Credit Card' THEN 1 END) AS CREDIT_CARD_TRANSACTIONS,
    COUNT(CASE WHEN PAYMENT_METHOD = 'Debit Card' THEN 1 END) AS DEBIT_CARD_TRANSACTIONS,
    COUNT(CASE WHEN PAYMENT_METHOD = 'PayPal' THEN 1 END) AS PAYPAL_TRANSACTIONS,
    CURRENT_TIMESTAMP() AS REFRESHED_AT
FROM SALES_SILVER
GROUP BY TRANSACTION_DATE, REGION
ORDER BY TRANSACTION_DATE, REGION;

-- Gold dynamic table 2: Customer lifetime value
-- Refreshes every 15 minutes
CREATE OR REPLACE DYNAMIC TABLE SALES_GOLD_CUSTOMER
    TARGET_LAG = '15 MINUTES'
    WAREHOUSE = COMPUTE_WH
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    COMMENT = 'Gold layer: Customer analytics with 15-minute refresh'
AS
SELECT
    CUSTOMER_ID,
    CUSTOMER_NAME,
    CUSTOMER_EMAIL,
    COUNT(*) AS TOTAL_PURCHASES,
    SUM(QUANTITY) AS TOTAL_ITEMS,
    SUM(TOTAL_AMOUNT) AS LIFETIME_VALUE,
    AVG(TOTAL_AMOUNT) AS AVG_ORDER_VALUE,
    MIN(TRANSACTION_DATE) AS FIRST_PURCHASE_DATE,
    MAX(TRANSACTION_DATE) AS LAST_PURCHASE_DATE,
    DATEDIFF(DAY, MIN(TRANSACTION_DATE), MAX(TRANSACTION_DATE)) AS CUSTOMER_TENURE_DAYS,
    COUNT(DISTINCT REGION) AS REGIONS_SHOPPED,
    COUNT(DISTINCT STORE_ID) AS STORES_VISITED,
    -- Customer segmentation
    CASE
        WHEN SUM(TOTAL_AMOUNT) >= 1000 THEN 'VIP'
        WHEN SUM(TOTAL_AMOUNT) >= 500 THEN 'Premium'
        WHEN SUM(TOTAL_AMOUNT) >= 100 THEN 'Standard'
        ELSE 'New'
    END AS CUSTOMER_SEGMENT,
    CURRENT_TIMESTAMP() AS REFRESHED_AT
FROM SALES_SILVER
GROUP BY CUSTOMER_ID, CUSTOMER_NAME, CUSTOMER_EMAIL
ORDER BY LIFETIME_VALUE DESC;

-- Gold dynamic table 3: Product performance
-- Refreshes every 15 minutes
CREATE OR REPLACE DYNAMIC TABLE SALES_GOLD_PRODUCT
    TARGET_LAG = '15 MINUTES'
    WAREHOUSE = COMPUTE_WH
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    COMMENT = 'Gold layer: Product analytics with 15-minute refresh'
AS
SELECT
    PRODUCT_ID,
    PRODUCT_NAME,
    COUNT(*) AS TIMES_SOLD,
    SUM(QUANTITY) AS TOTAL_QUANTITY_SOLD,
    SUM(TOTAL_AMOUNT) AS TOTAL_REVENUE,
    AVG(UNIT_PRICE) AS AVG_PRICE,
    MIN(UNIT_PRICE) AS MIN_PRICE,
    MAX(UNIT_PRICE) AS MAX_PRICE,
    COUNT(DISTINCT CUSTOMER_ID) AS UNIQUE_CUSTOMERS,
    COUNT(DISTINCT REGION) AS REGIONS_SOLD,
    COUNT(DISTINCT STORE_ID) AS STORES_SOLD,
    -- Product ranking
    RANK() OVER (ORDER BY SUM(TOTAL_AMOUNT) DESC) AS REVENUE_RANK,
    RANK() OVER (ORDER BY SUM(QUANTITY) DESC) AS QUANTITY_RANK,
    CURRENT_TIMESTAMP() AS REFRESHED_AT
FROM SALES_SILVER
GROUP BY PRODUCT_ID, PRODUCT_NAME
ORDER BY TOTAL_REVENUE DESC;

-- Gold dynamic table 4: Regional performance
-- Refreshes every 10 minutes
CREATE OR REPLACE DYNAMIC TABLE SALES_GOLD_REGIONAL
    TARGET_LAG = '10 MINUTES'
    WAREHOUSE = COMPUTE_WH
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    COMMENT = 'Gold layer: Regional performance with 10-minute refresh'
AS
SELECT
    REGION,
    COUNT(DISTINCT CUSTOMER_ID) AS UNIQUE_CUSTOMERS,
    COUNT(DISTINCT STORE_ID) AS ACTIVE_STORES,
    COUNT(*) AS TOTAL_TRANSACTIONS,
    SUM(TOTAL_AMOUNT) AS TOTAL_REVENUE,
    AVG(TOTAL_AMOUNT) AS AVG_TRANSACTION_VALUE,
    SUM(QUANTITY) AS TOTAL_ITEMS_SOLD,
    -- Performance metrics
    ROUND(SUM(TOTAL_AMOUNT) / COUNT(DISTINCT STORE_ID), 2) AS REVENUE_PER_STORE,
    ROUND(SUM(TOTAL_AMOUNT) / COUNT(DISTINCT CUSTOMER_ID), 2) AS REVENUE_PER_CUSTOMER,
    CURRENT_TIMESTAMP() AS REFRESHED_AT
FROM SALES_SILVER
GROUP BY REGION
ORDER BY TOTAL_REVENUE DESC;

-- ============================================================================
-- MONITORING AND MANAGEMENT
-- ============================================================================

-- View dynamic table refresh history
-- SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
--     'SALES_SILVER', DATEADD(day, -7, CURRENT_TIMESTAMP()), CURRENT_TIMESTAMP()
-- ));

-- View dynamic table details
-- SHOW DYNAMIC TABLES;

-- Describe a specific dynamic table
-- DESC DYNAMIC TABLE SALES_SILVER;

-- Check data lag
-- SELECT
--     name,
--     target_lag,
--     data_timestamp,
--     refresh_mode,
--     scheduling_state
-- FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES)
-- WHERE schema_name = 'SALES';

-- Manually refresh a dynamic table (if needed)
-- ALTER DYNAMIC TABLE SALES_SILVER REFRESH;

-- Suspend automatic refresh
-- ALTER DYNAMIC TABLE SALES_SILVER SUSPEND;

-- Resume automatic refresh
-- ALTER DYNAMIC TABLE SALES_SILVER RESUME;

-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Query silver layer (cleaned data)
SELECT * FROM SALES_SILVER LIMIT 10;

-- Query gold layer aggregations
SELECT * FROM SALES_GOLD_DAILY ORDER BY TRANSACTION_DATE DESC;
SELECT * FROM SALES_GOLD_CUSTOMER LIMIT 10;
SELECT * FROM SALES_GOLD_PRODUCT LIMIT 10;
SELECT * FROM SALES_GOLD_REGIONAL;

-- Check for VIP customers
SELECT
    CUSTOMER_NAME,
    LIFETIME_VALUE,
    TOTAL_PURCHASES,
    CUSTOMER_SEGMENT
FROM SALES_GOLD_CUSTOMER
WHERE CUSTOMER_SEGMENT = 'VIP'
ORDER BY LIFETIME_VALUE DESC;

-- Top performing products
SELECT
    PRODUCT_NAME,
    TOTAL_REVENUE,
    TOTAL_QUANTITY_SOLD,
    REVENUE_RANK
FROM SALES_GOLD_PRODUCT
WHERE REVENUE_RANK <= 5;

-- Daily revenue trend
SELECT
    TRANSACTION_DATE,
    REGION,
    TOTAL_REVENUE,
    UNIQUE_CUSTOMERS
FROM SALES_GOLD_DAILY
ORDER BY TRANSACTION_DATE DESC, TOTAL_REVENUE DESC;

-- ============================================================================
-- CLEANUP (Optional - only for testing)
-- ============================================================================

/*
-- Drop dynamic tables (in reverse dependency order)
DROP DYNAMIC TABLE IF EXISTS SALES_GOLD_REGIONAL;
DROP DYNAMIC TABLE IF EXISTS SALES_GOLD_PRODUCT;
DROP DYNAMIC TABLE IF EXISTS SALES_GOLD_CUSTOMER;
DROP DYNAMIC TABLE IF EXISTS SALES_GOLD_DAILY;
DROP DYNAMIC TABLE IF EXISTS SALES_SILVER;

-- Drop bronze table and stage
DROP TABLE IF EXISTS SALES_BRONZE;
DROP STAGE IF EXISTS sales_csvs;
DROP FILE FORMAT IF EXISTS CSV_FORMAT;
*/

-- ============================================================================
-- NOTES AND BEST PRACTICES
-- ============================================================================

/*
Dynamic Tables Best Practices:

1. TARGET_LAG:
   - Set based on business requirements
   - Shorter lag = more compute costs
   - Typical values: 5 minutes, 15 minutes, 1 hour

2. REFRESH_MODE:
   - AUTO: Snowflake determines full or incremental refresh
   - INCREMENTAL: Forces incremental refresh (more efficient)
   - FULL: Forces full refresh

3. Dependencies:
   - Dynamic tables automatically track dependencies
   - Downstream tables refresh when upstream changes
   - Create in order: Bronze → Silver → Gold

4. Monitoring:
   - Use DYNAMIC_TABLE_REFRESH_HISTORY for troubleshooting
   - Monitor data_timestamp to check freshness
   - Watch for scheduling_state issues

5. Cost Optimization:
   - Use incremental refresh when possible
   - Set appropriate target lag
   - Use clustering keys for large tables
   - Consider materialized views for simple aggregations

6. Performance:
   - Add appropriate filters in WHERE clauses
   - Use clustering on frequently queried columns
   - Monitor warehouse size and auto-scaling
   - Consider partitioning for very large tables
*/
