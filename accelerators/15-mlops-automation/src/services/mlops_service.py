"""MLOps Service for model lifecycle management and MLflow integration."""
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

from src.models.ml_model import MLModel
from src.models.deployment import Deployment
from src.repositories.model_repository import ModelRepository
from src.repositories.deployment_repository import DeploymentRepository
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MLOpsService:
    """Service for ML model operations and MLflow integration."""

    def __init__(self, db: Session):
        """Initialize MLOps service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.model_repo = ModelRepository(db)
        self.deployment_repo = DeploymentRepository(db)

        # Initialize MLflow client
        if MLFLOW_AVAILABLE:
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            self.mlflow_client = MlflowClient()
        else:
            self.mlflow_client = None

    def register_model_from_mlflow(
        self,
        mlflow_run_id: str,
        model_name: str,
        version: str,
        tags: Optional[Dict[str, Any]] = None
    ) -> MLModel:
        """Register a model from MLflow run.

        Args:
            mlflow_run_id: MLflow run identifier
            model_name: Model name
            version: Model version
            tags: Optional tags dictionary

        Returns:
            Created MLModel instance

        Raises:
            ValueError: If MLflow is not available or run not found
        """
        if not MLFLOW_AVAILABLE or not self.mlflow_client:
            raise ValueError("MLflow is not available")

        try:
            # Fetch run details from MLflow
            run = self.mlflow_client.get_run(mlflow_run_id)

            # Extract metrics and parameters
            metrics = run.data.metrics
            params = run.data.params

            # Create model instance
            model = MLModel(
                model_id=str(uuid.uuid4()),
                name=model_name,
                version=version,
                framework=params.get('framework', 'unknown'),
                algorithm=params.get('algorithm'),
                mlflow_run_id=mlflow_run_id,
                mlflow_experiment_id=run.info.experiment_id,
                mlflow_model_uri=f"runs:/{mlflow_run_id}/model",
                description=run.data.tags.get('mlflow.note.content'),
                tags=tags or {},
                parameters=dict(params),
                accuracy=metrics.get('accuracy'),
                precision=metrics.get('precision'),
                recall=metrics.get('recall'),
                f1_score=metrics.get('f1_score'),
                auc_roc=metrics.get('auc_roc'),
                custom_metrics={k: v for k, v in metrics.items()
                              if k not in ['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc']},
                status='registered',
                created_by=run.data.tags.get('mlflow.user', 'system')
            )

            # Save to database
            return self.model_repo.create(model)

        except MlflowException as e:
            logger.error(f"Failed to fetch MLflow run {mlflow_run_id}: {e}")
            raise ValueError(f"MLflow run not found: {mlflow_run_id}")

    def register_model(
        self,
        name: str,
        version: str,
        framework: str,
        algorithm: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        tags: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> MLModel:
        """Register a new ML model.

        Args:
            name: Model name
            version: Model version
            framework: ML framework (sklearn, tensorflow, pytorch, etc.)
            algorithm: Algorithm name
            parameters: Model parameters
            metrics: Performance metrics
            tags: Model tags
            description: Model description
            created_by: Creator identifier

        Returns:
            Created MLModel instance
        """
        # Check if model version already exists
        existing = self.model_repo.get_by_name_and_version(name, version)
        if existing:
            raise ValueError(f"Model {name} version {version} already exists")

        model = MLModel(
            model_id=str(uuid.uuid4()),
            name=name,
            version=version,
            framework=framework,
            algorithm=algorithm,
            parameters=parameters or {},
            tags=tags or {},
            description=description,
            status='registered',
            created_by=created_by
        )

        # Set metrics if provided
        if metrics:
            for key in ['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc']:
                if key in metrics:
                    setattr(model, key, metrics[key])

            # Store custom metrics
            custom = {k: v for k, v in metrics.items()
                     if k not in ['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc']}
            if custom:
                model.custom_metrics = custom

        return self.model_repo.create(model)

    def promote_to_production(
        self,
        model_id: str,
        demote_current: bool = True
    ) -> MLModel:
        """Promote a model to production.

        Args:
            model_id: Model identifier
            demote_current: Whether to demote current production model

        Returns:
            Updated MLModel instance

        Raises:
            ValueError: If model not found
        """
        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        # Demote current production models of the same name
        if demote_current:
            production_models = self.model_repo.get_production_models()
            for prod_model in production_models:
                if prod_model.name == model.name and prod_model.model_id != model_id:
                    self.model_repo.set_production_status(prod_model.model_id, False)
                    logger.info(f"Demoted model {prod_model.model_id} from production")

        # Promote new model
        updated = self.model_repo.set_production_status(model_id, True)
        logger.info(f"Promoted model {model_id} to production")
        return updated

    def create_deployment(
        self,
        model_id: str,
        deployment_name: str,
        environment: str,
        strategy: str = "rolling",
        replicas: int = 1,
        resource_config: Optional[Dict[str, Any]] = None,
        traffic_percentage: int = 100,
        deployed_by: Optional[str] = None
    ) -> Deployment:
        """Create a new model deployment.

        Args:
            model_id: Model identifier
            deployment_name: Deployment name
            environment: Target environment (dev, staging, production)
            strategy: Deployment strategy (blue_green, canary, rolling, shadow)
            replicas: Number of replicas
            resource_config: Resource configuration (CPU, memory, GPU)
            traffic_percentage: Traffic percentage for canary deployments
            deployed_by: Deployer identifier

        Returns:
            Created Deployment instance

        Raises:
            ValueError: If model not found or invalid parameters
        """
        # Validate model exists
        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        # Validate environment
        valid_environments = ['dev', 'staging', 'production']
        if environment not in valid_environments:
            raise ValueError(f"Invalid environment. Must be one of {valid_environments}")

        # Validate strategy
        valid_strategies = ['blue_green', 'canary', 'rolling', 'shadow']
        if strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy. Must be one of {valid_strategies}")

        # Check for existing deployment with same name
        existing = self.deployment_repo.get_by_name(deployment_name)
        if existing:
            raise ValueError(f"Deployment {deployment_name} already exists")

        deployment = Deployment(
            deployment_id=str(uuid.uuid4()),
            model_id=model_id,
            deployment_name=deployment_name,
            environment=environment,
            strategy=strategy,
            status='pending',
            health_status='unknown',
            replicas=replicas,
            resource_config=resource_config or {},
            traffic_percentage=traffic_percentage,
            deployed_by=deployed_by
        )

        created = self.deployment_repo.create(deployment)
        logger.info(f"Created deployment {deployment_name} for model {model_id}")

        # Trigger deployment process (in real implementation, this would call k8s/cloud APIs)
        self._execute_deployment(created)

        return created

    def _execute_deployment(self, deployment: Deployment) -> None:
        """Execute the deployment process.

        In a real implementation, this would:
        - Generate Kubernetes manifests
        - Apply deployment to cluster
        - Configure service mesh for traffic routing
        - Set up monitoring and alerts

        Args:
            deployment: Deployment instance
        """
        logger.info(f"Executing {deployment.strategy} deployment for {deployment.deployment_id}")

        # Update status to deploying
        self.deployment_repo.update_status(deployment.deployment_id, 'deploying')

        # Simulate deployment (replace with actual deployment logic)
        try:
            if deployment.strategy == 'blue_green':
                self._execute_blue_green_deployment(deployment)
            elif deployment.strategy == 'canary':
                self._execute_canary_deployment(deployment)
            elif deployment.strategy == 'rolling':
                self._execute_rolling_deployment(deployment)
            elif deployment.strategy == 'shadow':
                self._execute_shadow_deployment(deployment)

            # Update deployment status
            self.deployment_repo.update(deployment.deployment_id, {
                'status': 'running',
                'health_status': 'healthy',
                'deployed_at': datetime.utcnow()
            })

            logger.info(f"Deployment {deployment.deployment_id} completed successfully")

        except Exception as e:
            logger.error(f"Deployment {deployment.deployment_id} failed: {e}")
            self.deployment_repo.update_status(deployment.deployment_id, 'failed')
            raise

    def _execute_blue_green_deployment(self, deployment: Deployment) -> None:
        """Execute blue-green deployment strategy.

        Args:
            deployment: Deployment instance
        """
        logger.info(f"Executing blue-green deployment for {deployment.deployment_id}")
        # In production:
        # 1. Deploy new version (green) alongside old version (blue)
        # 2. Run health checks on green
        # 3. Switch traffic from blue to green
        # 4. Keep blue running for rollback capability
        # 5. After validation period, remove blue

    def _execute_canary_deployment(self, deployment: Deployment) -> None:
        """Execute canary deployment strategy.

        Args:
            deployment: Deployment instance
        """
        logger.info(f"Executing canary deployment for {deployment.deployment_id}")
        # In production:
        # 1. Deploy canary version with small traffic percentage
        # 2. Monitor metrics (error rate, latency, etc.)
        # 3. Gradually increase traffic if metrics are good
        # 4. Rollback if metrics degrade

    def _execute_rolling_deployment(self, deployment: Deployment) -> None:
        """Execute rolling deployment strategy.

        Args:
            deployment: Deployment instance
        """
        logger.info(f"Executing rolling deployment for {deployment.deployment_id}")
        # In production:
        # 1. Update pods one by one
        # 2. Wait for each pod to be healthy
        # 3. Continue to next pod
        # 4. Rollback if any pod fails health check

    def _execute_shadow_deployment(self, deployment: Deployment) -> None:
        """Execute shadow deployment strategy.

        Args:
            deployment: Deployment instance
        """
        logger.info(f"Executing shadow deployment for {deployment.deployment_id}")
        # In production:
        # 1. Deploy shadow version
        # 2. Mirror production traffic to shadow
        # 3. Compare predictions without affecting users
        # 4. Validate performance before full rollout

    def update_canary_traffic(
        self,
        deployment_id: str,
        traffic_percentage: int
    ) -> Deployment:
        """Update traffic percentage for canary deployment.

        Args:
            deployment_id: Deployment identifier
            traffic_percentage: New traffic percentage (0-100)

        Returns:
            Updated Deployment instance

        Raises:
            ValueError: If deployment not found or not a canary deployment
        """
        deployment = self.deployment_repo.get_by_id(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        if deployment.strategy != 'canary':
            raise ValueError(f"Deployment {deployment_id} is not a canary deployment")

        # Update traffic percentage
        updated = self.deployment_repo.update_traffic_percentage(
            deployment_id,
            traffic_percentage
        )

        logger.info(f"Updated canary traffic to {traffic_percentage}% for {deployment_id}")

        # In production, this would update service mesh configuration
        # (e.g., Istio VirtualService, AWS App Mesh routes)

        return updated

    def rollback_deployment(self, deployment_id: str) -> Deployment:
        """Rollback a deployment.

        Args:
            deployment_id: Deployment identifier

        Returns:
            Updated Deployment instance

        Raises:
            ValueError: If deployment not found
        """
        deployment = self.deployment_repo.get_by_id(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        # Update status
        updated = self.deployment_repo.update_status(deployment_id, 'rolled_back')

        logger.warning(f"Rolled back deployment {deployment_id}")

        # In production:
        # 1. Identify previous stable deployment
        # 2. Route traffic back to previous version
        # 3. Remove failed deployment
        # 4. Trigger alerts

        return updated

    def get_model_with_deployments(self, model_id: str) -> Dict[str, Any]:
        """Get model with all its deployments.

        Args:
            model_id: Model identifier

        Returns:
            Dictionary with model and deployment information

        Raises:
            ValueError: If model not found
        """
        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        deployments = self.deployment_repo.get_by_model(model_id)

        return {
            "model": {
                "model_id": model.model_id,
                "name": model.name,
                "version": model.version,
                "framework": model.framework,
                "status": model.status,
                "is_production": model.is_production,
                "metrics": {
                    "accuracy": model.accuracy,
                    "precision": model.precision,
                    "recall": model.recall,
                    "f1_score": model.f1_score,
                    "auc_roc": model.auc_roc,
                },
                "created_at": model.created_at.isoformat(),
            },
            "deployments": [
                {
                    "deployment_id": d.deployment_id,
                    "deployment_name": d.deployment_name,
                    "environment": d.environment,
                    "strategy": d.strategy,
                    "status": d.status,
                    "health_status": d.health_status,
                    "traffic_percentage": d.traffic_percentage,
                }
                for d in deployments
            ],
            "deployment_count": len(deployments),
        }

    def compare_models(self, model_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple models by their metrics.

        Args:
            model_ids: List of model identifiers

        Returns:
            Dictionary with comparison data

        Raises:
            ValueError: If any model not found
        """
        models = []
        for model_id in model_ids:
            model = self.model_repo.get_by_id(model_id)
            if not model:
                raise ValueError(f"Model {model_id} not found")
            models.append(model)

        comparison = {
            "models": [
                {
                    "model_id": m.model_id,
                    "name": m.name,
                    "version": m.version,
                    "framework": m.framework,
                    "accuracy": m.accuracy,
                    "precision": m.precision,
                    "recall": m.recall,
                    "f1_score": m.f1_score,
                    "auc_roc": m.auc_roc,
                    "is_production": m.is_production,
                }
                for m in models
            ],
            "winner_by_metric": self._determine_winners(models),
        }

        return comparison

    def _determine_winners(self, models: List[MLModel]) -> Dict[str, str]:
        """Determine best model for each metric.

        Args:
            models: List of MLModel instances

        Returns:
            Dictionary mapping metric to best model ID
        """
        winners = {}

        for metric in ['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc']:
            best_model = max(
                (m for m in models if getattr(m, metric) is not None),
                key=lambda m: getattr(m, metric),
                default=None
            )
            if best_model:
                winners[metric] = best_model.model_id

        return winners
