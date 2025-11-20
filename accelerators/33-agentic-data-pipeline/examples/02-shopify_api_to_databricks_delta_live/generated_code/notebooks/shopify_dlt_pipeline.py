# Databricks notebook source
"""
Shopify to Databricks Delta Live Tables Pipeline
Implements medallion architecture (Bronze -> Silver -> Gold)
"""

import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import *
import requests
from datetime import datetime, timedelta

# COMMAND ----------
# Configuration

shopify_secret_scope = "shopify_api"
api_key = dbutils.secrets.get(scope=shopify_secret_scope, key="api_key")
api_password = dbutils.secrets.get(scope=shopify_secret_scope, key="api_password")
store_url = "your-store.myshopify.com"

# COMMAND ----------
# BRONZE LAYER - Raw ingestion from Shopify API

@dlt.table(
    name="orders_bronze",
    comment="Raw Shopify orders data",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.zOrderCols": "created_at"
    }
)
def ingest_shopify_orders():
    """Ingest raw orders from Shopify API."""

    def fetch_shopify_orders():
        """Fetch orders from Shopify REST API."""
        url = f"https://{store_url}/admin/api/2025-01/orders.json"
        headers = {
            "X-Shopify-Access-Token": api_password
        }
        params = {
            "status": "any",
            "limit": 250,
            "created_at_min": (datetime.now() - timedelta(days=1)).isoformat()
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()["orders"]

    # Convert to Spark DataFrame
    orders = fetch_shopify_orders()
    return spark.createDataFrame(orders)

# COMMAND ----------
# SILVER LAYER - Cleaned and validated data

@dlt.table(
    name="orders_silver",
    comment="Cleaned Shopify orders with quality checks",
    table_properties={
        "quality": "silver"
    }
)
@dlt.expect_or_drop("valid_order_id", "id IS NOT NULL")
@dlt.expect_or_drop("valid_price", "CAST(total_price AS DOUBLE) >= 0")
@dlt.expect("valid_email", "email IS NOT NULL AND email LIKE '%@%'")
def clean_shopify_orders():
    """Clean and validate Shopify orders."""

    return (
        dlt.read("orders_bronze")
        .withColumn("order_id", F.col("id").cast("long"))
        .withColumn("total_price_usd", F.col("total_price").cast("double"))
        .withColumn("subtotal_price_usd", F.col("subtotal_price").cast("double"))
        .withColumn("total_tax_usd", F.col("total_tax").cast("double"))
        .withColumn("created_timestamp", F.to_timestamp("created_at"))
        .withColumn("updated_timestamp", F.to_timestamp("updated_at"))
        .withColumn("customer_id", F.col("customer.id").cast("long"))
        .withColumn("customer_email", F.col("customer.email"))
        .withColumn("customer_first_name", F.col("customer.first_name"))
        .withColumn("customer_last_name", F.col("customer.last_name"))
        .withColumn("shipping_city", F.col("shipping_address.city"))
        .withColumn("shipping_province", F.col("shipping_address.province"))
        .withColumn("shipping_country", F.col("shipping_address.country"))
        .withColumn("ingested_at", F.current_timestamp())
        .select(
            "order_id",
            "email",
            "created_timestamp",
            "updated_timestamp",
            "total_price_usd",
            "subtotal_price_usd",
            "total_tax_usd",
            "currency",
            "financial_status",
            "fulfillment_status",
            "customer_id",
            "customer_email",
            "customer_first_name",
            "customer_last_name",
            "shipping_city",
            "shipping_province",
            "shipping_country",
            "ingested_at"
        )
    )

# COMMAND ----------
# SILVER LAYER - Line items

@dlt.table(
    name="order_line_items_silver",
    comment="Individual line items from orders"
)
def extract_line_items():
    """Extract and flatten line items from orders."""

    return (
        dlt.read("orders_bronze")
        .select(
            F.col("id").alias("order_id"),
            F.explode("line_items").alias("line_item")
        )
        .select(
            "order_id",
            F.col("line_item.id").alias("line_item_id"),
            F.col("line_item.product_id").alias("product_id"),
            F.col("line_item.variant_id").alias("variant_id"),
            F.col("line_item.title").alias("product_title"),
            F.col("line_item.quantity").cast("int").alias("quantity"),
            F.col("line_item.price").cast("double").alias("price_usd")
        )
    )

# COMMAND ----------
# GOLD LAYER - Aggregated metrics

@dlt.table(
    name="daily_sales_metrics_gold",
    comment="Daily aggregated sales metrics"
)
def aggregate_daily_sales():
    """Calculate daily sales metrics."""

    return (
        dlt.read("orders_silver")
        .filter("financial_status = 'paid'")
        .withColumn("order_date", F.to_date("created_timestamp"))
        .groupBy("order_date", "shipping_country", "shipping_province")
        .agg(
            F.count("order_id").alias("total_orders"),
            F.sum("total_price_usd").alias("total_revenue"),
            F.avg("total_price_usd").alias("avg_order_value"),
            F.countDistinct("customer_id").alias("unique_customers")
        )
        .withColumn("calculated_at", F.current_timestamp())
    )

# COMMAND ----------
# GOLD LAYER - Customer metrics

@dlt.table(
    name="customer_lifetime_value_gold",
    comment="Customer lifetime value and metrics"
)
def calculate_customer_ltv():
    """Calculate customer lifetime value."""

    return (
        dlt.read("orders_silver")
        .filter("financial_status = 'paid'")
        .groupBy("customer_id", "customer_email", "customer_first_name", "customer_last_name")
        .agg(
            F.count("order_id").alias("total_orders"),
            F.sum("total_price_usd").alias("lifetime_value"),
            F.avg("total_price_usd").alias("avg_order_value"),
            F.min("created_timestamp").alias("first_order_date"),
            F.max("created_timestamp").alias("last_order_date")
        )
        .withColumn(
            "customer_tenure_days",
            F.datediff(F.col("last_order_date"), F.col("first_order_date"))
        )
        .withColumn("calculated_at", F.current_timestamp())
    )
