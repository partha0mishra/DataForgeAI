# Databricks notebook source
"""
Batch Inference using Feature Store and MLflow Model
Predicts churn for all active users
"""

from databricks import feature_store
import mlflow

# Initialize
fs = feature_store.FeatureStoreClient()

# COMMAND ----------
# Load registered model
model_uri = "models:/churn_model/Production"
model = mlflow.pyfunc.load_model(model_uri)

# COMMAND ----------
# Get users to score
users_df = spark.sql("""
    SELECT DISTINCT user_id
    FROM ml_platform.raw.user_activity
    WHERE churned IS NULL OR churned = 0
""")

# COMMAND ----------
# Score using feature store
predictions = fs.score_batch(
    model_uri=model_uri,
    df=users_df
)

# COMMAND ----------
# Save predictions
(predictions
    .select("user_id", "prediction")
    .write
    .mode("overwrite")
    .saveAsTable("ml_platform.predictions.churn_scores")
)

print(f"✓ Scored {predictions.count()} users")
