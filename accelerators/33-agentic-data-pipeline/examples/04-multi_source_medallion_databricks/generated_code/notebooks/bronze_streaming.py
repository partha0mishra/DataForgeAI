# Databricks notebook source
"""
Bronze Layer - Streaming Ingestion from Kafka
Ingests raw events from Kafka topics into Delta Lake
"""

from pyspark.sql import functions as F
from pyspark.sql.types import *

# COMMAND ----------
# Configuration

kafka_bootstrap_servers = "kafka-1:9092,kafka-2:9092,kafka-3:9092"
checkpoint_location = "s3://your-bucket/checkpoints/kafka"

# COMMAND ----------
# Schema definitions

user_events_schema = StructType([
    StructField("event_type", StringType()),
    StructField("user_id", StringType()),
    StructField("timestamp", StringType()),
    StructField("page_url", StringType()),
    StructField("referrer", StringType()),
    StructField("session_id", StringType()),
    StructField("device", StringType()),
    StructField("ip_address", StringType()),
    StructField("product_id", StringType()),
    StructField("quantity", IntegerType())
])

transaction_events_schema = StructType([
    StructField("event_type", StringType()),
    StructField("transaction_id", StringType()),
    StructField("original_transaction_id", StringType()),
    StructField("user_id", StringType()),
    StructField("timestamp", StringType()),
    StructField("amount", DoubleType()),
    StructField("currency", StringType()),
    StructField("payment_method", StringType()),
    StructField("reason", StringType()),
    StructField("items", ArrayType(StructType([
        StructField("product_id", StringType()),
        StructField("quantity", IntegerType()),
        StructField("price", DoubleType())
    ])))
])

# COMMAND ----------
# Ingest user events

user_events_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", kafka_bootstrap_servers)
    .option("subscribe", "user-events")
    .option("startingOffsets", "latest")
    .option("failOnDataLoss", "false")
    .load()
    .select(
        F.col("key").cast("string").alias("event_key"),
        F.from_json(F.col("value").cast("string"), user_events_schema).alias("event"),
        F.col("topic"),
        F.col("partition"),
        F.col("offset"),
        F.col("timestamp").alias("kafka_timestamp")
    )
    .select(
        "event_key",
        "event.*",
        "topic",
        "partition",
        "offset",
        "kafka_timestamp",
        F.current_timestamp().alias("ingested_at")
    )
)

# Write to bronze layer
(user_events_stream.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", f"{checkpoint_location}/user_events")
    .option("mergeSchema", "true")
    .trigger(processingTime="10 seconds")
    .table("analytics.bronze.user_events")
)

# COMMAND ----------
# Ingest transaction events

transaction_events_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", kafka_bootstrap_servers)
    .option("subscribe", "transaction-events")
    .option("startingOffsets", "latest")
    .option("failOnDataLoss", "false")
    .load()
    .select(
        F.col("key").cast("string").alias("event_key"),
        F.from_json(F.col("value").cast("string"), transaction_events_schema).alias("event"),
        F.col("topic"),
        F.col("partition"),
        F.col("offset"),
        F.col("timestamp").alias("kafka_timestamp")
    )
    .select(
        "event_key",
        "event.*",
        "topic",
        "partition",
        "offset",
        "kafka_timestamp",
        F.current_timestamp().alias("ingested_at")
    )
)

# Write to bronze layer
(transaction_events_stream.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", f"{checkpoint_location}/transaction_events")
    .option("mergeSchema", "true")
    .trigger(processingTime="10 seconds")
    .table("analytics.bronze.transaction_events")
)
