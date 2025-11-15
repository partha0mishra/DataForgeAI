"""Spark job for large-scale data ingestion."""

import sys
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


def create_spark_session(app_name: str = "DataForge Ingestion") -> SparkSession:
    """Create and configure Spark session."""
    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .getOrCreate()

    logger.info("Spark session created", app_name=app_name)

    return spark


def ingest_from_jdbc(
    spark: SparkSession,
    jdbc_url: str,
    table: str,
    user: str,
    password: str,
    output_path: str
) -> int:
    """
    Ingest data from JDBC source to Parquet.

    Args:
        spark: Spark session
        jdbc_url: JDBC connection URL
        table: Table name
        user: Database user
        password: Database password
        output_path: Output path for Parquet files

    Returns:
        int: Number of records ingested
    """
    logger.info(
        "Starting JDBC ingestion",
        table=table,
        output_path=output_path
    )

    # Read from JDBC
    df = spark.read \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", table) \
        .option("user", user) \
        .option("password", password) \
        .option("driver", "org.postgresql.Driver") \
        .load()

    # Add metadata columns
    df = df.withColumn("ingested_at", F.current_timestamp()) \
           .withColumn("ingestion_date", F.current_date())

    # Count records
    record_count = df.count()

    logger.info(
        "Data loaded from JDBC",
        table=table,
        records=record_count
    )

    # Write to Parquet (partitioned by date)
    df.write \
        .mode("overwrite") \
        .partitionBy("ingestion_date") \
        .parquet(output_path)

    logger.info(
        "Data written to Parquet",
        output_path=output_path,
        records=record_count
    )

    return record_count


def ingest_from_csv(
    spark: SparkSession,
    input_path: str,
    output_path: str,
    schema=None
) -> int:
    """
    Ingest data from CSV files to Parquet.

    Args:
        spark: Spark session
        input_path: Input CSV path (can use wildcards)
        output_path: Output Parquet path
        schema: Optional schema

    Returns:
        int: Number of records ingested
    """
    logger.info(
        "Starting CSV ingestion",
        input_path=input_path,
        output_path=output_path
    )

    # Read CSV
    df_reader = spark.read \
        .option("header", "true") \
        .option("inferSchema", "true" if schema is None else "false")

    if schema:
        df_reader = df_reader.schema(schema)

    df = df_reader.csv(input_path)

    # Add metadata
    df = df.withColumn("ingested_at", F.current_timestamp()) \
           .withColumn("ingestion_date", F.current_date())

    # Count records
    record_count = df.count()

    logger.info("CSV data loaded", records=record_count)

    # Write to Parquet
    df.write \
        .mode("overwrite") \
        .partitionBy("ingestion_date") \
        .parquet(output_path)

    logger.info(
        "Data written to Parquet",
        output_path=output_path,
        records=record_count
    )

    return record_count


def main():
    """Main ingestion job."""
    if len(sys.argv) < 4:
        print("Usage: spark-submit ingestion.py <source_type> <source_path> <output_path>")
        sys.exit(1)

    source_type = sys.argv[1]  # jdbc, csv, json, etc.
    source_path = sys.argv[2]
    output_path = sys.argv[3]

    logger.info(
        "Starting ingestion job",
        source_type=source_type,
        source_path=source_path,
        output_path=output_path
    )

    # Create Spark session
    spark = create_spark_session()

    try:
        if source_type == "csv":
            record_count = ingest_from_csv(spark, source_path, output_path)
        elif source_type == "jdbc":
            # Parse JDBC parameters from source_path
            # Format: jdbc:postgresql://host:port/db?table=tablename
            record_count = 0  # Implement JDBC ingestion
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        logger.info(
            "Ingestion completed successfully",
            records=record_count,
            source_type=source_type
        )

    except Exception as e:
        logger.error(
            "Ingestion failed",
            error=str(e),
            exc_info=True
        )
        raise

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
