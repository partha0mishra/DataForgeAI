"""Model registry for versioning and deployment management."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import mlflow
from mlflow.tracking import MlflowClient

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class ModelStage(str, Enum):
    """Model lifecycle stages."""

    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


@dataclass
class ModelVersion:
    """Model version information."""

    name: str
    version: str
    stage: ModelStage
    run_id: str
    created_at: datetime
    updated_at: datetime
    description: str
    tags: Dict[str, str]
    metrics: Dict[str, float]


@dataclass
class RegisteredModel:
    """Registered model information."""

    name: str
    latest_version: str
    description: str
    tags: Dict[str, str]
    versions: List[ModelVersion]


class ModelRegistry:
    """
    Model registry for managing model lifecycle.

    Provides:
    - Model registration
    - Version management
    - Stage transitions (None → Staging → Production → Archived)
    - Model comparison
    - Deployment tracking

    Example:
        registry = ModelRegistry(tracking_uri="http://mlflow:5000")

        # Register model from run
        version = registry.register_model(
            model_uri="runs:/abc123/model",
            name="customer_churn_predictor",
            description="XGBoost model for churn prediction"
        )

        # Transition to production
        registry.transition_stage(
            name="customer_churn_predictor",
            version=version,
            stage=ModelStage.PRODUCTION
        )

        # Get production model
        model = registry.get_model("customer_churn_predictor", stage="Production")
    """

    def __init__(self, tracking_uri: Optional[str] = None):
        """
        Initialize model registry.

        Args:
            tracking_uri: MLflow tracking server URI
        """
        self.logger = logger

        # Set tracking URI
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)

        # MLflow client
        self.client = MlflowClient()

        self.logger.info("Model registry initialized", tracking_uri=tracking_uri)

    def register_model(
        self,
        model_uri: str,
        name: str,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Register model in registry.

        Args:
            model_uri: URI to model (e.g., "runs:/run_id/model")
            name: Model name
            description: Model description
            tags: Model tags

        Returns:
            Model version
        """
        # Register model
        result = mlflow.register_model(model_uri, name)

        version = result.version

        # Update description
        if description:
            self.client.update_model_version(
                name=name,
                version=version,
                description=description,
            )

        # Add tags
        if tags:
            for key, value in tags.items():
                self.client.set_model_version_tag(name, version, key, value)

        self.logger.info(
            "Model registered",
            name=name,
            version=version,
        )

        return version

    def get_model(
        self,
        name: str,
        version: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> Any:
        """
        Load model from registry.

        Args:
            name: Model name
            version: Specific version (optional)
            stage: Stage to load from (optional)

        Returns:
            Loaded model
        """
        if version:
            model_uri = f"models:/{name}/{version}"
        elif stage:
            model_uri = f"models:/{name}/{stage}"
        else:
            # Load latest version
            model_uri = f"models:/{name}/latest"

        model = mlflow.pyfunc.load_model(model_uri)

        self.logger.info(
            "Model loaded",
            name=name,
            version=version,
            stage=stage,
        )

        return model

    def get_model_version(self, name: str, version: str) -> ModelVersion:
        """
        Get model version information.

        Args:
            name: Model name
            version: Version number

        Returns:
            Model version info
        """
        mv = self.client.get_model_version(name, version)

        # Get run to fetch metrics
        run = self.client.get_run(mv.run_id)

        return ModelVersion(
            name=mv.name,
            version=mv.version,
            stage=ModelStage(mv.current_stage),
            run_id=mv.run_id,
            created_at=datetime.fromtimestamp(mv.creation_timestamp / 1000),
            updated_at=datetime.fromtimestamp(mv.last_updated_timestamp / 1000),
            description=mv.description or "",
            tags=mv.tags,
            metrics=run.data.metrics,
        )

    def list_models(self) -> List[RegisteredModel]:
        """
        List all registered models.

        Returns:
            List of registered models
        """
        models = self.client.search_registered_models()

        result = []
        for model in models:
            versions = [
                self.get_model_version(model.name, v.version)
                for v in model.latest_versions
            ]

            result.append(
                RegisteredModel(
                    name=model.name,
                    latest_version=model.latest_versions[0].version if model.latest_versions else "0",
                    description=model.description or "",
                    tags=model.tags,
                    versions=versions,
                )
            )

        return result

    def transition_stage(
        self,
        name: str,
        version: str,
        stage: ModelStage,
        archive_existing: bool = True,
    ) -> None:
        """
        Transition model to new stage.

        Args:
            name: Model name
            version: Version number
            stage: New stage
            archive_existing: Archive existing models in target stage
        """
        self.client.transition_model_version_stage(
            name=name,
            version=version,
            stage=stage.value,
            archive_existing_versions=archive_existing,
        )

        self.logger.info(
            "Model stage transitioned",
            name=name,
            version=version,
            stage=stage.value,
        )

    def delete_model_version(self, name: str, version: str) -> None:
        """Delete model version."""
        self.client.delete_model_version(name, version)
        self.logger.info("Model version deleted", name=name, version=version)

    def delete_model(self, name: str) -> None:
        """Delete entire model (all versions)."""
        self.client.delete_registered_model(name)
        self.logger.info("Model deleted", name=name)

    def update_model_description(
        self,
        name: str,
        version: str,
        description: str,
    ) -> None:
        """Update model version description."""
        self.client.update_model_version(
            name=name,
            version=version,
            description=description,
        )

        self.logger.info("Model description updated", name=name, version=version)

    def add_model_tag(
        self,
        name: str,
        version: str,
        key: str,
        value: str,
    ) -> None:
        """Add tag to model version."""
        self.client.set_model_version_tag(name, version, key, value)
        self.logger.debug("Model tag added", name=name, version=version, tag=key)

    def compare_versions(
        self,
        name: str,
        versions: List[str],
    ) -> Dict[str, Any]:
        """
        Compare multiple versions of a model.

        Args:
            name: Model name
            versions: List of version numbers

        Returns:
            Comparison data
        """
        version_data = []

        for version in versions:
            mv = self.get_model_version(name, version)
            version_data.append(
                {
                    "version": mv.version,
                    "stage": mv.stage.value,
                    "metrics": mv.metrics,
                    "created_at": mv.created_at.isoformat(),
                    "description": mv.description,
                }
            )

        # Collect all metrics
        all_metrics = set()
        for v in version_data:
            all_metrics.update(v["metrics"].keys())

        return {
            "model_name": name,
            "versions": version_data,
            "metrics": list(all_metrics),
        }

    def get_production_model(self, name: str) -> Optional[ModelVersion]:
        """
        Get production version of model.

        Args:
            name: Model name

        Returns:
            Production model version or None
        """
        try:
            versions = self.client.get_latest_versions(name, stages=["Production"])
            if versions:
                return self.get_model_version(name, versions[0].version)
        except Exception as e:
            self.logger.warning(
                "No production model found",
                name=name,
                error=str(e),
            )

        return None

    def promote_to_production(
        self,
        name: str,
        version: str,
        archive_existing: bool = True,
    ) -> None:
        """
        Promote model version to production.

        Args:
            name: Model name
            version: Version to promote
            archive_existing: Archive existing production models
        """
        # First move to staging if not already there
        current = self.get_model_version(name, version)
        if current.stage == ModelStage.NONE:
            self.transition_stage(name, version, ModelStage.STAGING, archive_existing=False)

        # Then promote to production
        self.transition_stage(name, version, ModelStage.PRODUCTION, archive_existing)

        self.logger.info(
            "Model promoted to production",
            name=name,
            version=version,
        )

    def rollback_production(self, name: str, to_version: str) -> None:
        """
        Rollback production to previous version.

        Args:
            name: Model name
            to_version: Version to rollback to
        """
        self.promote_to_production(name, to_version, archive_existing=True)

        self.logger.info(
            "Production rolled back",
            name=name,
            to_version=to_version,
        )

    def get_model_lineage(self, name: str, version: str) -> Dict[str, Any]:
        """
        Get model lineage information.

        Args:
            name: Model name
            version: Version number

        Returns:
            Lineage information
        """
        mv = self.get_model_version(name, version)
        run = self.client.get_run(mv.run_id)

        return {
            "model_name": name,
            "version": version,
            "run_id": mv.run_id,
            "experiment_id": run.info.experiment_id,
            "parameters": run.data.params,
            "metrics": run.data.metrics,
            "tags": run.data.tags,
            "artifacts": [
                artifact.path
                for artifact in self.client.list_artifacts(mv.run_id)
            ],
        }
