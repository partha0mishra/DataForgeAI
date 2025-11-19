"""
AWS Glue ETL Job - Cost-Optimized Data Processing
Reads data from S3, applies transformations, and writes optimized Parquet files.

Features:
- Incremental processing with job bookmarks
- Partition pruning for query optimization
- Push-down predicates for Athena
- Data quality checks
- Cost-optimized file sizes (128-256 MB per file)
"""

import sys
from datetime import datetime
from typing import Dict, List, Optional

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, current_timestamp, date_format, lit,
    regexp_replace, trim, upper, when, year, month, dayofmonth
)
from pyspark.sql.types import DoubleType, StringType


# Job parameters
args = getResolvedOptions(
    sys.argv,
    [
        'JOB_NAME',
        'source_bucket',
        'source_prefix',
        'target_bucket',
        'target_prefix',
        'database_name',
        'table_name',
        'partition_keys',  # comma-separated list
        'file_format',  # csv, json, or parquet
    ]
)


class GlueETLJob:
    """AWS Glue ETL Job for cost-optimized data processing."""

    def __init__(self, args: Dict[str, str]):
        """Initialize Glue job with SparkContext and GlueContext."""
        self.args = args
        self.sc = SparkContext()
        self.glue_context = GlueContext(self.sc)
        self.spark = self.glue_context.spark_session
        self.job = Job(self.glue_context)
        self.job.init(args['JOB_NAME'], args)

        # Cost optimization: Configure Spark for efficient processing
        self.spark.conf.set("spark.sql.files.maxPartitionBytes", "134217728")  # 128 MB
        self.spark.conf.set("spark.sql.adaptive.enabled", "true")
        self.spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")

        # Partition keys
        self.partition_keys = [k.strip() for k in args['partition_keys'].split(',')]

    def read_source_data(self) -> DynamicFrame:
        """
        Read data from S3 using Glue DynamicFrame.
        Supports incremental processing with job bookmarks.
        """
        source_path = f"s3://{self.args['source_bucket']}/{self.args['source_prefix']}/"
        file_format = self.args['file_format'].lower()

        print(f"Reading {file_format} data from: {source_path}")

        # Use Glue DynamicFrame for schema inference and job bookmarks
        if file_format == 'csv':
            dynamic_frame = self.glue_context.create_dynamic_frame.from_options(
                connection_type="s3",
                connection_options={
                    "paths": [source_path],
                    "recurse": True
                },
                format="csv",
                format_options={
                    "withHeader": True,
                    "separator": ",",
                    "optimizePerformance": True,
                },
                transformation_ctx="source_data"
            )
        elif file_format == 'json':
            dynamic_frame = self.glue_context.create_dynamic_frame.from_options(
                connection_type="s3",
                connection_options={
                    "paths": [source_path],
                    "recurse": True
                },
                format="json",
                transformation_ctx="source_data"
            )
        elif file_format == 'parquet':
            dynamic_frame = self.glue_context.create_dynamic_frame.from_options(
                connection_type="s3",
                connection_options={
                    "paths": [source_path],
                    "recurse": True
                },
                format="parquet",
                transformation_ctx="source_data"
            )
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

        print(f"Read {dynamic_frame.count()} records from source")
        return dynamic_frame

    def apply_transformations(self, df: DataFrame) -> DataFrame:
        """
        Apply data transformations including cleansing and enrichment.

        Transformations:
        1. Remove duplicates
        2. Trim whitespace
        3. Standardize text fields
        4. Handle null values
        5. Add metadata columns
        6. Data type conversions
        """
        print("Applying transformations...")

        # Remove duplicate records
        df = df.dropDuplicates()

        # Add processing metadata
        df = df.withColumn("processed_at", current_timestamp())
        df = df.withColumn("processing_date", date_format(current_timestamp(), "yyyy-MM-dd"))

        # Cleansing: Trim whitespace from string columns
        string_columns = [field.name for field in df.schema.fields
                         if isinstance(field.dataType, StringType)]

        for col_name in string_columns:
            df = df.withColumn(col_name, trim(col(col_name)))

        # Handle null values - replace empty strings with null
        for col_name in string_columns:
            df = df.withColumn(
                col_name,
                when(col(col_name) == "", None).otherwise(col(col_name))
            )

        # Data quality: Filter out records with critical null values
        # Adjust based on your business rules
        if 'customer_id' in df.columns:
            initial_count = df.count()
            df = df.filter(col('customer_id').isNotNull())
            filtered_count = initial_count - df.count()
            print(f"Filtered {filtered_count} records with null customer_id")

        # Enrichment: Add derived columns for partitioning
        if 'transaction_date' in df.columns:
            df = df.withColumn('year', year(col('transaction_date')))
            df = df.withColumn('month', month(col('transaction_date')))
            df = df.withColumn('day', dayofmonth(col('transaction_date')))

        print(f"Transformation complete. Record count: {df.count()}")
        return df

    def write_optimized_parquet(self, df: DataFrame) -> None:
        """
        Write data to S3 in optimized Parquet format.

        Optimizations:
        - Partitioned by specified keys for query performance
        - Coalesced to optimal file sizes (128-256 MB)
        - Snappy compression for balance of speed and size
        - Column statistics for push-down predicates
        """
        target_path = f"s3://{self.args['target_bucket']}/{self.args['target_prefix']}/"

        print(f"Writing optimized Parquet to: {target_path}")
        print(f"Partition keys: {self.partition_keys}")

        # Cost optimization: Coalesce to create larger, fewer files
        # Target 128-256 MB per file for optimal Athena performance
        record_count = df.count()
        estimated_size_mb = record_count * 0.001  # Rough estimate: 1KB per record
        num_partitions = max(1, int(estimated_size_mb / 200))  # Target 200 MB files

        print(f"Coalescing to {num_partitions} partitions for optimal file size")
        df = df.coalesce(num_partitions)

        # Write partitioned Parquet with optimizations
        (df.write
            .mode("overwrite")
            .partitionBy(*self.partition_keys)
            .option("compression", "snappy")
            .option("parquet.block.size", 134217728)  # 128 MB block size
            .option("parquet.page.size", 1048576)  # 1 MB page size
            .parquet(target_path))

        print("Write complete")

    def update_glue_catalog(self, df: DataFrame) -> None:
        """
        Update AWS Glue Data Catalog with table metadata.
        Enables Athena queries with partition pruning.
        """
        target_path = f"s3://{self.args['target_bucket']}/{self.args['target_prefix']}/"

        print(f"Updating Glue Catalog: {self.args['database_name']}.{self.args['table_name']}")

        # Create or update Glue table
        dynamic_frame = DynamicFrame.fromDF(
            df,
            self.glue_context,
            "updated_data"
        )

        # Write to Glue Catalog
        self.glue_context.write_dynamic_frame.from_catalog(
            frame=dynamic_frame,
            database=self.args['database_name'],
            table_name=self.args['table_name'],
            transformation_ctx="write_catalog"
        )

        print("Glue Catalog updated successfully")

    def run(self) -> None:
        """Execute the complete ETL pipeline."""
        try:
            print(f"Starting Glue job: {self.args['JOB_NAME']}")
            print(f"Timestamp: {datetime.now().isoformat()}")

            # Step 1: Read source data
            dynamic_frame = self.read_source_data()

            # Convert to DataFrame for transformations
            df = dynamic_frame.toDF()

            # Step 2: Apply transformations
            df = self.apply_transformations(df)

            # Step 3: Write optimized Parquet
            self.write_optimized_parquet(df)

            # Step 4: Update Glue Catalog (optional, can be done by Crawler)
            # Uncomment if you want to update catalog directly
            # self.update_glue_catalog(df)

            # Commit job bookmark for incremental processing
            self.job.commit()

            print(f"Job completed successfully at {datetime.now().isoformat()}")

        except Exception as e:
            print(f"Job failed with error: {str(e)}")
            raise


def main():
    """Main entry point for Glue job."""
    job = GlueETLJob(args)
    job.run()


if __name__ == "__main__":
    main()
