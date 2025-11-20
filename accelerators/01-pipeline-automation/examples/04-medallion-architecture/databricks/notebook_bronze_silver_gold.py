"""
Notebook-based Medallion Architecture Implementation
=====================================================

Alternative to DLT pipeline using standard PySpark DataFrames and Delta Lake APIs.
Can be used without Delta Live Tables - runs on any Spark cluster with Delta Lake.

This implementation provides:
    - Full control over optimization (Z-ordering, compaction, vacuum)
    - Explicit merge operations for upserts
    - Traditional batch and streaming processing
    - Compatible with Databricks notebooks or standalone Spark

Usage:
    # In Databricks notebook or spark-submit
    %run ./notebook_bronze_silver_gold

    # Or via spark-submit
    spark-submit --packages io.delta:delta-core_2.12:2.4.0 notebook_bronze_silver_gold.py

Author: DataForgeAI Team
Version: 1.0.0
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, from_json, expr, window, count, avg, max as spark_max,
    min as spark_min, current_timestamp, lit, sum as spark_sum,
    lag, row_number, md5, concat_ws, unix_timestamp, to_timestamp,
    stddev, percentile_approx, first, date_format, when
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    TimestampType, IntegerType, LongType, BooleanType
)
from pyspark.sql.window import Window
from delta.tables import DeltaTable
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURATION AND SETUP
# ============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Spark Session with Delta Lake
spark = (
    SparkSession.builder
    .appName("Medallion Architecture - Bronze/Silver/Gold")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.databricks.delta.optimizeWrite.enabled", "true")
    .config("spark.databricks.delta.autoCompact.enabled", "true")
    .config("spark.sql.adaptive.enabled", "true")
    .getOrCreate()
)

# Storage paths (use DBFS in Databricks or S3/ADLS in production)
BASE_PATH = os.getenv("DELTA_LAKE_PATH", "/tmp/delta-lake")
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "/tmp/checkpoints")

PATHS = {
    "bronze": {
        "iot_events": f"{BASE_PATH}/bronze/iot_events",
        "sensor_readings": f"{BASE_PATH}/bronze/sensor_readings"
    },
    "silver": {
        "iot_events": f"{BASE_PATH}/silver/iot_events",
        "sensor_readings": f"{BASE_PATH}/silver/sensor_readings",
        "device_sessions": f"{BASE_PATH}/silver/device_sessions"
    },
    "gold": {
        "hourly_metrics": f"{BASE_PATH}/gold/hourly_metrics",
        "daily_metrics": f"{BASE_PATH}/gold/daily_metrics",
        "device_health": f"{BASE_PATH}/gold/device_health",
        "kpi_dashboard": f"{BASE_PATH}/gold/kpi_dashboard"
    }
}

# Kafka configuration
KAFKA_CONFIG = {
    "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    "topic": "iot_events",
    "starting_offsets": "earliest"
}

# PostgreSQL configuration
POSTGRES_CONFIG = {
    "url": os.getenv("POSTGRES_JDBC_URL", "jdbc:postgresql://localhost:5432/sensors"),
    "table": "public.sensor_readings",
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "password"),
    "driver": "org.postgresql.Driver"
}

# IoT event schema
IOT_EVENT_SCHEMA = StructType([
    StructField("device_id", StringType(), False),
    StructField("timestamp", StringType(), False),
    StructField("temperature", DoubleType(), True),
    StructField("humidity", DoubleType(), True),
    StructField("pressure", DoubleType(), True),
    StructField("battery_level", DoubleType(), True),
    StructField("signal_strength", IntegerType(), True),
    StructField("location_lat", DoubleType(), True),
    StructField("location_lon", DoubleType(), True),
    StructField("event_type", StringType(), True)
])


# ============================================================================
# BRONZE LAYER: Raw Data Ingestion
# ============================================================================

def ingest_bronze_iot_events_streaming() -> None:
    """
    Ingest IoT events from Kafka into Bronze Delta table (streaming).

    This creates a continuous streaming job that reads from Kafka and writes
    to Delta Lake with exactly-once semantics using checkpointing.
    """
    logger.info(f"Starting streaming ingestion from Kafka topic: {KAFKA_CONFIG['topic']}")

    # Read from Kafka
    kafka_stream = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_CONFIG["bootstrap_servers"])
        .option("subscribe", KAFKA_CONFIG["topic"])
        .option("startingOffsets", KAFKA_CONFIG["starting_offsets"])
        .option("maxOffsetsPerTrigger", 10000)
        .option("failOnDataLoss", "false")
        .load()
    )

    # Transform and write to bronze Delta table
    bronze_df = kafka_stream.select(
        col("key").cast("string").alias("kafka_key"),
        col("value").cast("string").alias("raw_value"),
        col("topic").alias("kafka_topic"),
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        col("timestamp").alias("kafka_timestamp"),
        current_timestamp().alias("ingestion_timestamp")
    )

    # Write to Delta with checkpointing
    query = (
        bronze_df.writeStream
        .format("delta")
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINT_PATH}/bronze_iot_events")
        .trigger(processingTime="30 seconds")
        .start(PATHS["bronze"]["iot_events"])
    )

    logger.info(f"Streaming query started. Writing to: {PATHS['bronze']['iot_events']}")
    return query


def ingest_bronze_sensor_readings_batch() -> None:
    """
    Ingest sensor readings from PostgreSQL into Bronze Delta table (batch).

    Uses incremental batch loading based on updated_at timestamp to avoid
    reprocessing the entire table on each run.
    """
    logger.info(f"Starting batch ingestion from PostgreSQL: {POSTGRES_CONFIG['table']}")

    # Check if table exists to determine incremental vs full load
    table_exists = DeltaTable.isDeltaTable(spark, PATHS["bronze"]["sensor_readings"])

    if table_exists:
        # Incremental load: get max timestamp from existing data
        max_timestamp = (
            spark.read.format("delta")
            .load(PATHS["bronze"]["sensor_readings"])
            .agg(spark_max("updated_at"))
            .collect()[0][0]
        )

        if max_timestamp:
            query = f"(SELECT * FROM {POSTGRES_CONFIG['table']} WHERE updated_at > '{max_timestamp}') as subq"
        else:
            query = POSTGRES_CONFIG['table']
    else:
        # Full load
        query = POSTGRES_CONFIG['table']

    # Read from PostgreSQL
    postgres_df = (
        spark.read
        .format("jdbc")
        .option("url", POSTGRES_CONFIG["url"])
        .option("dbtable", query)
        .option("user", POSTGRES_CONFIG["user"])
        .option("password", POSTGRES_CONFIG["password"])
        .option("driver", POSTGRES_CONFIG["driver"])
        .option("fetchsize", 10000)
        .load()
        .withColumn("ingestion_timestamp", current_timestamp())
    )

    # Write to Delta (append mode for bronze layer)
    postgres_df.write.format("delta").mode("append").save(PATHS["bronze"]["sensor_readings"])

    logger.info(f"Batch ingestion completed. Rows written: {postgres_df.count()}")


# ============================================================================
# SILVER LAYER: Cleansed and Validated Data
# ============================================================================

def process_silver_iot_events() -> DataFrame:
    """
    Process bronze IoT events into silver layer with cleansing and validation.

    Returns:
        DataFrame: Cleansed and validated IoT events
    """
    logger.info("Processing silver IoT events")

    # Read from bronze
    bronze_df = spark.read.format("delta").load(PATHS["bronze"]["iot_events"])

    # Parse JSON and extract fields
    parsed_df = (
        bronze_df
        .select(
            from_json(col("raw_value"), IOT_EVENT_SCHEMA).alias("data"),
            col("kafka_offset"),
            col("kafka_timestamp"),
            col("ingestion_timestamp")
        )
        .select("data.*", "kafka_offset", "kafka_timestamp", "ingestion_timestamp")
    )

    # Convert timestamp and validate
    validated_df = (
        parsed_df
        .withColumn("event_timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"))
        .filter(col("device_id").isNotNull())
        .filter(col("event_timestamp").isNotNull())
        .filter(col("temperature").between(-50, 150))
        .filter(col("humidity").between(0, 100))
        .filter(col("battery_level").between(0, 100))
    )

    # Add derived fields
    enriched_df = (
        validated_df
        .withColumn(
            "battery_status",
            when(col("battery_level") >= 80, "Good")
            .when(col("battery_level") >= 50, "Fair")
            .when(col("battery_level") >= 20, "Low")
            .otherwise("Critical")
        )
        .withColumn(
            "signal_status",
            when(col("signal_strength") >= -50, "Excellent")
            .when(col("signal_strength") >= -70, "Good")
            .when(col("signal_strength") >= -90, "Fair")
            .otherwise("Poor")
        )
        .withColumn(
            "event_id",
            md5(concat_ws("-", col("device_id"), col("timestamp"), col("kafka_offset")))
        )
    )

    # Deduplication
    window_spec = Window.partitionBy("device_id", "event_timestamp").orderBy(col("kafka_offset").desc())
    deduped_df = (
        enriched_df
        .withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num", "timestamp")
    )

    return deduped_df


def upsert_silver_iot_events(silver_df: DataFrame) -> None:
    """
    Upsert silver IoT events into Delta table using merge operation.

    Args:
        silver_df: Cleansed DataFrame to upsert
    """
    logger.info(f"Upserting silver IoT events to: {PATHS['silver']['iot_events']}")

    # Create table if not exists
    if not DeltaTable.isDeltaTable(spark, PATHS["silver"]["iot_events"]):
        silver_df.write.format("delta").mode("overwrite").save(PATHS["silver"]["iot_events"])
        logger.info("Created new silver IoT events table")
        return

    # Perform merge (upsert)
    delta_table = DeltaTable.forPath(spark, PATHS["silver"]["iot_events"])

    (
        delta_table.alias("target")
        .merge(
            silver_df.alias("source"),
            "target.event_id = source.event_id"
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )

    logger.info("Silver IoT events upsert completed")


def process_silver_sensor_readings() -> None:
    """
    Process bronze sensor readings into silver layer.
    """
    logger.info("Processing silver sensor readings")

    # Read from bronze
    bronze_df = spark.read.format("delta").load(PATHS["bronze"]["sensor_readings"])

    # Add processing timestamp
    processed_df = bronze_df.withColumn("processing_timestamp", current_timestamp())

    # Deduplication
    window_spec = Window.partitionBy("sensor_id", "reading_timestamp").orderBy(col("updated_at").desc())
    deduped_df = (
        processed_df
        .withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )

    # Write to silver
    deduped_df.write.format("delta").mode("overwrite").save(PATHS["silver"]["sensor_readings"])

    logger.info("Silver sensor readings processing completed")


# ============================================================================
# GOLD LAYER: Business Aggregations
# ============================================================================

def create_gold_hourly_metrics() -> None:
    """
    Create hourly aggregated metrics from silver IoT events.
    """
    logger.info("Creating gold hourly metrics")

    # Read from silver
    silver_df = spark.read.format("delta").load(PATHS["silver"]["iot_events"])

    # Hourly aggregation
    hourly_agg = (
        silver_df
        .groupBy(
            window("event_timestamp", "1 hour"),
            "device_id"
        )
        .agg(
            count("*").alias("event_count"),
            avg("temperature").alias("avg_temperature"),
            spark_min("temperature").alias("min_temperature"),
            spark_max("temperature").alias("max_temperature"),
            stddev("temperature").alias("stddev_temperature"),
            avg("humidity").alias("avg_humidity"),
            spark_min("humidity").alias("min_humidity"),
            spark_max("humidity").alias("max_humidity"),
            avg("pressure").alias("avg_pressure"),
            avg("battery_level").alias("avg_battery_level"),
            spark_min("battery_level").alias("min_battery_level"),
            avg("signal_strength").alias("avg_signal_strength"),
            first("location_lat").alias("last_location_lat"),
            first("location_lon").alias("last_location_lon"),
            first("battery_status").alias("last_battery_status"),
            first("signal_status").alias("last_signal_status")
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "*"
        )
        .drop("window")
        .withColumn("computed_at", current_timestamp())
    )

    # Write to gold (overwrite mode for aggregations)
    hourly_agg.write.format("delta").mode("overwrite").save(PATHS["gold"]["hourly_metrics"])

    logger.info("Gold hourly metrics created")


def create_gold_daily_metrics() -> None:
    """
    Create daily aggregated metrics from hourly metrics.
    """
    logger.info("Creating gold daily metrics")

    # Read from gold hourly
    hourly_df = spark.read.format("delta").load(PATHS["gold"]["hourly_metrics"])

    # Daily aggregation
    daily_agg = (
        hourly_df
        .withColumn("date", date_format("window_start", "yyyy-MM-dd"))
        .groupBy("date", "device_id")
        .agg(
            spark_sum("event_count").alias("total_events"),
            avg("avg_temperature").alias("avg_temperature"),
            spark_min("min_temperature").alias("min_temperature"),
            spark_max("max_temperature").alias("max_temperature"),
            avg("avg_humidity").alias("avg_humidity"),
            avg("avg_pressure").alias("avg_pressure"),
            avg("avg_battery_level").alias("avg_battery_level"),
            spark_min("min_battery_level").alias("min_battery_level"),
            avg("avg_signal_strength").alias("avg_signal_strength"),
            count("*").alias("hourly_records_count")
        )
        .withColumn("computed_at", current_timestamp())
    )

    # Write to gold
    daily_agg.write.format("delta").mode("overwrite").save(PATHS["gold"]["daily_metrics"])

    logger.info("Gold daily metrics created")


def create_gold_device_health() -> None:
    """
    Create current device health status table.
    """
    logger.info("Creating gold device health")

    # Read from silver
    silver_df = spark.read.format("delta").load(PATHS["silver"]["iot_events"])

    # Get latest record per device
    window_spec = Window.partitionBy("device_id").orderBy(col("event_timestamp").desc())

    latest_df = (
        silver_df
        .withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .select(
            "device_id",
            col("event_timestamp").alias("last_seen"),
            "temperature",
            "humidity",
            "pressure",
            "battery_level",
            "battery_status",
            "signal_strength",
            "signal_status",
            "location_lat",
            "location_lon",
            "event_type"
        )
    )

    # Add health score
    health_df = (
        latest_df
        .withColumn(
            "health_score",
            when((col("battery_level") >= 80) & (col("signal_strength") >= -60), 100)
            .when((col("battery_level") >= 50) & (col("signal_strength") >= -80), 75)
            .when((col("battery_level") >= 20) & (col("signal_strength") >= -90), 50)
            .otherwise(25)
        )
        .withColumn(
            "requires_attention",
            (col("battery_level") < 20) | (col("signal_strength") < -90)
        )
        .withColumn("computed_at", current_timestamp())
    )

    # Write to gold
    health_df.write.format("delta").mode("overwrite").save(PATHS["gold"]["device_health"])

    logger.info("Gold device health created")


# ============================================================================
# OPTIMIZATION UTILITIES
# ============================================================================

def optimize_delta_table(table_path: str, z_order_cols: Optional[list] = None) -> None:
    """
    Optimize Delta table with optional Z-ordering.

    Args:
        table_path: Path to Delta table
        z_order_cols: Columns to Z-order by
    """
    logger.info(f"Optimizing Delta table: {table_path}")

    if z_order_cols:
        spark.sql(f"OPTIMIZE delta.`{table_path}` ZORDER BY ({', '.join(z_order_cols)})")
    else:
        spark.sql(f"OPTIMIZE delta.`{table_path}`")

    logger.info("Optimization completed")


def vacuum_delta_table(table_path: str, retention_hours: int = 168) -> None:
    """
    Vacuum Delta table to remove old files.

    Args:
        table_path: Path to Delta table
        retention_hours: Retention period in hours (default: 7 days)
    """
    logger.info(f"Vacuuming Delta table: {table_path} (retention: {retention_hours}h)")

    spark.sql(f"VACUUM delta.`{table_path}` RETAIN {retention_hours} HOURS")

    logger.info("Vacuum completed")


# ============================================================================
# ORCHESTRATION
# ============================================================================

def run_bronze_layer() -> None:
    """Execute bronze layer ingestion."""
    logger.info("=" * 80)
    logger.info("BRONZE LAYER INGESTION")
    logger.info("=" * 80)

    # Batch ingestion from PostgreSQL
    ingest_bronze_sensor_readings_batch()

    # Note: Streaming ingestion needs to be run separately or in background
    logger.info("Note: Streaming Kafka ingestion should be started separately")


def run_silver_layer() -> None:
    """Execute silver layer processing."""
    logger.info("=" * 80)
    logger.info("SILVER LAYER PROCESSING")
    logger.info("=" * 80)

    # Process IoT events
    silver_iot_df = process_silver_iot_events()
    upsert_silver_iot_events(silver_iot_df)

    # Process sensor readings
    process_silver_sensor_readings()


def run_gold_layer() -> None:
    """Execute gold layer aggregations."""
    logger.info("=" * 80)
    logger.info("GOLD LAYER AGGREGATIONS")
    logger.info("=" * 80)

    create_gold_hourly_metrics()
    create_gold_daily_metrics()
    create_gold_device_health()


def run_optimization() -> None:
    """Optimize all Delta tables."""
    logger.info("=" * 80)
    logger.info("OPTIMIZATION")
    logger.info("=" * 80)

    # Optimize silver tables with Z-ordering
    optimize_delta_table(
        PATHS["silver"]["iot_events"],
        z_order_cols=["device_id", "event_timestamp"]
    )

    # Optimize gold tables
    optimize_delta_table(
        PATHS["gold"]["hourly_metrics"],
        z_order_cols=["window_start", "device_id"]
    )

    optimize_delta_table(PATHS["gold"]["daily_metrics"])
    optimize_delta_table(PATHS["gold"]["device_health"])


def run_full_pipeline() -> None:
    """Execute full medallion pipeline."""
    logger.info("=" * 80)
    logger.info("MEDALLION ARCHITECTURE PIPELINE")
    logger.info("=" * 80)

    try:
        run_bronze_layer()
        run_silver_layer()
        run_gold_layer()
        run_optimization()

        logger.info("=" * 80)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        raise


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import sys

    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "bronze":
            run_bronze_layer()
        elif command == "silver":
            run_silver_layer()
        elif command == "gold":
            run_gold_layer()
        elif command == "optimize":
            run_optimization()
        elif command == "full":
            run_full_pipeline()
        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Valid commands: bronze, silver, gold, optimize, full")
            sys.exit(1)
    else:
        # Default: run full pipeline
        run_full_pipeline()
