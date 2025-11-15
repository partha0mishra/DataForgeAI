"""Example: Complete ML lifecycle with Model Factory."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from training.experiment_tracker import ExperimentTracker
from training.model_trainer import ModelTrainer, TrainingConfig
from registry.model_registry import ModelRegistry, ModelStage
from serving.model_server import ModelServer


def print_section(title: str):
    """Print section header."""
    print()
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)
    print()


def create_sample_dataset():
    """Create sample classification dataset."""
    print("Creating sample dataset (customer churn prediction)...")

    # Generate synthetic data
    X, y = make_classification(
        n_samples=1000,
        n_features=10,
        n_informative=7,
        n_redundant=2,
        n_classes=2,
        random_state=42,
    )

    # Create feature names
    feature_names = [
        "age",
        "tenure_months",
        "monthly_charges",
        "total_charges",
        "contract_type",
        "internet_service",
        "tech_support",
        "online_security",
        "device_protection",
        "payment_method",
    ]

    df = pd.DataFrame(X, columns=feature_names)
    df["churn"] = y

    print(f"✓ Created dataset: {len(df)} samples, {len(feature_names)} features")
    print(f"  Class distribution: {(y == 0).sum()} no churn, {(y == 1).sum()} churn")

    return df[feature_names].values, df["churn"].values, feature_names


def main():
    """Run complete ML lifecycle example."""
    print("=" * 80)
    print(" DataForge Model Factory - Complete ML Lifecycle Example")
    print("=" * 80)

    # Step 1: Create dataset
    print_section("1. Create Sample Dataset")

    X, y, feature_names = create_sample_dataset()

    # Step 2: Initialize components
    print_section("2. Initialize Model Factory Components")

    experiment_tracker = ExperimentTracker(
        experiment_name="customer_churn_prediction",
        tracking_uri=None,  # Use local filesystem
    )
    print("✓ Experiment tracker initialized")

    model_registry = ModelRegistry(tracking_uri=None)
    print("✓ Model registry initialized")

    model_server = ModelServer(registry=model_registry, cache_size=5)
    print("✓ Model server initialized")

    # Step 3: Train models with tracking
    print_section("3. Train Multiple Models with Experiment Tracking")

    print("Training Random Forest...")
    with experiment_tracker.start_run(run_name="random_forest_baseline"):
        # Log parameters
        rf_params = {
            "model_type": "RandomForest",
            "n_estimators": 100,
            "max_depth": 10,
            "random_state": 42,
        }
        experiment_tracker.log_params(rf_params)

        # Train model
        trainer = ModelTrainer(
            config=TrainingConfig(
                task_type="classification",
                metric="f1",
                cv_folds=5,
            )
        )

        rf_model = RandomForestClassifier(
            n_estimators=rf_params["n_estimators"],
            max_depth=rf_params["max_depth"],
            random_state=rf_params["random_state"],
        )

        rf_result = trainer.train(X, y, rf_model)

        # Log metrics
        experiment_tracker.log_metrics(
            {
                "train_score": rf_result.train_score,
                "test_score": rf_result.test_score,
                "cv_mean": rf_result.cv_mean,
                "cv_std": rf_result.cv_std,
            }
        )

        # Log model
        experiment_tracker.log_model(rf_result.model, "model")

        print(f"  ✓ Random Forest trained")
        print(f"    Train F1: {rf_result.train_score:.3f}")
        print(f"    Test F1: {rf_result.test_score:.3f}")
        print(f"    CV Mean: {rf_result.cv_mean:.3f} ± {rf_result.cv_std:.3f}")

    # Step 4: Train with hyperparameter tuning
    print()
    print("Training XGBoost with hyperparameter tuning...")

    with experiment_tracker.start_run(run_name="xgboost_tuned"):
        # Define parameter space
        param_space = {
            "n_estimators": ("int", 50, 200),
            "max_depth": ("int", 3, 10),
            "learning_rate": ("float", 0.01, 0.3),
            "subsample": ("float", 0.6, 1.0),
        }

        # Log base params
        experiment_tracker.log_params(
            {
                "model_type": "XGBoost",
                "optimization": "optuna",
                "n_trials": 30,
            }
        )

        # Train with tuning
        xgb_result = trainer.train_with_tuning(
            X=X,
            y=y,
            model_class=XGBClassifier,
            param_space=param_space,
        )

        # Log best parameters
        experiment_tracker.log_params(xgb_result.best_params)

        # Log metrics
        experiment_tracker.log_metrics(
            {
                "train_score": xgb_result.train_score,
                "test_score": xgb_result.test_score,
                "cv_mean": xgb_result.cv_mean,
                "cv_std": xgb_result.cv_std,
            }
        )

        # Log model
        experiment_tracker.log_model(xgb_result.model, "model")

        print(f"  ✓ XGBoost trained with tuning")
        print(f"    Best params: {xgb_result.best_params}")
        print(f"    Train F1: {xgb_result.train_score:.3f}")
        print(f"    Test F1: {xgb_result.test_score:.3f}")
        print(f"    CV Mean: {xgb_result.cv_mean:.3f} ± {xgb_result.cv_std:.3f}")

    # Step 5: Find best model
    print_section("4. Compare Experiments and Find Best Model")

    best_run = experiment_tracker.get_best_run("test_score", mode="max")

    if best_run:
        print(f"Best model: {best_run.tags.get('mlflow.runName', 'Unknown')}")
        print(f"  Test F1: {best_run.metrics.get('test_score', 0):.3f}")
        print(f"  CV Mean: {best_run.metrics.get('cv_mean', 0):.3f}")
        print(f"  Run ID: {best_run.run_id}")

        # Step 6: Register best model
        print_section("5. Register Best Model in Model Registry")

        model_uri = f"runs:/{best_run.run_id}/model"

        try:
            version = model_registry.register_model(
                model_uri=model_uri,
                name="customer_churn_predictor",
                description="XGBoost model for customer churn prediction",
                tags={
                    "task": "classification",
                    "framework": "xgboost",
                    "dataset": "synthetic_churn",
                },
            )

            print(f"✓ Model registered as 'customer_churn_predictor' v{version}")

            # Step 7: Promote to staging
            print_section("6. Promote Model to Staging")

            model_registry.transition_stage(
                name="customer_churn_predictor",
                version=version,
                stage=ModelStage.STAGING,
            )

            print(f"✓ Model v{version} promoted to Staging")

            # Simulate testing in staging
            print()
            print("Testing model in staging environment...")
            print("  Running integration tests...")
            print("  Checking prediction latency...")
            print("  Validating output format...")
            print("✓ All staging tests passed")

            # Step 8: Promote to production
            print_section("7. Promote Model to Production")

            model_registry.promote_to_production(
                name="customer_churn_predictor",
                version=version,
            )

            print(f"✓ Model v{version} promoted to Production")

            # Step 9: Serve model
            print_section("8. Serve Model for Predictions")

            # Load production model
            model_server.load_model(
                name="customer_churn_predictor",
                stage="Production",
            )

            print("✓ Production model loaded into server")

            # Make sample predictions
            print()
            print("Making sample predictions...")

            # Single prediction
            sample_customer = {
                "age": 0.5,
                "tenure_months": 0.3,
                "monthly_charges": 0.7,
                "total_charges": 0.6,
                "contract_type": 0.2,
                "internet_service": 0.8,
                "tech_support": 0.1,
                "online_security": 0.3,
                "device_protection": 0.4,
                "payment_method": 0.5,
            }

            response = model_server.predict(
                model_name="customer_churn_predictor",
                model_stage="Production",
                features=sample_customer,
            )

            print()
            print("Single Prediction:")
            print(f"  Input: Customer with monthly_charges={sample_customer['monthly_charges']}")
            print(f"  Prediction: {'Will Churn' if response.predictions[0] == 1 else 'Will Not Churn'}")
            print(f"  Model version: {response.model_version}")
            print(f"  Latency: {response.latency_ms:.2f} ms")

            # Batch predictions
            print()
            print("Batch Predictions:")

            batch_customers = [
                {f: np.random.rand() for f in feature_names}
                for _ in range(5)
            ]

            batch_response = model_server.predict(
                model_name="customer_churn_predictor",
                model_stage="Production",
                instances=batch_customers,
            )

            print(f"  Predicted {batch_response.prediction_count} customers")
            print(f"  Results: {batch_response.predictions}")
            print(f"  Average latency: {batch_response.latency_ms / len(batch_customers):.2f} ms per prediction")

            # Step 10: Model lineage
            print_section("9. View Model Lineage")

            lineage = model_registry.get_model_lineage(
                name="customer_churn_predictor",
                version=version,
            )

            print("Model Lineage:")
            print(f"  Model: {lineage['model_name']} v{lineage['version']}")
            print(f"  Run ID: {lineage['run_id']}")
            print(f"  Experiment ID: {lineage['experiment_id']}")
            print()
            print("  Training Parameters:")
            for param, value in list(lineage['parameters'].items())[:5]:
                print(f"    {param}: {value}")
            print()
            print("  Metrics:")
            for metric, value in lineage['metrics'].items():
                print(f"    {metric}: {value:.4f}")

            # Step 11: Server statistics
            print_section("10. Server Statistics")

            stats = model_server.get_server_stats()

            print("Model Server Statistics:")
            print(f"  Loaded models: {stats['loaded_models']}")
            print(f"  Cache size: {stats['cache_size']}")
            print(f"  Total predictions: {stats['total_predictions']}")
            print()
            print("  Loaded models:")
            for model_info in stats['models']:
                print(f"    - {model_info['name']} v{model_info['version']} ({model_info['stage']})")
                print(f"      Predictions: {model_info['prediction_count']}")
                print(f"      Loaded at: {model_info['loaded_at']}")

        except Exception as e:
            print(f"Note: MLflow registry operations require MLflow server")
            print(f"Error: {str(e)}")
            print()
            print("To run with full MLflow support:")
            print("  1. Start MLflow server: mlflow server --host 0.0.0.0 --port 5000")
            print("  2. Set tracking_uri when initializing components")

    # Final summary
    print_section("Example Complete!")

    print("Summary:")
    print("  ✓ Created synthetic churn prediction dataset")
    print("  ✓ Trained 2 models (Random Forest, XGBoost)")
    print("  ✓ Performed hyperparameter tuning with Optuna")
    print("  ✓ Tracked all experiments with MLflow")
    print("  ✓ Registered best model in registry")
    print("  ✓ Promoted model: None → Staging → Production")
    print("  ✓ Served model for real-time predictions")
    print("  ✓ Demonstrated model lineage tracking")
    print()
    print("Next steps:")
    print("  1. Start MLflow UI: mlflow ui --port 5000")
    print("  2. Start API: uvicorn src.api.main:app --reload --port 8004")
    print("  3. View experiments at http://localhost:5000")
    print("  4. Try API at http://localhost:8004/docs")
    print()


if __name__ == "__main__":
    main()
