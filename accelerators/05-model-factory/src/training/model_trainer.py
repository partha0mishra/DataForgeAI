"""Model training with hyperparameter tuning."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import optuna
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score, train_test_split

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TrainingConfig:
    """Training configuration."""

    task_type: str  # classification, regression
    metric: str  # accuracy, f1, rmse, mae, roc_auc
    test_size: float = 0.2
    random_state: int = 42
    cv_folds: int = 5
    n_trials: int = 50  # For hyperparameter tuning
    timeout: Optional[int] = None  # Seconds


@dataclass
class TrainingResult:
    """Training result."""

    model: Any
    train_score: float
    test_score: float
    cv_scores: List[float]
    cv_mean: float
    cv_std: float
    best_params: Dict[str, Any]
    feature_importance: Optional[Dict[str, float]]
    training_time: float


class ModelTrainer:
    """
    Model trainer with hyperparameter optimization.

    Provides:
    - Automated train/test splitting
    - Cross-validation
    - Hyperparameter tuning with Optuna
    - Multiple evaluation metrics
    - Feature importance extraction

    Example:
        trainer = ModelTrainer(
            config=TrainingConfig(
                task_type="classification",
                metric="f1",
                cv_folds=5
            )
        )

        # Define parameter space
        param_space = {
            "n_estimators": ("int", 50, 300),
            "max_depth": ("int", 3, 10),
            "learning_rate": ("float", 0.01, 0.3)
        }

        # Train with tuning
        result = trainer.train_with_tuning(
            X_train, y_train,
            model_class=XGBClassifier,
            param_space=param_space
        )

        print(f"Best F1: {result.test_score:.3f}")
        print(f"Best params: {result.best_params}")
    """

    def __init__(self, config: TrainingConfig):
        """
        Initialize model trainer.

        Args:
            config: Training configuration
        """
        self.config = config
        self.logger = logger

        # Validate config
        self._validate_config()

        self.logger.info(
            "Model trainer initialized",
            task_type=config.task_type,
            metric=config.metric,
        )

    def _validate_config(self) -> None:
        """Validate configuration."""
        valid_tasks = ["classification", "regression"]
        if self.config.task_type not in valid_tasks:
            raise ValueError(f"task_type must be one of {valid_tasks}")

        classification_metrics = ["accuracy", "f1", "precision", "recall", "roc_auc"]
        regression_metrics = ["rmse", "mae", "mse", "r2"]

        if self.config.task_type == "classification":
            valid_metrics = classification_metrics
        else:
            valid_metrics = regression_metrics

        if self.config.metric not in valid_metrics:
            raise ValueError(f"For {self.config.task_type}, metric must be one of {valid_metrics}")

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model: Any,
        validation_split: bool = True,
    ) -> TrainingResult:
        """
        Train model with cross-validation.

        Args:
            X: Features
            y: Target
            model: Model instance
            validation_split: Whether to create validation split

        Returns:
            Training result
        """
        import time

        start_time = time.time()

        # Split data
        if validation_split:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=self.config.test_size,
                random_state=self.config.random_state,
            )
        else:
            X_train, X_test, y_train, y_test = X, None, y, None

        # Train model
        model.fit(X_train, y_train)

        # Evaluate on training set
        train_pred = model.predict(X_train)
        train_score = self._calculate_metric(y_train, train_pred, y_train)

        # Evaluate on test set
        if validation_split:
            test_pred = model.predict(X_test)
            test_score = self._calculate_metric(y_test, test_pred, y_test)
        else:
            test_score = train_score

        # Cross-validation
        cv_scores = cross_val_score(
            model, X_train, y_train,
            cv=self.config.cv_folds,
            scoring=self._get_sklearn_metric(),
        )

        # Feature importance
        feature_importance = self._extract_feature_importance(model, X)

        training_time = time.time() - start_time

        result = TrainingResult(
            model=model,
            train_score=train_score,
            test_score=test_score,
            cv_scores=cv_scores.tolist(),
            cv_mean=float(np.mean(cv_scores)),
            cv_std=float(np.std(cv_scores)),
            best_params={},
            feature_importance=feature_importance,
            training_time=training_time,
        )

        self.logger.info(
            "Model trained",
            train_score=train_score,
            test_score=test_score,
            cv_mean=result.cv_mean,
            time=training_time,
        )

        return result

    def train_with_tuning(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model_class: Any,
        param_space: Dict[str, Tuple],
        validation_split: bool = True,
    ) -> TrainingResult:
        """
        Train model with hyperparameter tuning.

        Args:
            X: Features
            y: Target
            model_class: Model class (not instance)
            param_space: Parameter space definition
                Format: {"param_name": ("type", min, max)} or {"param_name": ("categorical", [values])}
            validation_split: Whether to create validation split

        Returns:
            Training result with best parameters
        """
        import time

        start_time = time.time()

        # Split data
        if validation_split:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=self.config.test_size,
                random_state=self.config.random_state,
            )
        else:
            X_train, X_test, y_train, y_test = X, None, y, None

        # Define objective function for Optuna
        def objective(trial: optuna.Trial) -> float:
            # Suggest parameters
            params = {}
            for param_name, param_config in param_space.items():
                param_type = param_config[0]

                if param_type == "int":
                    params[param_name] = trial.suggest_int(param_name, param_config[1], param_config[2])
                elif param_type == "float":
                    params[param_name] = trial.suggest_float(param_name, param_config[1], param_config[2])
                elif param_type == "categorical":
                    params[param_name] = trial.suggest_categorical(param_name, param_config[1])
                elif param_type == "loguniform":
                    params[param_name] = trial.suggest_float(
                        param_name, param_config[1], param_config[2], log=True
                    )

            # Create model with suggested parameters
            model = model_class(**params)

            # Cross-validation score
            cv_scores = cross_val_score(
                model, X_train, y_train,
                cv=self.config.cv_folds,
                scoring=self._get_sklearn_metric(),
            )

            return float(np.mean(cv_scores))

        # Run optimization
        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=self.config.random_state),
        )

        study.optimize(
            objective,
            n_trials=self.config.n_trials,
            timeout=self.config.timeout,
            show_progress_bar=False,
        )

        # Get best parameters
        best_params = study.best_params

        self.logger.info(
            "Hyperparameter tuning complete",
            best_score=study.best_value,
            best_params=best_params,
            n_trials=len(study.trials),
        )

        # Train final model with best parameters
        best_model = model_class(**best_params)
        best_model.fit(X_train, y_train)

        # Evaluate
        train_pred = best_model.predict(X_train)
        train_score = self._calculate_metric(y_train, train_pred, y_train)

        if validation_split:
            test_pred = best_model.predict(X_test)
            test_score = self._calculate_metric(y_test, test_pred, y_test)
        else:
            test_score = train_score

        # Cross-validation on full training set
        cv_scores = cross_val_score(
            best_model, X_train, y_train,
            cv=self.config.cv_folds,
            scoring=self._get_sklearn_metric(),
        )

        # Feature importance
        feature_importance = self._extract_feature_importance(best_model, X)

        training_time = time.time() - start_time

        result = TrainingResult(
            model=best_model,
            train_score=train_score,
            test_score=test_score,
            cv_scores=cv_scores.tolist(),
            cv_mean=float(np.mean(cv_scores)),
            cv_std=float(np.std(cv_scores)),
            best_params=best_params,
            feature_importance=feature_importance,
            training_time=training_time,
        )

        self.logger.info(
            "Final model trained",
            train_score=train_score,
            test_score=test_score,
            cv_mean=result.cv_mean,
            time=training_time,
        )

        return result

    def _calculate_metric(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_train: np.ndarray,
    ) -> float:
        """Calculate specified metric."""
        metric = self.config.metric

        if metric == "accuracy":
            return accuracy_score(y_true, y_pred)
        elif metric == "f1":
            return f1_score(y_true, y_pred, average="weighted")
        elif metric == "precision":
            return precision_score(y_true, y_pred, average="weighted")
        elif metric == "recall":
            return recall_score(y_true, y_pred, average="weighted")
        elif metric == "rmse":
            return np.sqrt(mean_squared_error(y_true, y_pred))
        elif metric == "mae":
            return mean_absolute_error(y_true, y_pred)
        elif metric == "mse":
            return mean_squared_error(y_true, y_pred)
        else:
            raise ValueError(f"Unsupported metric: {metric}")

    def _get_sklearn_metric(self) -> str:
        """Get sklearn-compatible metric name."""
        metric_mapping = {
            "accuracy": "accuracy",
            "f1": "f1_weighted",
            "precision": "precision_weighted",
            "recall": "recall_weighted",
            "rmse": "neg_root_mean_squared_error",
            "mae": "neg_mean_absolute_error",
            "mse": "neg_mean_squared_error",
            "roc_auc": "roc_auc",
            "r2": "r2",
        }

        return metric_mapping.get(self.config.metric, self.config.metric)

    def _extract_feature_importance(
        self,
        model: Any,
        X: np.ndarray,
    ) -> Optional[Dict[str, float]]:
        """Extract feature importance from model."""
        try:
            # Try to get feature_importances_
            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_

                # Create feature names if not available
                feature_names = [f"feature_{i}" for i in range(len(importances))]

                # Sort by importance
                indices = np.argsort(importances)[::-1]

                return {
                    feature_names[i]: float(importances[i])
                    for i in indices[:20]  # Top 20 features
                }

            # Try to get coef_ (linear models)
            elif hasattr(model, "coef_"):
                coef = np.abs(model.coef_)
                if len(coef.shape) > 1:
                    coef = coef[0]

                feature_names = [f"feature_{i}" for i in range(len(coef))]
                indices = np.argsort(coef)[::-1]

                return {
                    feature_names[i]: float(coef[i])
                    for i in indices[:20]
                }

        except Exception as e:
            self.logger.debug("Could not extract feature importance", error=str(e))

        return None

    def evaluate_model(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Dict[str, float]:
        """
        Evaluate model with multiple metrics.

        Args:
            model: Trained model
            X: Features
            y: Target

        Returns:
            Dictionary of metrics
        """
        y_pred = model.predict(X)

        metrics = {}

        if self.config.task_type == "classification":
            metrics["accuracy"] = accuracy_score(y, y_pred)
            metrics["f1"] = f1_score(y, y_pred, average="weighted")
            metrics["precision"] = precision_score(y, y_pred, average="weighted")
            metrics["recall"] = recall_score(y, y_pred, average="weighted")

            # ROC AUC (if binary or probabilities available)
            try:
                if hasattr(model, "predict_proba"):
                    y_proba = model.predict_proba(X)
                    if y_proba.shape[1] == 2:
                        metrics["roc_auc"] = roc_auc_score(y, y_proba[:, 1])
                    else:
                        metrics["roc_auc"] = roc_auc_score(y, y_proba, multi_class="ovr")
            except Exception:
                pass

        else:  # regression
            metrics["mae"] = mean_absolute_error(y, y_pred)
            metrics["mse"] = mean_squared_error(y, y_pred)
            metrics["rmse"] = np.sqrt(metrics["mse"])

        return metrics
