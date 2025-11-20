"""
Snowpark Stored Procedure: Transform Sales Data
Cleanses and validates sales data using Snowpark DataFrame operations.
"""

from snowflake.snowpark import Session
from snowflake.snowpark.functions import (
    col, when, upper, trim, to_date, current_timestamp,
    row_number, lit, coalesce
)
from snowflake.snowpark.window import Window
from snowflake.snowpark.types import DecimalType


def transform_sales_data(session: Session, execution_date: str) -> str:
    """
    Transform raw sales data into clean, validated format.

    Args:
        session: Snowpark session
        execution_date: Date to process (YYYY-MM-DD format)

    Returns:
        Status message with row count
    """

    try:
        # Read from raw table
        raw_df = (session.table("ANALYTICS.RAW.SALES")
                  .filter(col("execution_date") == execution_date))

        # Data quality checks and transformations
        clean_df = (raw_df
            # Remove duplicates based on sale_id
            .withColumn(
                "row_num",
                row_number().over(
                    Window.partition_by("sale_id").order_by(col("ingested_at").desc())
                )
            )
            .filter(col("row_num") == 1)
            .drop("row_num")

            # Standardize region names
            .withColumn(
                "region_clean",
                when(col("region") == "US-WEST", "USA-WEST")
                .when(col("region") == "US-EAST", "USA-EAST")
                .when(col("region") == "US-CENTRAL", "USA-CENTRAL")
                .otherwise(upper(trim(col("region"))))
            )

            # Convert sale_date to proper date type
            .withColumn("sale_date_parsed", to_date(col("sale_date")))

            # Calculate discount if quantity > 3
            .withColumn(
                "discount_rate",
                when(col("quantity") >= 5, lit(0.10))
                .when(col("quantity") >= 3, lit(0.05))
                .otherwise(lit(0.0))
            )

            .withColumn(
                "discount_amount",
                (col("total_amount") * col("discount_rate")).cast(DecimalType(10, 2))
            )

            .withColumn(
                "final_amount",
                (col("total_amount") - col("discount_amount")).cast(DecimalType(10, 2))
            )

            # Categorize payment methods
            .withColumn(
                "payment_category",
                when(col("payment_method").isin(["credit_card", "debit_card"]), "CARD")
                .when(col("payment_method").isin(["paypal", "apple_pay", "google_pay"]), "DIGITAL")
                .when(col("payment_method") == "cash", "CASH")
                .otherwise("OTHER")
            )

            # Add data quality flag
            .withColumn(
                "quality_flag",
                when(
                    (col("sale_id").isNull()) |
                    (col("customer_id").isNull()) |
                    (col("total_amount") <= 0) |
                    (col("quantity") <= 0),
                    "FAILED"
                )
                .otherwise("PASSED")
            )

            # Add transformation timestamp
            .withColumn("transformed_at", current_timestamp())
        )

        # Select final columns
        final_df = clean_df.select(
            "sale_id",
            col("sale_date_parsed").alias("sale_date"),
            "customer_id",
            "product_id",
            "quantity",
            "unit_price",
            "total_amount",
            "discount_rate",
            "discount_amount",
            "final_amount",
            col("region_clean").alias("region"),
            "store_id",
            "payment_method",
            "payment_category",
            "quality_flag",
            "execution_date",
            "transformed_at"
        )

        # Filter only quality-passed records
        passed_df = final_df.filter(col("quality_flag") == "PASSED")

        # Write to clean table
        passed_df.write.mode("overwrite").save_as_table(
            "ANALYTICS.CLEAN.SALES",
            table_type="transient"
        )

        row_count = passed_df.count()
        failed_count = final_df.filter(col("quality_flag") == "FAILED").count()

        return f"SUCCESS: Transformed {row_count} rows ({failed_count} failed quality checks) for {execution_date}"

    except Exception as e:
        return f"ERROR: {str(e)}"


def main(session: Session, execution_date: str) -> str:
    return transform_sales_data(session, execution_date)
