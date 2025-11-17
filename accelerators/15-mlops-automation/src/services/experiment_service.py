"""Experiment Service for ML experiment management and MLflow integration."""
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import logging
from sqlalchemy.orm import Session

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.exceptions import MlflowException
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logging.warning("MLflow not available. Install with: pip install mlflow")

from src.models.experiment import Experiment
from src.repositories.experiment_repository import ExperimentRepository
from src.repositories.model_repository import ModelRepository
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ExperimentService:
    """Service for managing ML experiments and MLflow integration."""

    def __init__(self, db: Session):
        """Initialize experiment service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.experiment_repo = ExperimentRepository(db)
        self.model_repo = ModelRepository(db)

        # Initialize MLflow client
        if MLFLOW_AVAILABLE:
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            self.mlflow_client = MlflowClient()
        else:
            self.mlflow_client = None

    def create_experiment(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        artifact_location: Optional[str] = None,
        created_by: Optional[str] = None,
        sync_with_mlflow: bool = True
    ) -> Experiment:
        """Create a new experiment.

        Args:
            name: Experiment name
            description: Experiment description
            tags: Experiment tags
            artifact_location: Artifact storage location
            created_by: Creator identifier
            sync_with_mlflow: Whether to create in MLflow

        Returns:
            Created Experiment instance

        Raises:
            ValueError: If experiment already exists
        """
        # Check if experiment already exists
        existing = self.experiment_repo.get_by_name(name)
        if existing:
            raise ValueError(f"Experiment {name} already exists")

        mlflow_experiment_id = None
        mlflow_artifact_location = artifact_location

        # Create in MLflow if enabled
        if sync_with_mlflow and MLFLOW_AVAILABLE and self.mlflow_client:
            try:
                mlflow_experiment_id = mlflow.create_experiment(
                    name=name,
                    artifact_location=artifact_location,
                    tags=tags or {}
                )
                logger.info(f"Created MLflow experiment: {mlflow_experiment_id}")

                # Get artifact location from MLflow
                mlflow_exp = self.mlflow_client.get_experiment(mlflow_experiment_id)
                mlflow_artifact_location = mlflow_exp.artifact_location

            except MlflowException as e:
                logger.error(f"Failed to create MLflow experiment: {e}")
                # Continue without MLflow

        # Create in database
        experiment = Experiment(
            experiment_id=str(uuid.uuid4()),
            name=name,
            description=description,
            mlflow_experiment_id=mlflow_experiment_id,
            tags=tags or {},
            artifact_location=mlflow_artifact_location,
            run_count=0,
            created_by=created_by
        )

        created = self.experiment_repo.create(experiment)
        logger.info(f"Created experiment {name} with ID {created.experiment_id}")

        return created

    def sync_experiment_from_mlflow(self, mlflow_experiment_id: str) -> Experiment:
        """Sync experiment from MLflow.

        Args:
            mlflow_experiment_id: MLflow experiment ID

        Returns:
            Created or updated Experiment instance

        Raises:
            ValueError: If MLflow not available or experiment not found
        """
        if not MLFLOW_AVAILABLE or not self.mlflow_client:
            raise ValueError("MLflow is not available")

        try:
            mlflow_exp = self.mlflow_client.get_experiment(mlflow_experiment_id)

            # Check if already synced
            existing = self.experiment_repo.get_by_mlflow_experiment_id(mlflow_experiment_id)
            if existing:
                logger.info(f"Experiment {mlflow_exp.name} already synced")
                return existing

            # Get run count
            runs = self.mlflow_client.search_runs(experiment_ids=[mlflow_experiment_id])
            run_count = len(runs)

            # Create experiment
            experiment = Experiment(
                experiment_id=str(uuid.uuid4()),
                name=mlflow_exp.name,
                mlflow_experiment_id=mlflow_experiment_id,
                tags=dict(mlflow_exp.tags) if mlflow_exp.tags else {},
                artifact_location=mlflow_exp.artifact_location,
                run_count=run_count
            )

            created = self.experiment_repo.create(experiment)
            logger.info(f"Synced experiment {mlflow_exp.name} from MLflow")

            return created

        except MlflowException as e:
            logger.error(f"Failed to sync MLflow experiment: {e}")
            raise ValueError(f"MLflow experiment {mlflow_experiment_id} not found")

    def start_run(
        self,
        experiment_id: str,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new MLflow run for an experiment.

        Args:
            experiment_id: Experiment identifier
            run_name: Optional run name
            tags: Optional run tags

        Returns:
            MLflow run ID

        Raises:
            ValueError: If experiment not found or MLflow not available
        """
        experiment = self.experiment_repo.get_by_id(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        if not MLFLOW_AVAILABLE:
            raise ValueError("MLflow is not available")

        if not experiment.mlflow_experiment_id:
            raise ValueError(f"Experiment {experiment_id} not synced with MLflow")

        # Start MLflow run
        run = mlflow.start_run(
            experiment_id=experiment.mlflow_experiment_id,
            run_name=run_name,
            tags=tags
        )

        # Increment run count
        self.experiment_repo.increment_run_count(experiment_id)

        logger.info(f"Started run {run.info.run_id} for experiment {experiment.name}")

        return run.info.run_id

    def log_metrics(
        self,
        run_id: str,
        metrics: Dict[str, float],
        step: Optional[int] = None
    ) -> None:
        """Log metrics to MLflow run.

        Args:
            run_id: MLflow run ID
            metrics: Dictionary of metric names and values
            step: Optional step number

        Raises:
            ValueError: If MLflow not available
        """
        if not MLFLOW_AVAILABLE:
            raise ValueError("MLflow is not available")

        with mlflow.start_run(run_id=run_id):
            for metric_name, value in metrics.items():
                mlflow.log_metric(metric_name, value, step=step)

        logger.info(f"Logged {len(metrics)} metrics to run {run_id}")

    def log_parameters(self, run_id: str, params: Dict[str, Any]) -> None:
        """Log parameters to MLflow run.

        Args:
            run_id: MLflow run ID
            params: Dictionary of parameter names and values

        Raises:
            ValueError: If MLflow not available
        """
        if not MLFLOW_AVAILABLE:
            raise ValueError("MLflow is not available")

        with mlflow.start_run(run_id=run_id):
            mlflow.log_params(params)

        logger.info(f"Logged {len(params)} parameters to run {run_id}")

    def end_run(self, run_id: Optional[str] = None) -> None:
        """End an MLflow run.

        Args:
            run_id: Optional MLflow run ID (ends active run if None)

        Raises:
            ValueError: If MLflow not available
        """
        if not MLFLOW_AVAILABLE:
            raise ValueError("MLflow is not available")

        if run_id:
            with mlflow.start_run(run_id=run_id):
                mlflow.end_run()
        else:
            mlflow.end_run()

        logger.info(f"Ended run {run_id or 'active run'}")

    def get_experiment_details(self, experiment_id: str) -> Dict[str, Any]:
        """Get detailed experiment information.

        Args:
            experiment_id: Experiment identifier

        Returns:
            Dictionary with experiment details

        Raises:
            ValueError: If experiment not found
        """
        experiment = self.experiment_repo.get_by_id(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Get models from this experiment
        models = []
        if experiment.mlflow_experiment_id:
            models = self.model_repo.get_models_by_experiment(
                experiment.mlflow_experiment_id
            )

        return {
            "experiment_id": experiment.experiment_id,
            "name": experiment.name,
            "description": experiment.description,
            "mlflow_experiment_id": experiment.mlflow_experiment_id,
            "tags": experiment.tags,
            "artifact_location": experiment.artifact_location,
            "run_count": experiment.run_count,
            "model_count": len(models),
            "created_by": experiment.created_by,
            "created_at": experiment.created_at.isoformat(),
            "updated_at": experiment.updated_at.isoformat(),
            "models": [
                {
                    "model_id": m.model_id,
                    "name": m.name,
                    "version": m.version,
                    "is_production": m.is_production,
                    "accuracy": m.accuracy
                }
                for m in models
            ]
        }

    def get_experiment_leaderboard(
        self,
        experiment_id: str,
        metric: str = "accuracy",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get leaderboard of best models from an experiment.

        Args:
            experiment_id: Experiment identifier
            metric: Metric to rank by
            limit: Maximum number of results

        Returns:
            List of top performing models

        Raises:
            ValueError: If experiment not found
        """
        experiment = self.experiment_repo.get_by_id(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        if not experiment.mlflow_experiment_id:
            return []

        # Get models from this experiment
        models = self.model_repo.get_models_by_experiment(
            experiment.mlflow_experiment_id
        )

        # Sort by metric
        metric_attr = getattr(models[0] if models else None, metric, None)
        if metric_attr is None and models:
            # Check if metric is in custom_metrics
            models_with_metric = [
                m for m in models
                if m.custom_metrics and metric in m.custom_metrics
            ]
            sorted_models = sorted(
                models_with_metric,
                key=lambda m: m.custom_metrics[metric],
                reverse=True
            )[:limit]
        else:
            # Standard metric
            sorted_models = sorted(
                [m for m in models if getattr(m, metric) is not None],
                key=lambda m: getattr(m, metric),
                reverse=True
            )[:limit]

        return [
            {
                "rank": idx + 1,
                "model_id": m.model_id,
                "name": m.name,
                "version": m.version,
                "mlflow_run_id": m.mlflow_run_id,
                metric: getattr(m, metric, m.custom_metrics.get(metric) if m.custom_metrics else None),
                "is_production": m.is_production,
                "created_at": m.created_at.isoformat()
            }
            for idx, m in enumerate(sorted_models)
        ]

    def compare_runs(
        self,
        experiment_id: str,
        run_ids: List[str]
    ) -> Dict[str, Any]:
        """Compare multiple runs from an experiment.

        Args:
            experiment_id: Experiment identifier
            run_ids: List of MLflow run IDs

        Returns:
            Dictionary with comparison data

        Raises:
            ValueError: If experiment not found or MLflow not available
        """
        experiment = self.experiment_repo.get_by_id(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        if not MLFLOW_AVAILABLE or not self.mlflow_client:
            raise ValueError("MLflow is not available")

        runs_data = []
        for run_id in run_ids:
            try:
                run = self.mlflow_client.get_run(run_id)
                runs_data.append({
                    "run_id": run_id,
                    "run_name": run.data.tags.get("mlflow.runName", ""),
                    "status": run.info.status,
                    "metrics": dict(run.data.metrics),
                    "params": dict(run.data.params),
                    "start_time": datetime.fromtimestamp(
                        run.info.start_time / 1000
                    ).isoformat(),
                })
            except MlflowException as e:
                logger.warning(f"Failed to get run {run_id}: {e}")

        return {
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "runs": runs_data,
            "comparison_count": len(runs_data)
        }

    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete an experiment.

        Args:
            experiment_id: Experiment identifier

        Returns:
            True if deleted

        Raises:
            ValueError: If experiment not found
        """
        experiment = self.experiment_repo.get_by_id(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Delete from MLflow if synced
        if experiment.mlflow_experiment_id and MLFLOW_AVAILABLE and self.mlflow_client:
            try:
                self.mlflow_client.delete_experiment(experiment.mlflow_experiment_id)
                logger.info(f"Deleted MLflow experiment {experiment.mlflow_experiment_id}")
            except MlflowException as e:
                logger.warning(f"Failed to delete MLflow experiment: {e}")

        # Delete from database
        deleted = self.experiment_repo.delete(experiment_id)
        logger.info(f"Deleted experiment {experiment.name}")

        return deleted

    def get_all_experiments_summary(self) -> Dict[str, Any]:
        """Get summary of all experiments.

        Returns:
            Dictionary with experiments summary
        """
        experiments = self.experiment_repo.list_all()
        stats = self.experiment_repo.get_experiment_stats()

        return {
            "total_experiments": stats["total_experiments"],
            "total_runs": stats["total_runs"],
            "avg_runs_per_experiment": stats["avg_runs_per_experiment"],
            "most_active_experiment": stats["most_active_experiment"],
            "experiments": [
                {
                    "experiment_id": e.experiment_id,
                    "name": e.name,
                    "run_count": e.run_count,
                    "mlflow_synced": e.mlflow_experiment_id is not None,
                    "created_at": e.created_at.isoformat()
                }
                for e in experiments
            ]
        }
