# Databricks notebook source
"""
Bronze Layer - Batch Ingestion from PostgreSQL
Ingests dimension tables from PostgreSQL into Delta Lake
"""

from pyspark.sql import functions as F

# COMMAND ----------
# Configuration

postgres_config = {
    "host": "postgres.company.com",
    "port": "5432",
    "database": "production",
    "user": "readonly_user",
    "password": dbutils.secrets.get(scope="postgres_creds", key="db_password")
}

jdbc_url = f"jdbc:postgresql://{postgres_config['host']}:{postgres_config['port']}/{postgres_config['database']}"

# COMMAND ----------
# Helper function for incremental loads

def load_table_incremental(table_name, schema, incremental_column, target_table):
    """Load table incrementally based on a timestamp column."""

    # Get last loaded timestamp
    try:
        last_loaded = (
            spark.read.table(target_table)
            .agg(F.max(incremental_column).alias("max_timestamp"))
            .collect()[0]["max_timestamp"]
        )
        where_clause = f"{incremental_column} > '{last_loaded}'"
    except:
        # Table doesn't exist or is empty - do full load
        where_clause = "1=1"

    # Read from PostgreSQL
    df = (
        spark.read
        .format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", f"{schema}.{table_name}")
        .option("user", postgres_config["user"])
        .option("password", postgres_config["password"])
        .option("driver", "org.postgresql.Driver")
        .option("fetchsize", 10000)
        .load()
        .filter(where_clause)
        .withColumn("ingested_at", F.current_timestamp())
    )

    # Write to bronze layer
    (df.write
        .format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .saveAsTable(target_table)
    )

    return df.count()

# COMMAND ----------
# Load users table

users_count = load_table_incremental(
    table_name="users",
    schema="public",
    incremental_column="updated_at",
    target_table="analytics.bronze.users"
)

print(f"Loaded {users_count} users records")

# COMMAND ----------
# Load products table

products_count = load_table_incremental(
    table_name="products",
    schema="public",
    incremental_column="updated_at",
    target_table="analytics.bronze.products"
)

print(f"Loaded {products_count} products records")

# COMMAND ----------
# Data quality checks

def check_data_quality(table_name):
    """Run basic data quality checks."""
    df = spark.read.table(table_name)

    total_records = df.count()
    null_counts = df.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in df.columns])

    print(f"\n{table_name} Quality Report:")
    print(f"Total records: {total_records}")
    print(f"Null counts:")
    null_counts.show()

check_data_quality("analytics.bronze.users")
check_data_quality("analytics.bronze.products")
