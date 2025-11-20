# Databricks notebook source
"""
Create Feature Store Tables for Churn Prediction
Implements feature engineering with text embeddings
"""

from databricks import feature_store
from databricks.feature_store import feature_table
from pyspark.sql import functions as F
from pyspark.sql.types import *
import mlflow

# Initialize Feature Store
fs = feature_store.FeatureStoreClient()

# COMMAND ----------
# Create behavioral features table

def compute_behavioral_features(df):
    """Compute user behavioral features."""
    return df.select(
        "user_id",
        "event_timestamp",
        "total_logins_30d",
        "avg_session_duration",
        "support_tickets_count"
    )

behavioral_features = compute_behavioral_features(
    spark.read.table("ml_platform.raw.user_activity")
)

fs.create_table(
    name="ml_platform.churn_features.user_behavioral_features",
    primary_keys=["user_id"],
    timestamp_keys=["event_timestamp"],
    df=behavioral_features,
    description="User engagement and support features"
)

# COMMAND ----------
# Create transaction features table

def compute_transaction_features(df):
    """Compute transaction-based features."""
    return df.select(
        "user_id",
        F.col("event_timestamp").alias("feature_timestamp"),
        "transaction_count_30d",
        "avg_transaction_amount",
        (F.col("transaction_count_30d") * F.col("avg_transaction_amount")).alias("total_spend_30d")
    )

transaction_features = compute_transaction_features(
    spark.read.table("ml_platform.raw.user_activity")
)

fs.create_table(
    name="ml_platform.churn_features.user_transaction_features",
    primary_keys=["user_id"],
    timestamp_keys=["feature_timestamp"],
    df=transaction_features,
    description="User transaction and spend features"
)

# COMMAND ----------
# Generate text embeddings

from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def generate_embeddings(text_df):
    """Generate embeddings from user text data."""

    # Combine review and ticket text
    text_df['combined_text'] = text_df['user_reviews'] + ' ' + text_df['support_tickets']

    # Generate embeddings
    embeddings = model.encode(text_df['combined_text'].tolist())

    # Convert to DataFrame
    embedding_df = pd.DataFrame({
        'user_id': text_df['user_id'],
        'text_embedding': list(embeddings),
        'embedding_timestamp': pd.Timestamp.now()
    })

    return embedding_df

# Load text data
text_data = spark.read.json("ml_platform.raw.user_text_data").toPandas()

# Generate embeddings
embedding_features = generate_embeddings(text_data)

# Convert to Spark DataFrame
embedding_spark_df = spark.createDataFrame(embedding_features)

fs.create_table(
    name="ml_platform.churn_features.user_interaction_embeddings",
    primary_keys=["user_id"],
    timestamp_keys=["embedding_timestamp"],
    df=embedding_spark_df,
    description="Text embeddings from reviews and support tickets"
)

# COMMAND ----------
print("✓ Feature tables created successfully")
