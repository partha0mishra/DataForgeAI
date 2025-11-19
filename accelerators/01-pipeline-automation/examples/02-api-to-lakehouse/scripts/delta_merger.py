"""
Delta Lake Merge/Upsert Processor

Production-ready script for merging data into Delta Lake tables with:
- MERGE INTO operations for upserts
- Schema evolution handling
- Optimize and vacuum operations
- Change data capture support
- Data quality validations

Author: DataForgeAI
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, current_timestamp, lit, when, sha2, concat_ws,
    to_timestamp, coalesce
)
from delta import DeltaTable
from delta.tables import DeltaMergeBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MergeConfig:
    """Configuration for Delta Lake merge operations."""
    source_path: str
    target_path: str
    merge_keys: List[str]
    update_condition: Optional[str] = None
    partition_cols: Optional[List[str]] = None
    enable_schema_evolution: bool = True
    enable_cdf: bool = True  # Change Data Feed
    optimize_after_merge: bool = True
    vacuum_after_merge: bool = False
    vacuum_retention_hours: int = 168  # 7 days
    quality_checks: bool = True


class DeltaMerger:
    """
    Production-ready Delta Lake merge processor.
    """

    def __init__(self, config: MergeConfig, spark: Optional[SparkSession] = None):
        """
        Initialize Delta merger.

        Args:
            config: Merge configuration
            spark: Spark session (creates new if not provided)
        """
        self.config = config
        self.spark = spark or self._create_spark_session()

    def _create_spark_session(self) -> SparkSession:
        """
        Create Spark session with Delta Lake configuration.

        Returns:
            Configured Spark session
        """
        builder = (
            SparkSession.builder
            .appName("DeltaLakeMerger")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .config("spark.databricks.delta.properties.defaults.enableChangeDataFeed", str(self.config.enable_cdf))
            .config("spark.databricks.delta.schema.autoMerge.enabled", str(self.config.enable_schema_evolution))
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        )

        # Add cloud-specific configurations if needed
        if 'AWS_ACCESS_KEY_ID' in os.environ:
            builder = builder.config("spark.hadoop.fs.s3a.access.key", os.environ['AWS_ACCESS_KEY_ID'])
            builder = builder.config("spark.hadoop.fs.s3a.secret.key", os.environ['AWS_SECRET_ACCESS_KEY'])

        return builder.getOrCreate()

    def read_source_data(self) -> DataFrame:
        """
        Read source data from Parquet/JSON files.

        Returns:
            Source DataFrame
        """
        logger.info(f"Reading source data from {self.config.source_path}")

        try:
            # Detect file format
            if self.config.source_path.endswith('.parquet'):
                df = self.spark.read.parquet(self.config.source_path)
            elif self.config.source_path.endswith('.json'):
                df = self.spark.read.json(self.config.source_path)
            else:
                # Try to infer
                df = self.spark.read.format("parquet").load(self.config.source_path)

            record_count = df.count()
            logger.info(f"Read {record_count} records from source")

            return df

        except Exception as e:
            logger.error(f"Failed to read source data: {e}")
            raise

    def validate_source_data(self, df: DataFrame) -> DataFrame:
        """
        Validate source data quality.

        Args:
            df: Source DataFrame

        Returns:
            Validated DataFrame

        Raises:
            ValueError: If validation fails
        """
        if not self.config.quality_checks:
            return df

        logger.info("Running data quality validations")

        # Check merge keys are not null
        for key in self.config.merge_keys:
            null_count = df.filter(col(key).isNull()).count()
            if null_count > 0:
                raise ValueError(
                    f"Merge key '{key}' has {null_count} null values. "
                    "Cannot merge with null keys."
                )

        # Check for duplicates on merge keys
        total_count = df.count()
        distinct_count = df.select(*self.config.merge_keys).distinct().count()

        if total_count != distinct_count:
            logger.warning(
                f"Source data has duplicates on merge keys. "
                f"Total: {total_count}, Distinct: {distinct_count}"
            )
            # Keep most recent record (assuming updated_at column exists)
            if 'updated_at' in df.columns:
                logger.info("Deduplicating based on updated_at timestamp")
                df = self._deduplicate_data(df)

        logger.info("Data quality validation passed")
        return df

    def _deduplicate_data(self, df: DataFrame) -> DataFrame:
        """
        Deduplicate data keeping most recent records.

        Args:
            df: DataFrame to deduplicate

        Returns:
            Deduplicated DataFrame
        """
        from pyspark.sql.window import Window
        from pyspark.sql.functions import row_number, desc

        window_spec = Window.partitionBy(*self.config.merge_keys).orderBy(desc("updated_at"))

        return (
            df
            .withColumn("_row_num", row_number().over(window_spec))
            .filter(col("_row_num") == 1)
            .drop("_row_num")
        )

    def prepare_source_data(self, df: DataFrame) -> DataFrame:
        """
        Prepare source data for merge by adding metadata columns.

        Args:
            df: Source DataFrame

        Returns:
            Prepared DataFrame
        """
        logger.info("Preparing source data")

        # Add metadata columns
        df = (
            df
            .withColumn("_merge_timestamp", current_timestamp())
            .withColumn("_merge_date", current_timestamp().cast("date"))
        )

        # Add row hash for change detection
        all_cols = [c for c in df.columns if not c.startswith('_')]
        df = df.withColumn(
            "_row_hash",
            sha2(concat_ws("||", *[coalesce(col(c).cast("string"), lit("")) for c in all_cols]), 256)
        )

        return df

    def create_or_get_delta_table(self, source_df: DataFrame) -> DeltaTable:
        """
        Create Delta table if not exists, or get existing table.

        Args:
            source_df: Source DataFrame (for schema)

        Returns:
            Delta table
        """
        if DeltaTable.isDeltaTable(self.spark, self.config.target_path):
            logger.info(f"Delta table exists at {self.config.target_path}")
            return DeltaTable.forPath(self.spark, self.config.target_path)

        logger.info(f"Creating new Delta table at {self.config.target_path}")

        # Write initial data
        writer = source_df.write.format("delta")

        if self.config.partition_cols:
            writer = writer.partitionBy(*self.config.partition_cols)

        writer.mode("overwrite").save(self.config.target_path)

        return DeltaTable.forPath(self.spark, self.config.target_path)

    def merge_data(self, source_df: DataFrame, target_table: DeltaTable) -> Dict[str, Any]:
        """
        Merge source data into target Delta table.

        Args:
            source_df: Source DataFrame
            target_table: Target Delta table

        Returns:
            Merge statistics
        """
        logger.info("Starting merge operation")

        # Build merge condition
        merge_condition = " AND ".join([
            f"source.{key} = target.{key}"
            for key in self.config.merge_keys
        ])

        logger.info(f"Merge condition: {merge_condition}")

        # Build merge
        merge_builder = (
            target_table.alias("target")
            .merge(source_df.alias("source"), merge_condition)
        )

        # Define update condition (only update if data changed)
        if self.config.update_condition:
            update_condition = self.config.update_condition
        else:
            # Default: update if row hash changed
            update_condition = "source._row_hash <> target._row_hash"

        # Get all columns except merge keys and metadata
        update_cols = {
            col: f"source.{col}"
            for col in source_df.columns
            if col not in self.config.merge_keys
        }

        # Execute merge
        merge_result = (
            merge_builder
            .whenMatchedUpdate(
                condition=update_condition,
                set=update_cols
            )
            .whenNotMatchedInsertAll()
            .execute()
        )

        logger.info("Merge operation completed")

        # Get merge statistics
        stats = self._get_merge_stats(target_table)
        return stats

    def _get_merge_stats(self, target_table: DeltaTable) -> Dict[str, Any]:
        """
        Get statistics about the merge operation.

        Args:
            target_table: Target Delta table

        Returns:
            Statistics dictionary
        """
        # Get latest operation metrics
        history = target_table.history(1).select("operationMetrics").collect()

        if history:
            metrics = history[0]["operationMetrics"]
            logger.info(f"Merge metrics: {metrics}")
            return metrics
        else:
            return {}

    def optimize_table(self, target_table: DeltaTable) -> None:
        """
        Optimize Delta table by compacting small files.

        Args:
            target_table: Target Delta table
        """
        if not self.config.optimize_after_merge:
            return

        logger.info("Optimizing Delta table")

        try:
            # Run optimize with Z-ordering if partition columns specified
            if self.config.partition_cols:
                target_table.optimize().executeZOrderBy(*self.config.partition_cols)
            else:
                target_table.optimize().executeCompaction()

            logger.info("Table optimization completed")

        except Exception as e:
            logger.warning(f"Optimization failed: {e}")

    def vacuum_table(self, target_table: DeltaTable) -> None:
        """
        Vacuum old files from Delta table.

        Args:
            target_table: Target Delta table
        """
        if not self.config.vacuum_after_merge:
            return

        logger.info(f"Vacuuming table (retention: {self.config.vacuum_retention_hours} hours)")

        try:
            target_table.vacuum(self.config.vacuum_retention_hours / 24)  # Convert to days
            logger.info("Vacuum completed")

        except Exception as e:
            logger.warning(f"Vacuum failed: {e}")

    def run(self) -> Dict[str, Any]:
        """
        Execute complete merge pipeline.

        Returns:
            Merge statistics
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("Starting Delta Lake merge process")
        logger.info(f"Source: {self.config.source_path}")
        logger.info(f"Target: {self.config.target_path}")
        logger.info(f"Merge keys: {self.config.merge_keys}")
        logger.info("=" * 80)

        try:
            # Step 1: Read source data
            source_df = self.read_source_data()

            # Step 2: Validate data quality
            source_df = self.validate_source_data(source_df)

            # Step 3: Prepare data
            source_df = self.prepare_source_data(source_df)

            # Step 4: Create or get target table
            target_table = self.create_or_get_delta_table(source_df)

            # Step 5: Merge data
            merge_stats = self.merge_data(source_df, target_table)

            # Step 6: Optimize table
            self.optimize_table(target_table)

            # Step 7: Vacuum old files
            self.vacuum_table(target_table)

            # Calculate elapsed time
            elapsed_time = (datetime.now() - start_time).total_seconds()

            logger.info("=" * 80)
            logger.info("Merge process completed successfully")
            logger.info(f"Elapsed time: {elapsed_time:.2f} seconds")
            logger.info("=" * 80)

            return {
                'status': 'success',
                'elapsed_time': elapsed_time,
                'metrics': merge_stats
            }

        except Exception as e:
            logger.error(f"Merge process failed: {e}")
            raise


def main():
    """
    Example usage of Delta merger.
    """
    config = MergeConfig(
        source_path=os.getenv('SOURCE_PATH', './data/shopify/orders_*.parquet'),
        target_path=os.getenv('TARGET_PATH', 's3a://lakehouse/bronze/shopify/orders'),
        merge_keys=['id'],
        partition_cols=['_merge_date'],
        enable_schema_evolution=True,
        optimize_after_merge=True,
        vacuum_after_merge=False,
    )

    merger = DeltaMerger(config)

    try:
        result = merger.run()
        print(f"Merge successful: {result}")
    except Exception as e:
        print(f"Merge failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
