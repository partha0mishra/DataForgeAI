-- Create Athena database
CREATE DATABASE IF NOT EXISTS data_lake;

-- Create external table for raw sales data
CREATE EXTERNAL TABLE IF NOT EXISTS data_lake.sales_raw (
    order_id STRING,
    order_date STRING,
    customer_id STRING,
    product_id STRING,
    quantity INT,
    amount DECIMAL(10,2),
    region STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://your-data-lake/raw/sales/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- Create external table for processed sales data (partitioned Parquet)
CREATE EXTERNAL TABLE IF NOT EXISTS data_lake.sales_processed (
    order_id STRING,
    order_date DATE,
    customer_id STRING,
    product_id STRING,
    quantity INT,
    amount DECIMAL(10,2),
    region STRING,
    processed_at TIMESTAMP
)
PARTITIONED BY (
    year INT,
    month INT,
    day INT
)
STORED AS PARQUET
LOCATION 's3://your-data-lake/processed/sales/'
TBLPROPERTIES (
    'parquet.compression'='SNAPPY',
    'projection.enabled'='true',
    'projection.year.type'='integer',
    'projection.year.range'='2020,2030',
    'projection.month.type'='integer',
    'projection.month.range'='1,12',
    'projection.day.type'='integer',
    'projection.day.range'='1,31',
    'storage.location.template'='s3://your-data-lake/processed/sales/year=${year}/month=${month}/day=${day}'
);

-- Create view for daily sales aggregations
CREATE OR REPLACE VIEW data_lake.daily_sales_summary AS
SELECT
    year,
    month,
    day,
    region,
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(amount) AS total_revenue,
    AVG(amount) AS avg_order_value,
    SUM(quantity) AS total_units_sold
FROM data_lake.sales_processed
GROUP BY year, month, day, region;

-- Query to test the view
-- SELECT * FROM data_lake.daily_sales_summary
-- WHERE year = 2025 AND month = 1
-- ORDER BY day DESC, total_revenue DESC;
