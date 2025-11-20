"""
Snowpark Stored Procedure: Aggregate Sales Metrics
Calculates daily sales metrics using Snowpark aggregations.
"""

from snowflake.snowpark import Session
from snowflake.snowpark.functions import (
    col, sum as sum_, avg, count, countDistinct, min as min_, max as max_,
    current_timestamp, lit
)
from snowflake.snowpark.types import DecimalType


def aggregate_metrics(session: Session, execution_date: str) -> str:
    """
    Aggregate daily sales metrics from clean data.

    Args:
        session: Snowpark session
        execution_date: Date to process (YYYY-MM-DD format)

    Returns:
        Status message with metrics
    """

    try:
        # Read clean sales data
        sales_df = (session.table("ANALYTICS.CLEAN.SALES")
                    .filter(col("execution_date") == execution_date))

        # Overall daily metrics
        daily_metrics = sales_df.agg(
            count("sale_id").alias("total_transactions"),
            sum_("final_amount").cast(DecimalType(18, 2)).alias("total_revenue"),
            avg("final_amount").cast(DecimalType(10, 2)).alias("avg_transaction_value"),
            min_("final_amount").alias("min_transaction_value"),
            max_("final_amount").alias("max_transaction_value"),
            countDistinct("customer_id").alias("unique_customers"),
            countDistinct("product_id").alias("unique_products"),
            sum_("quantity").alias("total_units_sold"),
            sum_("discount_amount").cast(DecimalType(18, 2)).alias("total_discounts")
        ).withColumn("metric_date", lit(execution_date)) \
         .withColumn("calculated_at", current_timestamp())

        # Metrics by region
        region_metrics = (sales_df
            .groupBy("region")
            .agg(
                count("sale_id").alias("transactions"),
                sum_("final_amount").cast(DecimalType(18, 2)).alias("revenue"),
                avg("final_amount").cast(DecimalType(10, 2)).alias("avg_value"),
                countDistinct("customer_id").alias("unique_customers")
            )
            .withColumn("metric_date", lit(execution_date))
            .withColumn("metric_type", lit("REGION"))
            .withColumn("calculated_at", current_timestamp())
        )

        # Metrics by payment category
        payment_metrics = (sales_df
            .groupBy("payment_category")
            .agg(
                count("sale_id").alias("transactions"),
                sum_("final_amount").cast(DecimalType(18, 2)).alias("revenue"),
                avg("final_amount").cast(DecimalType(10, 2)).alias("avg_value")
            )
            .withColumn("metric_date", lit(execution_date))
            .withColumn("metric_type", lit("PAYMENT"))
            .withColumn("calculated_at", current_timestamp())
        )

        # Metrics by product
        product_metrics = (sales_df
            .groupBy("product_id")
            .agg(
                count("sale_id").alias("transactions"),
                sum_("quantity").alias("units_sold"),
                sum_("final_amount").cast(DecimalType(18, 2)).alias("revenue"),
                avg("unit_price").cast(DecimalType(10, 2)).alias("avg_price")
            )
            .withColumn("metric_date", lit(execution_date))
            .withColumn("metric_type", lit("PRODUCT"))
            .withColumn("calculated_at", current_timestamp())
        )

        # Store metrics
        store_metrics = (sales_df
            .groupBy("store_id", "region")
            .agg(
                count("sale_id").alias("transactions"),
                sum_("final_amount").cast(DecimalType(18, 2)).alias("revenue"),
                countDistinct("customer_id").alias("unique_customers")
            )
            .withColumn("metric_date", lit(execution_date))
            .withColumn("metric_type", lit("STORE"))
            .withColumn("calculated_at", current_timestamp())
        )

        # Write metrics to tables
        daily_metrics.write.mode("append").save_as_table("ANALYTICS.METRICS.DAILY_OVERALL")

        region_metrics.write.mode("append").save_as_table("ANALYTICS.METRICS.DAILY_BY_REGION")

        payment_metrics.write.mode("append").save_as_table("ANALYTICS.METRICS.DAILY_BY_PAYMENT")

        product_metrics.write.mode("append").save_as_table("ANALYTICS.METRICS.DAILY_BY_PRODUCT")

        store_metrics.write.mode("append").save_as_table("ANALYTICS.METRICS.DAILY_BY_STORE")

        # Get summary stats
        total_revenue = daily_metrics.select("total_revenue").collect()[0][0]
        total_transactions = daily_metrics.select("total_transactions").collect()[0][0]

        return f"SUCCESS: Calculated metrics for {execution_date} - {total_transactions} transactions, ${total_revenue:.2f} revenue"

    except Exception as e:
        return f"ERROR: {str(e)}"


def main(session: Session, execution_date: str) -> str:
    return aggregate_metrics(session, execution_date)
