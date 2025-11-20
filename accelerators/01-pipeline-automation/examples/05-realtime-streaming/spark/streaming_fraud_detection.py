#!/usr/bin/env python3
"""
Real-time Fraud Detection using Spark Structured Streaming
===========================================================

Complete implementation of fraud detection pipeline with:
    - Kinesis stream ingestion
    - 5-minute tumbling window aggregations
    - Stream-static joins with Redis for customer risk scores
    - Real-time fraud score calculation
    - Delta Lake sink for fraud events
    - Slack alerting for high-risk transactions
    - Watermarking for late data handling
    - Exactly-once processing semantics

Architecture:
    Kinesis → Spark Streaming → [Window Agg + Redis Join] → [Fraud Scoring] → Delta Lake + Slack

Author: DataForgeAI Team
Version: 1.0.0
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, Iterator
from datetime import datetime, timedelta

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, from_json, expr, window, count, avg, sum as spark_sum,
    max as spark_max, min as spark_min, current_timestamp, lit,
    stddev, when, udf, concat_ws, struct, to_json,
    unix_timestamp, to_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    TimestampType, IntegerType, LongType, BooleanType,
    FloatType
)
from delta.tables import DeltaTable
import redis

# Import Slack notifier (assumes it's in the same package)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from alerts.slack_notifier import SlackNotifier
except ImportError:
    SlackNotifier = None
    logging.warning("SlackNotifier not available - alerts will be disabled")

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kinesis configuration
KINESIS_CONFIG = {
    "stream_name": os.getenv("KINESIS_STREAM_NAME", "transactions"),
    "region": os.getenv("AWS_REGION", "us-east-1"),
    "endpoint_url": os.getenv("KINESIS_ENDPOINT_URL", None),  # For LocalStack
    "starting_position": "TRIM_HORIZON"  # Or "LATEST"
}

# Redis configuration
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": int(os.getenv("REDIS_DB", 0)),
    "password": os.getenv("REDIS_PASSWORD", None)
}

# Delta Lake configuration
DELTA_CONFIG = {
    "base_path": os.getenv("DELTA_LAKE_PATH", "s3://your-bucket/fraud-detection"),
    "checkpoint_path": os.getenv("CHECKPOINT_PATH", "s3://your-bucket/checkpoints"),
    "fraud_events_path": os.getenv("FRAUD_EVENTS_PATH", "s3://your-bucket/fraud-detection/fraud_events")
}

# Fraud detection thresholds
FRAUD_THRESHOLDS = {
    "high_risk_score": 0.8,
    "max_amount_per_window": 10000.0,
    "max_transactions_per_window": 50,
    "suspicious_merchant_categories": ["GAMBLING", "CRYPTO", "WIRE_TRANSFER"],
    "high_risk_countries": ["NG", "PK", "RU", "CN"]
}

# Window configuration
WINDOW_CONFIG = {
    "duration": "5 minutes",
    "watermark": "10 minutes"
}

# Transaction schema
TRANSACTION_SCHEMA = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("customer_id", StringType(), False),
    StructField("timestamp", StringType(), False),
    StructField("amount", DoubleType(), False),
    StructField("currency", StringType(), True),
    StructField("merchant_id", StringType(), True),
    StructField("merchant_category", StringType(), True),
    StructField("merchant_country", StringType(), True),
    StructField("card_last_4", StringType(), True),
    StructField("location_lat", DoubleType(), True),
    StructField("location_lon", DoubleType(), True),
    StructField("ip_address", StringType(), True),
    StructField("device_id", StringType(), True)
])


# ============================================================================
# REDIS CONNECTION
# ============================================================================

class RedisConnection:
    """Thread-safe Redis connection manager."""

    _instance = None
    _connection = None

    @classmethod
    def get_instance(cls) -> redis.Redis:
        """Get Redis connection instance."""
        if cls._connection is None:
            cls._connection = redis.Redis(
                host=REDIS_CONFIG["host"],
                port=REDIS_CONFIG["port"],
                db=REDIS_CONFIG["db"],
                password=REDIS_CONFIG["password"],
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            logger.info(f"Connected to Redis at {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")

        return cls._connection


def get_customer_risk_score(customer_id: str) -> float:
    """
    Retrieve customer risk score from Redis.

    Args:
        customer_id: Customer identifier

    Returns:
        float: Risk score (0.0 to 1.0), default 0.5 if not found
    """
    if not customer_id:
        return 0.5

    try:
        redis_client = RedisConnection.get_instance()
        risk_score = redis_client.hget("customer_risk_scores", customer_id)

        if risk_score:
            return float(risk_score)
        else:
            return 0.5  # Default risk score for unknown customers

    except Exception as e:
        logger.error(f"Error fetching risk score for {customer_id}: {e}")
        return 0.5


# Register UDF for Redis lookup
get_customer_risk_score_udf = udf(get_customer_risk_score, FloatType())


# ============================================================================
# FRAUD DETECTION LOGIC
# ============================================================================

def calculate_fraud_score(
    customer_risk_score: float,
    amount: float,
    transaction_count: int,
    total_amount: float,
    unique_merchants: int,
    merchant_category: str,
    merchant_country: str,
    avg_amount: float,
    stddev_amount: float
) -> float:
    """
    Calculate fraud score based on multiple factors.

    Scoring factors:
        - Customer risk score (0-1)
        - Transaction amount vs window average
        - Number of transactions in window
        - Merchant category
        - Merchant country
        - Amount volatility

    Args:
        customer_risk_score: Pre-computed customer risk
        amount: Transaction amount
        transaction_count: Transactions in window
        total_amount: Total amount in window
        unique_merchants: Number of unique merchants
        merchant_category: Merchant category code
        merchant_country: Merchant country code
        avg_amount: Average amount in window
        stddev_amount: Standard deviation of amounts

    Returns:
        float: Fraud score (0.0 to 1.0)
    """
    score = 0.0

    # Factor 1: Customer risk score (weight: 30%)
    score += customer_risk_score * 0.3

    # Factor 2: High transaction amount (weight: 25%)
    if amount > 5000:
        score += 0.25
    elif amount > 2000:
        score += 0.15
    elif amount > 1000:
        score += 0.05

    # Factor 3: Transaction velocity (weight: 20%)
    if transaction_count > FRAUD_THRESHOLDS["max_transactions_per_window"]:
        score += 0.20
    elif transaction_count > 30:
        score += 0.15
    elif transaction_count > 20:
        score += 0.10

    # Factor 4: Suspicious merchant (weight: 15%)
    if merchant_category in FRAUD_THRESHOLDS["suspicious_merchant_categories"]:
        score += 0.15
    if merchant_country in FRAUD_THRESHOLDS["high_risk_countries"]:
        score += 0.10

    # Factor 5: Amount volatility (weight: 10%)
    if avg_amount and stddev_amount:
        if stddev_amount > avg_amount:
            score += 0.10
        elif stddev_amount > avg_amount * 0.5:
            score += 0.05

    # Normalize to 0-1 range
    return min(1.0, score)


# Register UDF for fraud scoring
calculate_fraud_score_udf = udf(calculate_fraud_score, FloatType())


# ============================================================================
# STREAMING PIPELINE
# ============================================================================

class FraudDetectionPipeline:
    """Real-time fraud detection streaming pipeline."""

    def __init__(self, spark: SparkSession):
        """
        Initialize fraud detection pipeline.

        Args:
            spark: SparkSession instance
        """
        self.spark = spark
        self.slack_notifier = None

        if SlackNotifier:
            slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
            if slack_webhook:
                self.slack_notifier = SlackNotifier(slack_webhook)
                logger.info("Slack notifier initialized")

    def read_from_kinesis(self) -> DataFrame:
        """
        Read streaming data from Kinesis.

        Returns:
            DataFrame: Raw Kinesis stream
        """
        logger.info(f"Reading from Kinesis stream: {KINESIS_CONFIG['stream_name']}")

        # Note: Kinesis source requires additional configuration
        # Using Kafka format as example (replace with actual Kinesis connector)
        kinesis_df = (
            self.spark.readStream
            .format("kinesis")
            .option("streamName", KINESIS_CONFIG["stream_name"])
            .option("region", KINESIS_CONFIG["region"])
            .option("initialPosition", KINESIS_CONFIG["starting_position"])
            .load()
        )

        return kinesis_df

    def parse_transactions(self, raw_df: DataFrame) -> DataFrame:
        """
        Parse JSON transactions from Kinesis stream.

        Args:
            raw_df: Raw Kinesis DataFrame

        Returns:
            DataFrame: Parsed transactions
        """
        logger.info("Parsing transaction data")

        parsed_df = (
            raw_df
            .select(
                from_json(col("data").cast("string"), TRANSACTION_SCHEMA).alias("transaction")
            )
            .select("transaction.*")
            .withColumn("event_timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"))
            .withColumn("processing_timestamp", current_timestamp())
        )

        # Add watermark for late data handling
        parsed_df = parsed_df.withWatermark("event_timestamp", WINDOW_CONFIG["watermark"])

        return parsed_df

    def enrich_with_risk_scores(self, transactions_df: DataFrame) -> DataFrame:
        """
        Enrich transactions with customer risk scores from Redis.

        Args:
            transactions_df: Transaction DataFrame

        Returns:
            DataFrame: Enriched with risk scores
        """
        logger.info("Enriching with customer risk scores from Redis")

        enriched_df = transactions_df.withColumn(
            "customer_risk_score",
            get_customer_risk_score_udf(col("customer_id"))
        )

        return enriched_df

    def calculate_window_aggregations(self, enriched_df: DataFrame) -> DataFrame:
        """
        Calculate windowed aggregations per customer.

        Args:
            enriched_df: Enriched transaction DataFrame

        Returns:
            DataFrame: Window aggregations
        """
        logger.info(f"Calculating window aggregations (window: {WINDOW_CONFIG['duration']})")

        # Tumbling window aggregations
        window_agg = (
            enriched_df
            .groupBy(
                window("event_timestamp", WINDOW_CONFIG["duration"]),
                "customer_id"
            )
            .agg(
                count("*").alias("transaction_count"),
                spark_sum("amount").alias("total_amount"),
                avg("amount").alias("avg_amount"),
                spark_max("amount").alias("max_amount"),
                spark_min("amount").alias("min_amount"),
                stddev("amount").alias("stddev_amount"),
                countDistinct("merchant_id").alias("unique_merchants"),
                countDistinct("merchant_country").alias("unique_countries")
            )
        )

        # Join back with transactions to get individual transaction details
        result = (
            enriched_df.alias("t")
            .join(
                window_agg.alias("w"),
                (col("t.customer_id") == col("w.customer_id")) &
                (col("t.event_timestamp") >= col("w.window.start")) &
                (col("t.event_timestamp") < col("w.window.end")),
                "left"
            )
            .select(
                col("t.*"),
                col("w.window.start").alias("window_start"),
                col("w.window.end").alias("window_end"),
                col("w.transaction_count"),
                col("w.total_amount"),
                col("w.avg_amount"),
                col("w.max_amount"),
                col("w.min_amount"),
                col("w.stddev_amount"),
                col("w.unique_merchants"),
                col("w.unique_countries")
            )
        )

        return result

    def detect_fraud(self, aggregated_df: DataFrame) -> DataFrame:
        """
        Apply fraud detection logic.

        Args:
            aggregated_df: DataFrame with window aggregations

        Returns:
            DataFrame: Transactions with fraud scores
        """
        logger.info("Applying fraud detection logic")

        # Calculate fraud score
        fraud_df = aggregated_df.withColumn(
            "fraud_score",
            calculate_fraud_score_udf(
                col("customer_risk_score"),
                col("amount"),
                col("transaction_count"),
                col("total_amount"),
                col("unique_merchants"),
                col("merchant_category"),
                col("merchant_country"),
                col("avg_amount"),
                col("stddev_amount")
            )
        )

        # Flag as fraud if score exceeds threshold
        fraud_df = fraud_df.withColumn(
            "is_fraud",
            col("fraud_score") >= FRAUD_THRESHOLDS["high_risk_score"]
        ).withColumn(
            "risk_level",
            when(col("fraud_score") >= 0.8, "HIGH")
            .when(col("fraud_score") >= 0.5, "MEDIUM")
            .otherwise("LOW")
        )

        return fraud_df

    def write_to_delta(self, fraud_df: DataFrame) -> None:
        """
        Write fraud events to Delta Lake.

        Args:
            fraud_df: DataFrame with fraud scores
        """
        logger.info(f"Writing fraud events to Delta Lake: {DELTA_CONFIG['fraud_events_path']}")

        # Filter for fraud events only
        fraud_events = fraud_df.filter(col("is_fraud") == True)

        # Write to Delta Lake with checkpointing
        query = (
            fraud_events.writeStream
            .format("delta")
            .outputMode("append")
            .option("checkpointLocation", f"{DELTA_CONFIG['checkpoint_path']}/fraud_events")
            .option("mergeSchema", "true")
            .trigger(processingTime="30 seconds")
            .start(DELTA_CONFIG["fraud_events_path"])
        )

        logger.info("Streaming write to Delta Lake started")
        return query

    def send_alerts(self, fraud_df: DataFrame) -> None:
        """
        Send alerts for high-risk transactions via Slack.

        Args:
            fraud_df: DataFrame with fraud scores
        """
        if not self.slack_notifier:
            logger.warning("Slack notifier not configured - skipping alerts")
            return

        logger.info("Setting up fraud alert notifications")

        # Filter high-risk transactions
        high_risk = fraud_df.filter(col("fraud_score") >= FRAUD_THRESHOLDS["high_risk_score"])

        def send_slack_alert(batch_df: DataFrame, batch_id: int) -> None:
            """
            Process each micro-batch and send Slack alerts.

            Args:
                batch_df: Batch DataFrame
                batch_id: Batch identifier
            """
            if batch_df.isEmpty():
                return

            logger.info(f"Processing batch {batch_id} with {batch_df.count()} high-risk transactions")

            # Collect fraud events (limit to prevent spam)
            fraud_events = batch_df.limit(10).collect()

            for row in fraud_events:
                transaction_data = {
                    "transaction_id": row["transaction_id"],
                    "customer_id": row["customer_id"],
                    "amount": row["amount"],
                    "currency": row["currency"],
                    "merchant_id": row["merchant_id"],
                    "merchant_category": row["merchant_category"],
                    "fraud_score": row["fraud_score"],
                    "risk_level": row["risk_level"],
                    "timestamp": str(row["event_timestamp"])
                }

                try:
                    self.slack_notifier.send_fraud_alert(transaction_data)
                except Exception as e:
                    logger.error(f"Failed to send Slack alert: {e}")

        # Write stream with foreachBatch for alerting
        query = (
            high_risk.writeStream
            .foreachBatch(send_slack_alert)
            .option("checkpointLocation", f"{DELTA_CONFIG['checkpoint_path']}/alerts")
            .trigger(processingTime="30 seconds")
            .start()
        )

        logger.info("Alert streaming query started")
        return query

    def run(self) -> None:
        """Execute the complete fraud detection pipeline."""
        logger.info("=" * 80)
        logger.info("STARTING FRAUD DETECTION PIPELINE")
        logger.info("=" * 80)

        try:
            # 1. Read from Kinesis
            raw_stream = self.read_from_kinesis()

            # 2. Parse transactions
            transactions = self.parse_transactions(raw_stream)

            # 3. Enrich with risk scores from Redis
            enriched = self.enrich_with_risk_scores(transactions)

            # 4. Calculate window aggregations
            aggregated = self.calculate_window_aggregations(enriched)

            # 5. Detect fraud
            fraud_detected = self.detect_fraud(aggregated)

            # 6. Write to Delta Lake
            delta_query = self.write_to_delta(fraud_detected)

            # 7. Send alerts
            alert_query = self.send_alerts(fraud_detected)

            # 8. Wait for termination
            logger.info("Pipeline running... Press Ctrl+C to stop")
            if delta_query:
                delta_query.awaitTermination()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping pipeline...")
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            raise
        finally:
            logger.info("Pipeline stopped")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    logger.info("Initializing Spark session...")

    # Create Spark session with Delta Lake support
    spark = (
        SparkSession.builder
        .appName("Fraud Detection - Real-time Streaming")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.streaming.checkpointLocation", DELTA_CONFIG["checkpoint_path"])
        .config("spark.sql.streaming.schemaInference", "true")
        .config("spark.databricks.delta.optimizeWrite.enabled", "true")
        .config("spark.databricks.delta.autoCompact.enabled", "true")
        # Kinesis-specific configurations
        .config("spark.executor.instances", "4")
        .config("spark.executor.memory", "4g")
        .config("spark.executor.cores", "2")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    # Initialize and run pipeline
    pipeline = FraudDetectionPipeline(spark)
    pipeline.run()


if __name__ == "__main__":
    main()
