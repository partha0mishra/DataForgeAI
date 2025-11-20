# Databricks notebook source
"""
Silver Layer - Data Cleansing and Transformations
Applies business logic, deduplication, and quality checks
"""

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# COMMAND ----------
# Silver: Clean user events

cleaned_user_events = (
    spark.readStream.table("analytics.bronze.user_events")
    .filter(F.col("user_id").isNotNull())
    .filter(F.col("event_type").isNotNull())
    .withColumn("event_timestamp", F.to_timestamp("timestamp"))
    .withColumn("event_date", F.to_date("event_timestamp"))
    .withColumn("hour_of_day", F.hour("event_timestamp"))
    .withColumn("day_of_week", F.dayofweek("event_timestamp"))
    .dropDuplicates(["user_id", "session_id", "timestamp", "event_type"])
    .select(
        "event_key",
        "event_type",
        "user_id",
        "event_timestamp",
        "event_date",
        "hour_of_day",
        "day_of_week",
        "page_url",
        "referrer",
        "session_id",
        "device",
        "ip_address",
        "product_id",
        "quantity",
        "ingested_at"
    )
)

(cleaned_user_events.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "s3://your-bucket/checkpoints/silver/user_events")
    .option("mergeSchema", "true")
    .trigger(processingTime="30 seconds")
    .table("analytics.silver.user_events")
)

# COMMAND ----------
# Silver: Clean transaction events

cleaned_transactions = (
    spark.readStream.table("analytics.bronze.transaction_events")
    .filter(F.col("transaction_id").isNotNull())
    .filter(F.col("user_id").isNotNull())
    .filter(F.col("amount").isNotNull())
    .withColumn("event_timestamp", F.to_timestamp("timestamp"))
    .withColumn("event_date", F.to_date("event_timestamp"))
    .withColumn("amount_usd",
        F.when(F.col("currency") == "USD", F.col("amount"))
        .otherwise(F.col("amount") * 1.0)  # Simplified - use real FX rates
    )
    .dropDuplicates(["transaction_id"])
    .select(
        "event_key",
        "event_type",
        "transaction_id",
        "original_transaction_id",
        "user_id",
        "event_timestamp",
        "event_date",
        "amount",
        "amount_usd",
        "currency",
        "payment_method",
        "reason",
        "items",
        "ingested_at"
    )
)

(cleaned_transactions.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "s3://your-bucket/checkpoints/silver/transactions")
    .option("mergeSchema", "true")
    .trigger(processingTime="30 seconds")
    .table("analytics.silver.transactions")
)

# COMMAND ----------
# Silver: Clean users (batch - using merge for SCD Type 1)

def merge_users():
    """Merge users from bronze to silver with deduplication."""

    # Get latest record for each user
    window_spec = Window.partitionBy("user_id").orderBy(F.col("updated_at").desc())

    latest_users = (
        spark.read.table("analytics.bronze.users")
        .withColumn("row_num", F.row_number().over(window_spec))
        .filter(F.col("row_num") == 1)
        .drop("row_num")
        .withColumn("updated_timestamp", F.to_timestamp("updated_at"))
        .withColumn("signup_timestamp", F.to_timestamp("signup_date"))
    )

    # Merge into silver
    latest_users.createOrReplaceTempView("latest_users")

    spark.sql("""
        MERGE INTO analytics.silver.users AS target
        USING latest_users AS source
        ON target.user_id = source.user_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

merge_users()

# COMMAND ----------
# Silver: Clean products (batch)

def merge_products():
    """Merge products from bronze to silver."""

    window_spec = Window.partitionBy("product_id").orderBy(F.col("updated_at").desc())

    latest_products = (
        spark.read.table("analytics.bronze.products")
        .withColumn("row_num", F.row_number().over(window_spec))
        .filter(F.col("row_num") == 1)
        .drop("row_num")
        .withColumn("updated_timestamp", F.to_timestamp("updated_at"))
        .filter(F.col("price") > 0)
        .filter(F.col("stock_quantity") >= 0)
    )

    latest_products.createOrReplaceTempView("latest_products")

    spark.sql("""
        MERGE INTO analytics.silver.products AS target
        USING latest_products AS source
        ON target.product_id = source.product_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

merge_products()
