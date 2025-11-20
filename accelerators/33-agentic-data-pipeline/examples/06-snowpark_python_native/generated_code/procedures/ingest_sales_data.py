"""
Snowpark Stored Procedure: Ingest Sales Data from S3
This procedure runs natively in Snowflake using Snowpark Python.
"""

from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, current_timestamp, lit
from snowflake.snowpark.types import StructType, StructField, StringType, IntegerType, DecimalType, DateType
import sys


def ingest_sales_data(session: Session, execution_date: str) -> str:
    """
    Ingest sales data from S3 stage into raw table.

    Args:
        session: Snowpark session
        execution_date: Date to process (YYYY-MM-DD format)

    Returns:
        Status message with row count
    """

    # Define schema for sales data
    sales_schema = StructType([
        StructField("sale_id", StringType()),
        StructField("sale_date", StringType()),
        StructField("customer_id", StringType()),
        StructField("product_id", StringType()),
        StructField("quantity", IntegerType()),
        StructField("unit_price", DecimalType(10, 2)),
        StructField("total_amount", DecimalType(10, 2)),
        StructField("region", StringType()),
        StructField("store_id", StringType()),
        StructField("payment_method", StringType())
    ])

    try:
        # Read from S3 stage
        df = (session.read
              .schema(sales_schema)
              .option("SKIP_HEADER", 1)
              .option("FIELD_OPTIONALLY_ENCLOSED_BY", '"')
              .csv(f"@ANALYTICS.STAGES.S3_SALES_STAGE/sales_data_{execution_date}.csv"))

        # Add metadata columns
        df_with_metadata = (df
            .withColumn("ingested_at", current_timestamp())
            .withColumn("execution_date", lit(execution_date))
            .withColumn("source_file", lit(f"sales_data_{execution_date}.csv"))
        )

        # Write to raw table
        df_with_metadata.write.mode("append").save_as_table("ANALYTICS.RAW.SALES")

        row_count = df_with_metadata.count()

        return f"SUCCESS: Ingested {row_count} rows for {execution_date}"

    except Exception as e:
        return f"ERROR: {str(e)}"


# For deployment as stored procedure
def main(session: Session, execution_date: str) -> str:
    return ingest_sales_data(session, execution_date)


# Register as stored procedure
if __name__ == "__main__":
    import snowflake.snowpark as snowpark

    # This code runs when deploying the stored procedure
    # The actual registration happens via SQL DDL (see setup.sql)
    pass
