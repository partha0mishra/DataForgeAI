"""ML experiment tracking with MLflow."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import mlflow
from mlflow.tracking import MlflowClient

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExperimentRun:
    """Experiment run information."""

    run_id: str
    experiment_id: str
    experiment_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    metrics: Dict[str, float]
    parameters: Dict[str, Any]
    tags: Dict[str, str]
    artifacts: List[str]


class ExperimentTracker:
    """
    ML experiment tracker using MLflow.

    Provides:
    - Experiment organization
    - Metrics and parameter logging
    - Artifact storage
    - Run comparison

    Example:
        tracker = ExperimentTracker(
            experiment_name="customer_churn",
            tracking_uri="http://mlflow:5000"
        )

        # Start run
        with tracker.start_run(run_name="xgboost_v1"):
            # Log parameters
            tracker.log_params({
                "n_estimators": 100,
                "max_depth": 5
            })

            # Train model
            model.fit(X_train, y_train)

            # Log metrics
            tracker.log_metrics({
                "accuracy": 0.92,
                "f1_score": 0.89
            })

            # Log model
            tracker.log_model(model, "model")
    """

    def __init__(
        self,
        experiment_name: str,
        tracking_uri: Optional[str] = None,
        artifact_location: Optional[str] = None,
    ):
        """
        Initialize experiment tracker.

        Args:
            experiment_name: Name of the experiment
            tracking_uri: MLflow tracking server URI
            artifact_location: S3/Azure blob location for artifacts
        """
        self.experiment_name = experiment_name
        self.logger = logger

        # Set tracking URI
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)

        # Create or get experiment
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                self.experiment_id = mlflow.create_experiment(
                    experiment_name,
                    artifact_location=artifact_location,
                )
            else:
                self.experiment_id = experiment.experiment_id
        except Exception as e:
            self.logger.warning(f"Could not create MLflow experiment: {e}")
            self.experiment_id = "0"  # Default experiment

        # Set active experiment
        mlflow.set_experiment(experiment_name)

        # MLflow client
        self.client = MlflowClient()

        self.logger.info(
            "Experiment tracker initialized",
            experiment_name=experiment_name,
            experiment_id=self.experiment_id,
        )

    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        """
        Start a new MLflow run.

        Args:
            run_name: Name of the run
            tags: Tags for the run

        Returns:
            MLflow run context manager
        """
        tags = tags or {}

        # Add system tags
        tags.update(
            {
                "experiment_name": self.experiment_name,
                "start_time": datetime.utcnow().isoformat(),
            }
        )

        return mlflow.start_run(run_name=run_name, tags=tags)

    def log_params(self, params: Dict[str, Any]) -> None:
        """
        Log parameters.

        Args:
            params: Parameters to log
        """
        for key, value in params.items():
            mlflow.log_param(key, value)

        self.logger.debug("Parameters logged", count=len(params))

    def log_metrics(
        self,
        metrics: Dict[str, float],
        step: Optional[int] = None,
    ) -> None:
        """
        Log metrics.

        Args:
            metrics: Metrics to log
            step: Optional step number (for time series metrics)
        """
        for key, value in metrics.items():
            mlflow.log_metric(key, value, step=step)

        self.logger.debug("Metrics logged", count=len(metrics))

    def log_metric_history(
        self,
        metric_name: str,
        values: List[float],
    ) -> None:
        """
        Log metric history (e.g., training loss per epoch).

        Args:
            metric_name: Name of the metric
            values: List of metric values
        """
        for step, value in enumerate(values):
            mlflow.log_metric(metric_name, value, step=step)

        self.logger.debug(
            "Metric history logged",
            metric=metric_name,
            steps=len(values),
        )

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None) -> None:
        """
        Log artifact file.

        Args:
            local_path: Path to local file
            artifact_path: Path within artifacts directory
        """
        mlflow.log_artifact(local_path, artifact_path)

        self.logger.debug("Artifact logged", path=local_path)

    def log_model(
        self,
        model: Any,
        artifact_path: str,
        registered_model_name: Optional[str] = None,
    ) -> None:
        """
        Log ML model.

        Args:
            model: Model object (sklearn, xgboost, etc.)
            artifact_path: Path to save model
            registered_model_name: Name for model registry
        """
        # Detect model type and log accordingly
        model_type = type(model).__module__

        if "sklearn" in model_type:
            mlflow.sklearn.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
            )
        elif "xgboost" in model_type:
            mlflow.xgboost.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
            )
        elif "lightgbm" in model_type:
            mlflow.lightgbm.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
            )
        else:
            # Use generic Python function logging
            mlflow.pyfunc.log_model(
                artifact_path,
                python_model=model,
                registered_model_name=registered_model_name,
            )

        self.logger.info(
            "Model logged",
            model_type=model_type,
            artifact_path=artifact_path,
        )

    def get_run(self, run_id: str) -> ExperimentRun:
        """
        Get run information.

        Args:
            run_id: Run identifier

        Returns:
            Experiment run information
        """
        run = self.client.get_run(run_id)

        return ExperimentRun(
            run_id=run.info.run_id,
            experiment_id=run.info.experiment_id,
            experiment_name=self.experiment_name,
            status=run.info.status,
            start_time=datetime.fromtimestamp(run.info.start_time / 1000),
            end_time=(
                datetime.fromtimestamp(run.info.end_time / 1000)
                if run.info.end_time
                else None
            ),
            metrics=run.data.metrics,
            parameters=run.data.params,
            tags=run.data.tags,
            artifacts=[],  # Would need to list artifacts separately
        )

    def search_runs(
        self,
        filter_string: Optional[str] = None,
        max_results: int = 100,
    ) -> List[ExperimentRun]:
        """
        Search runs in experiment.

        Args:
            filter_string: MLflow filter string (e.g., "metrics.accuracy > 0.9")
            max_results: Maximum results to return

        Returns:
            List of matching runs
        """
        runs = self.client.search_runs(
            experiment_ids=[self.experiment_id],
            filter_string=filter_string,
            max_results=max_results,
            order_by=["metrics.accuracy DESC"],
        )

        return [
            ExperimentRun(
                run_id=run.info.run_id,
                experiment_id=run.info.experiment_id,
                experiment_name=self.experiment_name,
                status=run.info.status,
                start_time=datetime.fromtimestamp(run.info.start_time / 1000),
                end_time=(
                    datetime.fromtimestamp(run.info.end_time / 1000)
                    if run.info.end_time
                    else None
                ),
                metrics=run.data.metrics,
                parameters=run.data.params,
                tags=run.data.tags,
                artifacts=[],
            )
            for run in runs
        ]

    def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple runs.

        Args:
            run_ids: List of run IDs to compare

        Returns:
            Comparison results
        """
        runs = [self.get_run(run_id) for run_id in run_ids]

        # Collect all metrics
        all_metrics = set()
        for run in runs:
            all_metrics.update(run.metrics.keys())

        # Build comparison table
        comparison = {
            "runs": [
                {
                    "run_id": run.run_id,
                    "status": run.status,
                    "parameters": run.parameters,
                    "metrics": run.metrics,
                }
                for run in runs
            ],
            "metric_names": list(all_metrics),
        }

        return comparison

    def get_best_run(self, metric_name: str, mode: str = "max") -> Optional[ExperimentRun]:
        """
        Get best run by metric.

        Args:
            metric_name: Metric to optimize
            mode: "max" or "min"

        Returns:
            Best run or None
        """
        filter_string = f"metrics.{metric_name} != 0"
        runs = self.search_runs(filter_string=filter_string, max_results=1000)

        if not runs:
            return None

        if mode == "max":
            best_run = max(runs, key=lambda r: r.metrics.get(metric_name, float("-inf")))
        else:
            best_run = min(runs, key=lambda r: r.metrics.get(metric_name, float("inf")))

        return best_run

    def delete_run(self, run_id: str) -> None:
        """Delete run."""
        self.client.delete_run(run_id)
        self.logger.info("Run deleted", run_id=run_id)
