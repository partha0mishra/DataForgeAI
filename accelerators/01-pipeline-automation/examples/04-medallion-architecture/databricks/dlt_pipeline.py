"""
Delta Live Tables Pipeline: Medallion Architecture
====================================================

This module implements a complete medallion architecture using Delta Live Tables (DLT).
Ingests data from Kafka (IoT events) and PostgreSQL (sensor readings), applies
cleansing and validation in the silver layer, and creates aggregated tables in the gold layer.

Architecture:
    - Bronze: Raw data ingestion from Kafka + PostgreSQL
    - Silver: Cleansed, validated, deduplicated data
    - Gold: Business-level aggregations for analytics

Author: DataForgeAI Team
Version: 1.0.0
"""

import dlt
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, from_json, expr, window, count, avg, max as spark_max,
    min as spark_min, current_timestamp, lit, sum as spark_sum,
    last, row_number, md5, concat_ws, unix_timestamp, to_timestamp,
    stddev, percentile_approx, first
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    TimestampType, IntegerType, LongType
)
from pyspark.sql.window import Window
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Kafka configuration (use Databricks secrets in production)
KAFKA_BOOTSTRAP_SERVERS = spark.conf.get("kafka.bootstrap.servers", "localhost:9092")
KAFKA_TOPIC = "iot_events"

# PostgreSQL configuration (use Databricks secrets in production)
POSTGRES_JDBC_URL = spark.conf.get("postgres.jdbc.url", "jdbc:postgresql://localhost:5432/sensors")
POSTGRES_USER = spark.conf.get("postgres.user", "postgres")
POSTGRES_PASSWORD = spark.conf.get("postgres.password", "password")
POSTGRES_TABLE = "public.sensor_readings"

# Schema definitions
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

@dlt.table(
    name="bronze_iot_events",
    comment="Raw IoT events from Kafka stream - append only",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.zOrderCols": "timestamp,device_id"
    }
)
def bronze_iot_events() -> DataFrame:
    """
    Ingest raw IoT events from Kafka topic.

    Streaming ingestion with schema enforcement. All data is preserved
    in its original form for data lineage and reprocessing capabilities.

    Returns:
        DataFrame: Raw Kafka messages with metadata
    """
    logger.info(f"Ingesting IoT events from Kafka topic: {KAFKA_TOPIC}")

    return (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "earliest")
        .option("maxOffsetsPerTrigger", 10000)
        .option("failOnDataLoss", "false")
        .load()
        .select(
            col("key").cast("string").alias("kafka_key"),
            col("value").cast("string").alias("raw_value"),
            col("topic").alias("kafka_topic"),
            col("partition").alias("kafka_partition"),
            col("offset").alias("kafka_offset"),
            col("timestamp").alias("kafka_timestamp"),
            current_timestamp().alias("ingestion_timestamp")
        )
    )


@dlt.table(
    name="bronze_sensor_readings",
    comment="Raw sensor readings from PostgreSQL - batch snapshots",
    table_properties={
        "quality": "bronze"
    }
)
def bronze_sensor_readings() -> DataFrame:
    """
    Ingest sensor readings from PostgreSQL using JDBC.

    Incremental batch ingestion based on updated_at timestamp.
    Captures full snapshots for historical tracking.

    Returns:
        DataFrame: Raw sensor data with ingestion metadata
    """
    logger.info(f"Ingesting sensor readings from PostgreSQL: {POSTGRES_TABLE}")

    return (
        spark.read
        .format("jdbc")
        .option("url", POSTGRES_JDBC_URL)
        .option("dbtable", POSTGRES_TABLE)
        .option("user", POSTGRES_USER)
        .option("password", POSTGRES_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        .option("fetchsize", 10000)
        .load()
        .withColumn("ingestion_timestamp", current_timestamp())
    )


# ============================================================================
# SILVER LAYER: Cleansed and Validated Data
# ============================================================================

@dlt.table(
    name="silver_iot_events",
    comment="Cleansed and validated IoT events with quality checks",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.zOrderCols": "device_id,event_timestamp"
    }
)
@dlt.expect_or_drop("valid_device_id", "device_id IS NOT NULL AND length(device_id) > 0")
@dlt.expect_or_drop("valid_timestamp", "event_timestamp IS NOT NULL")
@dlt.expect_or_drop("valid_temperature", "temperature BETWEEN -50 AND 150")
@dlt.expect_or_drop("valid_humidity", "humidity BETWEEN 0 AND 100")
@dlt.expect_or_drop("valid_battery", "battery_level BETWEEN 0 AND 100")
@dlt.expect("valid_location", "location_lat IS NOT NULL AND location_lon IS NOT NULL", 0.95)
def silver_iot_events() -> DataFrame:
    """
    Parse, cleanse, and validate IoT events from bronze layer.

    Transformations:
        - Parse JSON from Kafka messages
        - Type casting and validation
        - Deduplication based on device_id + timestamp
        - Data quality expectations
        - Enrich with derived fields

    Returns:
        DataFrame: Validated IoT events ready for analytics
    """
    logger.info("Processing silver IoT events with quality checks")

    # Read from bronze and parse JSON
    df = (
        dlt.read_stream("bronze_iot_events")
        .select(
            from_json(col("raw_value"), IOT_EVENT_SCHEMA).alias("data"),
            col("kafka_offset"),
            col("kafka_timestamp"),
            col("ingestion_timestamp")
        )
        .select("data.*", "kafka_offset", "kafka_timestamp", "ingestion_timestamp")
    )

    # Convert string timestamp to proper timestamp type
    df = df.withColumn("event_timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"))

    # Add derived fields
    df = df.withColumn(
        "battery_status",
        expr("""
            CASE
                WHEN battery_level >= 80 THEN 'Good'
                WHEN battery_level >= 50 THEN 'Fair'
                WHEN battery_level >= 20 THEN 'Low'
                ELSE 'Critical'
            END
        """)
    ).withColumn(
        "signal_status",
        expr("""
            CASE
                WHEN signal_strength >= -50 THEN 'Excellent'
                WHEN signal_strength >= -70 THEN 'Good'
                WHEN signal_strength >= -90 THEN 'Fair'
                ELSE 'Poor'
            END
        """)
    ).withColumn(
        "event_id",
        md5(concat_ws("-", col("device_id"), col("timestamp"), col("kafka_offset")))
    )

    # Deduplication using watermark and window function
    df = df.withWatermark("event_timestamp", "10 minutes")

    window_spec = Window.partitionBy("device_id", "event_timestamp").orderBy(col("kafka_offset").desc())

    df = (
        df.withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num", "timestamp")
    )

    return df


@dlt.table(
    name="silver_sensor_readings",
    comment="Enriched sensor readings with metadata",
    table_properties={
        "quality": "silver"
    }
)
@dlt.expect_or_drop("valid_sensor_id", "sensor_id IS NOT NULL")
@dlt.expect_or_drop("valid_reading", "reading_value IS NOT NULL")
def silver_sensor_readings() -> DataFrame:
    """
    Enrich and validate sensor readings from PostgreSQL.

    Transformations:
        - Data validation
        - Type conversions
        - Duplicate removal
        - Add processing metadata

    Returns:
        DataFrame: Validated sensor readings
    """
    logger.info("Processing silver sensor readings")

    df = dlt.read("bronze_sensor_readings")

    # Add processing timestamp
    df = df.withColumn("processing_timestamp", current_timestamp())

    # Deduplication based on sensor_id and reading_timestamp
    window_spec = Window.partitionBy("sensor_id", "reading_timestamp").orderBy(col("updated_at").desc())

    df = (
        df.withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )

    return df


@dlt.table(
    name="silver_device_sessions",
    comment="Sessionized IoT events - groups events by device and time gaps",
    table_properties={
        "quality": "silver"
    }
)
def silver_device_sessions() -> DataFrame:
    """
    Create device sessions by grouping events with time-based sessionization.

    A new session starts when there's a gap of more than 30 minutes between events
    from the same device.

    Returns:
        DataFrame: Sessionized events with session_id
    """
    logger.info("Creating device sessions")

    df = dlt.read("silver_iot_events")

    # Define window for sessionization
    window_spec = Window.partitionBy("device_id").orderBy("event_timestamp")

    # Calculate time difference from previous event
    df = df.withColumn(
        "prev_timestamp",
        lag("event_timestamp").over(window_spec)
    ).withColumn(
        "time_diff_seconds",
        unix_timestamp("event_timestamp") - unix_timestamp("prev_timestamp")
    ).withColumn(
        "new_session",
        expr("CASE WHEN time_diff_seconds > 1800 OR time_diff_seconds IS NULL THEN 1 ELSE 0 END")
    )

    # Create session_id using cumulative sum
    df = df.withColumn(
        "session_num",
        expr("sum(new_session) over (partition by device_id order by event_timestamp)")
    ).withColumn(
        "session_id",
        concat_ws("-", col("device_id"), col("session_num"))
    )

    return df.drop("prev_timestamp", "time_diff_seconds", "new_session", "session_num")


# ============================================================================
# GOLD LAYER: Business Aggregations
# ============================================================================

@dlt.table(
    name="gold_hourly_metrics",
    comment="Hourly aggregated metrics per device",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.zOrderCols": "window_start,device_id"
    }
)
def gold_hourly_metrics() -> DataFrame:
    """
    Hourly aggregations of IoT metrics per device.

    Metrics include:
        - Event counts
        - Temperature statistics (avg, min, max, stddev)
        - Humidity statistics
        - Battery health metrics
        - Signal quality metrics

    Returns:
        DataFrame: Hourly aggregated metrics
    """
    logger.info("Creating gold hourly metrics")

    df = dlt.read("silver_iot_events")

    hourly_agg = (
        df.groupBy(
            window("event_timestamp", "1 hour").alias("window"),
            "device_id"
        ).agg(
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
    )

    # Unpack window struct
    result = (
        hourly_agg
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("device_id"),
            col("event_count"),
            col("avg_temperature"),
            col("min_temperature"),
            col("max_temperature"),
            col("stddev_temperature"),
            col("avg_humidity"),
            col("min_humidity"),
            col("max_humidity"),
            col("avg_pressure"),
            col("avg_battery_level"),
            col("min_battery_level"),
            col("avg_signal_strength"),
            col("last_location_lat"),
            col("last_location_lon"),
            col("last_battery_status"),
            col("last_signal_status"),
            current_timestamp().alias("computed_at")
        )
    )

    return result


@dlt.table(
    name="gold_daily_metrics",
    comment="Daily aggregated metrics per device",
    table_properties={
        "quality": "gold"
    }
)
def gold_daily_metrics() -> DataFrame:
    """
    Daily aggregations of IoT metrics per device.

    Aggregates hourly metrics into daily summaries.

    Returns:
        DataFrame: Daily aggregated metrics
    """
    logger.info("Creating gold daily metrics")

    df = dlt.read("gold_hourly_metrics")

    daily_agg = (
        df.groupBy(
            expr("date(window_start)").alias("date"),
            "device_id"
        ).agg(
            spark_sum("event_count").alias("total_events"),
            avg("avg_temperature").alias("avg_temperature"),
            spark_min("min_temperature").alias("min_temperature"),
            spark_max("max_temperature").alias("max_temperature"),
            avg("avg_humidity").alias("avg_humidity"),
            avg("avg_pressure").alias("avg_pressure"),
            avg("avg_battery_level").alias("avg_battery_level"),
            spark_min("min_battery_level").alias("min_battery_level"),
            avg("avg_signal_strength").alias("avg_signal_strength"),
            count("*").alias("hourly_records_count"),
            current_timestamp().alias("computed_at")
        )
    )

    return daily_agg


@dlt.table(
    name="gold_device_health",
    comment="Current health status of all devices",
    table_properties={
        "quality": "gold"
    }
)
def gold_device_health() -> DataFrame:
    """
    Current health status and latest readings for each device.

    This is a slowly changing dimension (SCD Type 1) that always
    shows the latest state of each device.

    Returns:
        DataFrame: Latest device health metrics
    """
    logger.info("Creating gold device health summary")

    df = dlt.read("silver_iot_events")

    # Get latest record per device
    window_spec = Window.partitionBy("device_id").orderBy(col("event_timestamp").desc())

    latest = (
        df.withColumn("row_num", row_number().over(window_spec))
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

    # Add health indicators
    result = latest.withColumn(
        "health_score",
        expr("""
            CASE
                WHEN battery_level >= 80 AND signal_strength >= -60 THEN 100
                WHEN battery_level >= 50 AND signal_strength >= -80 THEN 75
                WHEN battery_level >= 20 AND signal_strength >= -90 THEN 50
                ELSE 25
            END
        """)
    ).withColumn(
        "requires_attention",
        expr("battery_level < 20 OR signal_strength < -90")
    ).withColumn(
        "computed_at",
        current_timestamp()
    )

    return result


@dlt.table(
    name="gold_kpi_dashboard",
    comment="Executive KPI dashboard - real-time fleet metrics",
    table_properties={
        "quality": "gold"
    }
)
def gold_kpi_dashboard() -> DataFrame:
    """
    High-level KPIs for executive dashboard.

    Provides fleet-wide statistics updated in real-time:
        - Total active devices
        - Devices requiring attention
        - Average fleet health score
        - Event processing statistics

    Returns:
        DataFrame: Executive KPI metrics
    """
    logger.info("Creating gold KPI dashboard")

    health = dlt.read("gold_device_health")

    # Calculate fleet-wide KPIs
    kpis = health.agg(
        count("device_id").alias("total_devices"),
        spark_sum(expr("CAST(requires_attention AS INT)")).alias("devices_requiring_attention"),
        avg("health_score").alias("avg_fleet_health"),
        avg("battery_level").alias("avg_battery_level"),
        avg("signal_strength").alias("avg_signal_strength"),
        percentile_approx("battery_level", 0.5).alias("median_battery_level"),
        current_timestamp().alias("snapshot_timestamp")
    )

    # Add derived metrics
    result = kpis.withColumn(
        "fleet_status",
        expr("""
            CASE
                WHEN avg_fleet_health >= 90 THEN 'Excellent'
                WHEN avg_fleet_health >= 75 THEN 'Good'
                WHEN avg_fleet_health >= 50 THEN 'Fair'
                ELSE 'Poor'
            END
        """)
    ).withColumn(
        "attention_rate",
        expr("devices_requiring_attention / total_devices * 100")
    )

    return result


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def lag(column_name: str) -> Column:
    """
    Helper function to get previous value in window.

    Args:
        column_name: Name of the column to lag

    Returns:
        Column: Lagged column expression
    """
    from pyspark.sql.functions import lag as spark_lag
    return spark_lag(column_name, 1)
