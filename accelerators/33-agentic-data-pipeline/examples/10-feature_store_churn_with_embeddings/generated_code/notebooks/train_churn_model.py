# Databricks notebook source
"""
Train Churn Prediction Model using Feature Store
Uses LightGBM with text embeddings
"""

from databricks import feature_store
from databricks.feature_store import FeatureLookup
import mlflow
import mlflow.lightgbm
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support
import pandas as pd

# Initialize Feature Store
fs = feature_store.FeatureStoreClient()

# COMMAND ----------
# Load training labels
training_df = spark.read.table("ml_platform.raw.user_activity").select("user_id", "churned")

# COMMAND ----------
# Define feature lookups

feature_lookups = [
    FeatureLookup(
        table_name="ml_platform.churn_features.user_behavioral_features",
        lookup_key="user_id"
    ),
    FeatureLookup(
        table_name="ml_platform.churn_features.user_transaction_features",
        lookup_key="user_id"
    ),
    FeatureLookup(
        table_name="ml_platform.churn_features.user_interaction_embeddings",
        lookup_key="user_id"
    )
]

# Create training set
training_set = fs.create_training_set(
    df=training_df,
    feature_lookups=feature_lookups,
    label="churned",
    exclude_columns=["user_id"]
)

training_pd = training_set.load_df().toPandas()

# COMMAND ----------
# Prepare features

# Flatten text embeddings
import numpy as np

embedding_columns = []
if 'text_embedding' in training_pd.columns:
    embeddings_array = np.array(training_pd['text_embedding'].tolist())
    for i in range(embeddings_array.shape[1]):
        col_name = f'embedding_{i}'
        training_pd[col_name] = embeddings_array[:, i]
        embedding_columns.append(col_name)
    training_pd = training_pd.drop('text_embedding', axis=1)

# Define feature columns
feature_cols = [
    'total_logins_30d',
    'avg_session_duration',
    'support_tickets_count',
    'transaction_count_30d',
    'avg_transaction_amount',
    'total_spend_30d'
] + embedding_columns

X = training_pd[feature_cols]
y = training_pd['churned']

# COMMAND ----------
# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# COMMAND ----------
# Train model with MLflow

mlflow.set_experiment("/ml/churn_prediction")

with mlflow.start_run(run_name="churn_lgbm_with_embeddings") as run:

    # Log parameters
    params = {
        'n_estimators': 100,
        'max_depth': 6,
        'learning_rate': 0.1,
        'num_leaves': 31,
        'feature_fraction': 0.8
    }
    mlflow.log_params(params)

    # Train model
    model = LGBMClassifier(**params, random_state=42)
    model.fit(X_train, y_train)

    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Metrics
    auc = roc_auc_score(y_test, y_pred_proba)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='binary'
    )

    mlflow.log_metrics({
        'auc': auc,
        'precision': precision,
        'recall': recall,
        'f1_score': f1
    })

    # Log model with feature store integration
    fs.log_model(
        model=model,
        artifact_path="model",
        flavor=mlflow.lightgbm,
        training_set=training_set,
        registered_model_name="churn_model"
    )

    print(f"✓ Model trained - AUC: {auc:.3f}, F1: {f1:.3f}")
