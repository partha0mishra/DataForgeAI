"""Repository for ML Model data access operations."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from src.models.ml_model import MLModel


class ModelRepository:
    """Repository for managing ML model data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, model: MLModel) -> MLModel:
        """Create a new ML model.

        Args:
            model: MLModel instance to create

        Returns:
            Created MLModel instance
        """
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def get_by_id(self, model_id: str) -> Optional[MLModel]:
        """Get model by ID.

        Args:
            model_id: Model identifier

        Returns:
            MLModel instance or None if not found
        """
        return self.db.query(MLModel).filter(MLModel.model_id == model_id).first()

    def get_by_name_and_version(self, name: str, version: str) -> Optional[MLModel]:
        """Get model by name and version.

        Args:
            name: Model name
            version: Model version

        Returns:
            MLModel instance or None if not found
        """
        return self.db.query(MLModel).filter(
            and_(MLModel.name == name, MLModel.version == version)
        ).first()

    def get_by_mlflow_run_id(self, mlflow_run_id: str) -> Optional[MLModel]:
        """Get model by MLflow run ID.

        Args:
            mlflow_run_id: MLflow run identifier

        Returns:
            MLModel instance or None if not found
        """
        return self.db.query(MLModel).filter(
            MLModel.mlflow_run_id == mlflow_run_id
        ).first()

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        framework: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[MLModel]:
        """List all models with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            framework: Filter by framework (optional)
            status: Filter by status (optional)

        Returns:
            List of MLModel instances
        """
        query = self.db.query(MLModel)

        if framework:
            query = query.filter(MLModel.framework == framework)
        if status:
            query = query.filter(MLModel.status == status)

        return query.order_by(desc(MLModel.created_at)).offset(skip).limit(limit).all()

    def get_production_models(self) -> List[MLModel]:
        """Get all models currently in production.

        Returns:
            List of production MLModel instances
        """
        return self.db.query(MLModel).filter(
            MLModel.is_production == True
        ).order_by(desc(MLModel.created_at)).all()

    def get_models_by_name(self, name: str) -> List[MLModel]:
        """Get all versions of a model by name.

        Args:
            name: Model name

        Returns:
            List of MLModel instances, ordered by version descending
        """
        return self.db.query(MLModel).filter(
            MLModel.name == name
        ).order_by(desc(MLModel.version)).all()

    def get_latest_version(self, name: str) -> Optional[MLModel]:
        """Get the latest version of a model by name.

        Args:
            name: Model name

        Returns:
            Latest MLModel instance or None
        """
        return self.db.query(MLModel).filter(
            MLModel.name == name
        ).order_by(desc(MLModel.version)).first()

    def get_models_by_experiment(self, experiment_id: str) -> List[MLModel]:
        """Get all models from a specific experiment.

        Args:
            experiment_id: MLflow experiment ID

        Returns:
            List of MLModel instances
        """
        return self.db.query(MLModel).filter(
            MLModel.mlflow_experiment_id == experiment_id
        ).order_by(desc(MLModel.created_at)).all()

    def search_by_tags(self, tags: Dict[str, Any]) -> List[MLModel]:
        """Search models by tags.

        Args:
            tags: Dictionary of tag key-value pairs to search

        Returns:
            List of matching MLModel instances
        """
        # For PostgreSQL JSONB queries
        query = self.db.query(MLModel)
        for key, value in tags.items():
            query = query.filter(MLModel.tags[key].astext == str(value))
        return query.order_by(desc(MLModel.created_at)).all()

    def get_top_performing_models(
        self,
        metric: str = "accuracy",
        limit: int = 10,
        framework: Optional[str] = None,
    ) -> List[MLModel]:
        """Get top performing models by a specific metric.

        Args:
            metric: Metric name (accuracy, precision, recall, f1_score, auc_roc)
            limit: Maximum number of results
            framework: Filter by framework (optional)

        Returns:
            List of top performing MLModel instances
        """
        query = self.db.query(MLModel)

        if framework:
            query = query.filter(MLModel.framework == framework)

        # Get the appropriate metric column
        metric_column = getattr(MLModel, metric, None)
        if metric_column is None:
            raise ValueError(f"Invalid metric: {metric}")

        return query.filter(metric_column.isnot(None)).order_by(
            desc(metric_column)
        ).limit(limit).all()

    def update(self, model_id: str, updates: Dict[str, Any]) -> Optional[MLModel]:
        """Update model attributes.

        Args:
            model_id: Model identifier
            updates: Dictionary of attributes to update

        Returns:
            Updated MLModel instance or None if not found
        """
        model = self.get_by_id(model_id)
        if not model:
            return None

        for key, value in updates.items():
            if hasattr(model, key):
                setattr(model, key, value)

        model.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(model)
        return model

    def set_production_status(self, model_id: str, is_production: bool) -> Optional[MLModel]:
        """Update model production status.

        Args:
            model_id: Model identifier
            is_production: Production status

        Returns:
            Updated MLModel instance or None if not found
        """
        return self.update(model_id, {"is_production": is_production})

    def update_metrics(self, model_id: str, metrics: Dict[str, float]) -> Optional[MLModel]:
        """Update model performance metrics.

        Args:
            model_id: Model identifier
            metrics: Dictionary of metric names and values

        Returns:
            Updated MLModel instance or None if not found
        """
        model = self.get_by_id(model_id)
        if not model:
            return None

        # Update standard metrics
        for metric_name in ["accuracy", "precision", "recall", "f1_score", "auc_roc"]:
            if metric_name in metrics:
                setattr(model, metric_name, metrics[metric_name])

        # Update custom metrics
        custom_metrics = {k: v for k, v in metrics.items()
                         if k not in ["accuracy", "precision", "recall", "f1_score", "auc_roc"]}
        if custom_metrics:
            if model.custom_metrics is None:
                model.custom_metrics = {}
            model.custom_metrics.update(custom_metrics)

        model.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(model)
        return model

    def delete(self, model_id: str) -> bool:
        """Delete a model.

        Args:
            model_id: Model identifier

        Returns:
            True if deleted, False if not found
        """
        model = self.get_by_id(model_id)
        if not model:
            return False

        self.db.delete(model)
        self.db.commit()
        return True

    def count_by_framework(self) -> Dict[str, int]:
        """Get count of models grouped by framework.

        Returns:
            Dictionary mapping framework to count
        """
        results = self.db.query(
            MLModel.framework,
            func.count(MLModel.model_id).label('count')
        ).group_by(MLModel.framework).all()

        return {framework: count for framework, count in results}

    def count_by_status(self) -> Dict[str, int]:
        """Get count of models grouped by status.

        Returns:
            Dictionary mapping status to count
        """
        results = self.db.query(
            MLModel.status,
            func.count(MLModel.model_id).label('count')
        ).group_by(MLModel.status).all()

        return {status: count for status, count in results}

    def get_models_created_after(self, date: datetime) -> List[MLModel]:
        """Get models created after a specific date.

        Args:
            date: Cutoff datetime

        Returns:
            List of MLModel instances
        """
        return self.db.query(MLModel).filter(
            MLModel.created_at >= date
        ).order_by(desc(MLModel.created_at)).all()
