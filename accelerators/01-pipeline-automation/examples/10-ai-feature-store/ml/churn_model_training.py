"""
Customer Churn Prediction Model Training

This script trains a machine learning model to predict customer churn using
features from the Feast feature store with point-in-time correctness.

Key Features:
- Retrieves historical features from Feast offline store
- Ensures point-in-time correctness for training data
- Trains XGBoost classifier with hyperparameter tuning
- Logs experiments to MLflow
- Performs feature importance analysis
- Evaluates model with comprehensive metrics
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix,
    precision_recall_curve, roc_curve
)
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from feast import FeatureStore
import mlflow
import mlflow.sklearn
import mlflow.xgboost
from mlflow.models.signature import infer_signature
import matplotlib.pyplot as plt
import seaborn as sns


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChurnModelTrainer:
    """
    Train customer churn prediction model using Feast features.
    """

    def __init__(
        self,
        feast_repo_path: str,
        mlflow_tracking_uri: str = 'http://localhost:5000',
        experiment_name: str = 'customer_churn_prediction',
    ):
        """
        Initialize model trainer.

        Args:
            feast_repo_path: Path to Feast feature repository
            mlflow_tracking_uri: MLflow tracking server URI
            experiment_name: MLflow experiment name
        """
        self.feast_repo_path = feast_repo_path
        self.store = FeatureStore(repo_path=feast_repo_path)

        # MLflow configuration
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        mlflow.set_experiment(experiment_name)

        self.model = None
        self.scaler = None
        self.feature_names = None

    def get_training_data(
        self,
        entity_df: pd.DataFrame,
        features: List[str],
    ) -> pd.DataFrame:
        """
        Retrieve historical features from Feast with point-in-time correctness.

        Args:
            entity_df: DataFrame with entity_id and event_timestamp columns
            features: List of feature references to retrieve

        Returns:
            DataFrame with features and labels
        """
        logger.info(f"Retrieving {len(features)} features from Feast offline store")

        # Get historical features with point-in-time correctness
        training_df = self.store.get_historical_features(
            entity_df=entity_df,
            features=features,
        ).to_df()

        logger.info(f"Retrieved {len(training_df)} training samples with {len(training_df.columns)} features")

        return training_df

    def prepare_entity_dataframe(
        self,
        lookback_days: int = 90,
        label_window_days: int = 30,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare entity DataFrame with labels for training.

        The entity DataFrame defines:
        - Which customers to get features for
        - At what point in time (for historical feature retrieval)
        - What the label (churned or not) is for each customer

        Args:
            lookback_days: Days of history to use for features
            label_window_days: Days in future to determine churn label

        Returns:
            Tuple of (entity_df, labels)
        """
        logger.info("Preparing entity DataFrame with churn labels")

        # In production, this would query your data warehouse
        # For this example, we'll create a synthetic dataset

        # Simulate entity DataFrame
        # In reality, you would query:
        # SELECT customer_id, feature_timestamp, churned
        # FROM analytics.customer_churn_labels
        # WHERE feature_timestamp BETWEEN 'start_date' AND 'end_date'

        entity_df = pd.DataFrame({
            'customer_id': range(1, 10001),  # 10,000 customers
            'event_timestamp': [
                datetime.now() - timedelta(days=lookback_days + np.random.randint(0, 30))
                for _ in range(10000)
            ],
        })

        # Simulate churn labels (1 = churned, 0 = retained)
        # In production, this comes from actual customer behavior
        labels = pd.Series(np.random.binomial(1, 0.15, 10000), name='churned')

        logger.info(f"Entity DataFrame shape: {entity_df.shape}")
        logger.info(f"Churn rate: {labels.mean():.2%}")

        return entity_df, labels

    def prepare_features(
        self,
        df: pd.DataFrame,
        labels: pd.Series,
    ) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """
        Prepare features for model training.

        Args:
            df: DataFrame with raw features
            labels: Target labels

        Returns:
            Tuple of (X, y, feature_names)
        """
        logger.info("Preparing features for training")

        # Drop non-feature columns
        exclude_cols = ['customer_id', 'event_timestamp', 'churned']
        feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[feature_cols].copy()

        # Handle categorical variables
        categorical_cols = X.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            X[col] = X[col].astype('category').cat.codes

        # Handle missing values
        X = X.fillna(X.median())

        # Align labels with features
        y = labels.loc[X.index]

        logger.info(f"Feature matrix shape: {X.shape}")
        logger.info(f"Feature names: {list(X.columns)[:10]}...")

        return X, y, list(X.columns)

    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        hyperparameters: Dict[str, Any] = None,
    ) -> xgb.XGBClassifier:
        """
        Train XGBoost classifier.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            hyperparameters: Model hyperparameters

        Returns:
            Trained XGBoost model
        """
        logger.info("Training XGBoost model")

        # Default hyperparameters
        if hyperparameters is None:
            hyperparameters = {
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'objective': 'binary:logistic',
                'eval_metric': 'logloss',
                'early_stopping_rounds': 10,
                'random_state': 42,
            }

        # Initialize model
        model = xgb.XGBClassifier(**hyperparameters)

        # Train with validation set for early stopping
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        logger.info(f"Model trained with {model.n_estimators} boosting rounds")

        return model

    def evaluate_model(
        self,
        model: xgb.XGBClassifier,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> Dict[str, Any]:
        """
        Evaluate model performance.

        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels

        Returns:
            Dictionary of evaluation metrics
        """
        logger.info("Evaluating model performance")

        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        # Compute metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1_score': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
        }

        # Log metrics
        for metric_name, metric_value in metrics.items():
            logger.info(f"{metric_name}: {metric_value:.4f}")

        # Classification report
        logger.info("\nClassification Report:")
        logger.info(f"\n{classification_report(y_test, y_pred)}")

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        logger.info(f"\nConfusion Matrix:\n{cm}")

        return metrics

    def analyze_feature_importance(
        self,
        model: xgb.XGBClassifier,
        feature_names: List[str],
        top_n: int = 20,
    ) -> pd.DataFrame:
        """
        Analyze and visualize feature importance.

        Args:
            model: Trained model
            feature_names: List of feature names
            top_n: Number of top features to display

        Returns:
            DataFrame of feature importances
        """
        logger.info("Analyzing feature importance")

        # Get feature importance
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        # Log top features
        logger.info(f"\nTop {top_n} Most Important Features:")
        for i, row in importance_df.head(top_n).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        return importance_df

    def plot_feature_importance(
        self,
        importance_df: pd.DataFrame,
        top_n: int = 20,
        output_path: str = 'feature_importance.png',
    ) -> None:
        """
        Create feature importance visualization.

        Args:
            importance_df: DataFrame with feature importances
            top_n: Number of top features to plot
            output_path: Path to save plot
        """
        plt.figure(figsize=(10, 8))
        top_features = importance_df.head(top_n)

        sns.barplot(
            data=top_features,
            y='feature',
            x='importance',
            palette='viridis'
        )

        plt.title(f'Top {top_n} Feature Importances for Churn Prediction')
        plt.xlabel('Importance')
        plt.ylabel('Feature')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Feature importance plot saved to {output_path}")

    def run_training_pipeline(
        self,
        test_size: float = 0.2,
        val_size: float = 0.1,
    ) -> None:
        """
        Execute the complete model training pipeline.

        Args:
            test_size: Proportion of data for test set
            val_size: Proportion of train data for validation
        """
        with mlflow.start_run() as run:
            logger.info(f"Starting MLflow run: {run.info.run_id}")

            # Log parameters
            mlflow.log_param("test_size", test_size)
            mlflow.log_param("val_size", val_size)

            # Step 1: Prepare entity DataFrame and labels
            entity_df, labels = self.prepare_entity_dataframe()

            # Step 2: Get historical features from Feast
            features_to_retrieve = [
                'billing_features:spend_7d',
                'billing_features:spend_30d',
                'billing_features:spend_90d',
                'billing_features:invoice_count_30d',
                'billing_features:spend_trend_30d',
                'usage_features:session_count_7d',
                'usage_features:session_count_30d',
                'usage_features:active_days_30d',
                'usage_features:avg_engagement_score_7d',
                'support_features:ticket_count_30d',
                'support_features:avg_satisfaction_score_90d',
                'support_features:open_ticket_count',
                'customer_profile:customer_tier',
                'customer_profile:account_age_days',
            ]

            training_df = self.get_training_data(entity_df, features_to_retrieve)

            # Step 3: Prepare features
            X, y, feature_names = self.prepare_features(training_df, labels)
            self.feature_names = feature_names

            # Step 4: Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )

            X_train, X_val, y_train, y_val = train_test_split(
                X_train, y_train, test_size=val_size, random_state=42, stratify=y_train
            )

            logger.info(f"Train size: {len(X_train)}, Val size: {len(X_val)}, Test size: {len(X_test)}")

            # Step 5: Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)
            X_test_scaled = self.scaler.transform(X_test)

            # Convert back to DataFrames
            X_train_scaled = pd.DataFrame(X_train_scaled, columns=feature_names, index=X_train.index)
            X_val_scaled = pd.DataFrame(X_val_scaled, columns=feature_names, index=X_val.index)
            X_test_scaled = pd.DataFrame(X_test_scaled, columns=feature_names, index=X_test.index)

            # Step 6: Train model
            self.model = self.train_model(X_train_scaled, y_train, X_val_scaled, y_val)

            # Step 7: Evaluate model
            metrics = self.evaluate_model(self.model, X_test_scaled, y_test)

            # Log metrics to MLflow
            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)

            # Step 8: Feature importance analysis
            importance_df = self.analyze_feature_importance(self.model, feature_names)
            self.plot_feature_importance(importance_df)
            mlflow.log_artifact('feature_importance.png')

            # Step 9: Log model to MLflow
            signature = infer_signature(X_train_scaled, y_train)

            mlflow.xgboost.log_model(
                self.model,
                artifact_path="model",
                signature=signature,
                registered_model_name="customer_churn_xgboost",
            )

            # Log scaler
            mlflow.sklearn.log_model(
                self.scaler,
                artifact_path="scaler",
            )

            logger.info(f"Model training complete. MLflow run ID: {run.info.run_id}")
            logger.info(f"Model URI: runs:/{run.info.run_id}/model")

            return run.info.run_id


def main():
    """Main entry point for model training."""
    # Configuration
    feast_repo_path = os.getenv('FEAST_REPO_PATH', './feature_store/feast_repo')
    mlflow_tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')

    # Initialize trainer
    trainer = ChurnModelTrainer(
        feast_repo_path=feast_repo_path,
        mlflow_tracking_uri=mlflow_tracking_uri,
    )

    # Run training pipeline
    run_id = trainer.run_training_pipeline()

    logger.info("=" * 80)
    logger.info("Model Training Summary")
    logger.info("=" * 80)
    logger.info(f"MLflow Run ID: {run_id}")
    logger.info(f"Model registered as: customer_churn_xgboost")
    logger.info(f"View results at: {mlflow_tracking_uri}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
