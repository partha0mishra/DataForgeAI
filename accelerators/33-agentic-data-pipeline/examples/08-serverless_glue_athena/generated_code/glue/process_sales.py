"""
AWS Glue ETL Job: Process Sales Data
Transforms raw sales data and writes to partitioned Parquet format.
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import col, year, month, dayofmonth, to_date, current_timestamp

# Get job parameters
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'SOURCE_PATH', 'TARGET_PATH'])

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read raw data from S3
raw_dyf = glueContext.create_dynamic_frame.from_options(
    format_options={"quoteChar": '"', "withHeader": True, "separator": ","},
    connection_type="s3",
    format="csv",
    connection_options={
        "paths": [args['SOURCE_PATH']],
        "recurse": True
    }
)

# Convert to Spark DataFrame for transformations
df = raw_dyf.toDF()

# Data transformations
transformed_df = (df
    # Convert date column
    .withColumn("order_date_parsed", to_date(col("order_date")))

    # Add partition columns
    .withColumn("year", year(col("order_date_parsed")))
    .withColumn("month", month(col("order_date_parsed")))
    .withColumn("day", dayofmonth(col("order_date_parsed")))

    # Data quality filters
    .filter(col("order_id").isNotNull())
    .filter(col("customer_id").isNotNull())
    .filter(col("amount") > 0)

    # Add processing metadata
    .withColumn("processed_at", current_timestamp())

    # Select final columns
    .select(
        "order_id",
        col("order_date_parsed").alias("order_date"),
        "customer_id",
        "product_id",
        col("quantity").cast("int"),
        col("amount").cast("decimal(10,2)"),
        "region",
        "year",
        "month",
        "day",
        "processed_at"
    )
)

# Convert back to DynamicFrame
output_dyf = DynamicFrame.fromDF(transformed_df, glueContext, "output_dyf")

# Write partitioned Parquet to S3
glueContext.write_dynamic_frame.from_options(
    frame=output_dyf,
    connection_type="s3",
    format="parquet",
    connection_options={
        "path": args['TARGET_PATH'],
        "partitionKeys": ["year", "month", "day"]
    },
    format_options={
        "compression": "snappy"
    }
)

job.commit()
