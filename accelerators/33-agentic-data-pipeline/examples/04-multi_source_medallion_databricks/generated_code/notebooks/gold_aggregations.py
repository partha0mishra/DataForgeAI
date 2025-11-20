# Databricks notebook source
"""
Gold Layer - Business Aggregations and Analytics
Creates materialized views and aggregated metrics for analytics
"""

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# COMMAND ----------
# Gold: User activity summary

user_activity = (
    spark.read.table("analytics.silver.user_events")
    .groupBy("user_id", "event_date")
    .agg(
        F.count("*").alias("total_events"),
        F.countDistinct("session_id").alias("session_count"),
        F.sum(F.when(F.col("event_type") == "page_view", 1).otherwise(0)).alias("page_views"),
        F.sum(F.when(F.col("event_type") == "add_to_cart", 1).otherwise(0)).alias("cart_additions"),
        F.countDistinct(F.when(F.col("event_type") == "page_view", F.col("page_url"))).alias("unique_pages_viewed"),
        F.min("event_timestamp").alias("first_event_time"),
        F.max("event_timestamp").alias("last_event_time")
    )
    .withColumn("session_duration_minutes",
        (F.unix_timestamp("last_event_time") - F.unix_timestamp("first_event_time")) / 60
    )
)

(user_activity.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable("analytics.gold.user_daily_activity")
)

# COMMAND ----------
# Gold: Transaction metrics

transaction_metrics = (
    spark.read.table("analytics.silver.transactions")
    .filter(F.col("event_type") == "purchase")
    .groupBy("event_date", "payment_method")
    .agg(
        F.count("transaction_id").alias("transaction_count"),
        F.sum("amount_usd").alias("total_revenue_usd"),
        F.avg("amount_usd").alias("avg_transaction_value_usd"),
        F.min("amount_usd").alias("min_transaction_usd"),
        F.max("amount_usd").alias("max_transaction_usd"),
        F.countDistinct("user_id").alias("unique_customers")
    )
)

(transaction_metrics.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable("analytics.gold.daily_transaction_metrics")
)

# COMMAND ----------
# Gold: Product performance

product_performance = (
    spark.read.table("analytics.silver.transactions")
    .filter(F.col("event_type") == "purchase")
    .select(
        "transaction_id",
        "event_date",
        "user_id",
        F.explode("items").alias("item")
    )
    .select(
        "event_date",
        F.col("item.product_id").alias("product_id"),
        F.col("item.quantity").alias("quantity"),
        F.col("item.price").alias("price")
    )
    .groupBy("event_date", "product_id")
    .agg(
        F.sum("quantity").alias("units_sold"),
        F.sum(F.col("quantity") * F.col("price")).alias("revenue"),
        F.count("*").alias("order_count")
    )
    .join(
        spark.read.table("analytics.silver.products").select("product_id", "product_name", "category"),
        "product_id",
        "left"
    )
)

(product_performance.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable("analytics.gold.product_daily_performance")
)

# COMMAND ----------
# Gold: User lifetime value

user_ltv = (
    spark.read.table("analytics.silver.transactions")
    .filter(F.col("event_type") == "purchase")
    .groupBy("user_id")
    .agg(
        F.count("transaction_id").alias("total_purchases"),
        F.sum("amount_usd").alias("lifetime_value_usd"),
        F.avg("amount_usd").alias("avg_order_value_usd"),
        F.min("event_timestamp").alias("first_purchase_date"),
        F.max("event_timestamp").alias("last_purchase_date")
    )
    .withColumn("customer_tenure_days",
        F.datediff(F.col("last_purchase_date"), F.col("first_purchase_date"))
    )
    .withColumn("avg_days_between_purchases",
        F.col("customer_tenure_days") / F.greatest(F.col("total_purchases") - 1, F.lit(1))
    )
    .join(
        spark.read.table("analytics.silver.users").select("user_id", "email", "country", "subscription_tier"),
        "user_id",
        "left"
    )
)

(user_ltv.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable("analytics.gold.user_lifetime_value")
)

# COMMAND ----------
# Gold: Funnel analysis

funnel = (
    spark.read.table("analytics.silver.user_events")
    .groupBy("user_id", "session_id", "event_date")
    .agg(
        F.max(F.when(F.col("event_type") == "page_view", 1).otherwise(0)).alias("viewed"),
        F.max(F.when(F.col("event_type") == "add_to_cart", 1).otherwise(0)).alias("added_to_cart")
    )
    .join(
        spark.read.table("analytics.silver.transactions")
        .filter(F.col("event_type") == "purchase")
        .select("user_id", F.to_date("event_timestamp").alias("event_date"), F.lit(1).alias("purchased"))
        .dropDuplicates(["user_id", "event_date"]),
        ["user_id", "event_date"],
        "left"
    )
    .fillna(0, ["purchased"])
    .groupBy("event_date")
    .agg(
        F.sum("viewed").alias("users_viewed"),
        F.sum("added_to_cart").alias("users_added_to_cart"),
        F.sum("purchased").alias("users_purchased")
    )
    .withColumn("cart_conversion_rate", F.col("users_added_to_cart") / F.col("users_viewed"))
    .withColumn("purchase_conversion_rate", F.col("users_purchased") / F.col("users_viewed"))
)

(funnel.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable("analytics.gold.daily_conversion_funnel")
)
