"""Repository for Experiment data access operations."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from src.models.experiment import Experiment


class ExperimentRepository:
    """Repository for managing experiment data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, experiment: Experiment) -> Experiment:
        """Create a new experiment.

        Args:
            experiment: Experiment instance to create

        Returns:
            Created Experiment instance
        """
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    def get_by_id(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID.

        Args:
            experiment_id: Experiment identifier

        Returns:
            Experiment instance or None if not found
        """
        return self.db.query(Experiment).filter(
            Experiment.experiment_id == experiment_id
        ).first()

    def get_by_name(self, name: str) -> Optional[Experiment]:
        """Get experiment by name.

        Args:
            name: Experiment name

        Returns:
            Experiment instance or None if not found
        """
        return self.db.query(Experiment).filter(
            Experiment.name == name
        ).first()

    def get_by_mlflow_experiment_id(
        self,
        mlflow_experiment_id: str
    ) -> Optional[Experiment]:
        """Get experiment by MLflow experiment ID.

        Args:
            mlflow_experiment_id: MLflow experiment identifier

        Returns:
            Experiment instance or None if not found
        """
        return self.db.query(Experiment).filter(
            Experiment.mlflow_experiment_id == mlflow_experiment_id
        ).first()

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Experiment]:
        """List all experiments.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Experiment instances
        """
        return self.db.query(Experiment).order_by(
            desc(Experiment.created_at)
        ).offset(skip).limit(limit).all()

    def search_by_tags(self, tags: Dict[str, Any]) -> List[Experiment]:
        """Search experiments by tags.

        Args:
            tags: Dictionary of tag key-value pairs to search

        Returns:
            List of matching Experiment instances
        """
        query = self.db.query(Experiment)
        for key, value in tags.items():
            query = query.filter(Experiment.tags[key].astext == str(value))
        return query.order_by(desc(Experiment.created_at)).all()

    def get_experiments_by_creator(self, created_by: str) -> List[Experiment]:
        """Get experiments created by a specific user.

        Args:
            created_by: Creator identifier

        Returns:
            List of Experiment instances
        """
        return self.db.query(Experiment).filter(
            Experiment.created_by == created_by
        ).order_by(desc(Experiment.created_at)).all()

    def get_active_experiments(self, min_run_count: int = 1) -> List[Experiment]:
        """Get experiments with at least minimum run count.

        Args:
            min_run_count: Minimum number of runs

        Returns:
            List of active Experiment instances
        """
        return self.db.query(Experiment).filter(
            Experiment.run_count >= min_run_count
        ).order_by(desc(Experiment.run_count)).all()

    def get_experiments_created_after(self, date: datetime) -> List[Experiment]:
        """Get experiments created after a specific date.

        Args:
            date: Cutoff datetime

        Returns:
            List of Experiment instances
        """
        return self.db.query(Experiment).filter(
            Experiment.created_at >= date
        ).order_by(desc(Experiment.created_at)).all()

    def update(self, experiment_id: str, updates: Dict[str, Any]) -> Optional[Experiment]:
        """Update experiment attributes.

        Args:
            experiment_id: Experiment identifier
            updates: Dictionary of attributes to update

        Returns:
            Updated Experiment instance or None if not found
        """
        experiment = self.get_by_id(experiment_id)
        if not experiment:
            return None

        for key, value in updates.items():
            if hasattr(experiment, key):
                setattr(experiment, key, value)

        experiment.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    def increment_run_count(self, experiment_id: str, count: int = 1) -> Optional[Experiment]:
        """Increment run count for an experiment.

        Args:
            experiment_id: Experiment identifier
            count: Number to increment by

        Returns:
            Updated Experiment instance or None if not found
        """
        experiment = self.get_by_id(experiment_id)
        if not experiment:
            return None

        experiment.run_count = (experiment.run_count or 0) + count
        experiment.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    def update_tags(self, experiment_id: str, tags: Dict[str, Any]) -> Optional[Experiment]:
        """Update experiment tags.

        Args:
            experiment_id: Experiment identifier
            tags: New tags dictionary

        Returns:
            Updated Experiment instance or None if not found
        """
        experiment = self.get_by_id(experiment_id)
        if not experiment:
            return None

        if experiment.tags is None:
            experiment.tags = {}
        experiment.tags.update(tags)

        experiment.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    def delete(self, experiment_id: str) -> bool:
        """Delete an experiment.

        Args:
            experiment_id: Experiment identifier

        Returns:
            True if deleted, False if not found
        """
        experiment = self.get_by_id(experiment_id)
        if not experiment:
            return False

        self.db.delete(experiment)
        self.db.commit()
        return True

    def get_experiment_stats(self) -> Dict[str, Any]:
        """Get overall experiment statistics.

        Returns:
            Dictionary with experiment statistics
        """
        total_experiments = self.db.query(func.count(Experiment.experiment_id)).scalar()
        total_runs = self.db.query(func.sum(Experiment.run_count)).scalar() or 0

        avg_runs_per_experiment = 0
        if total_experiments > 0:
            avg_runs_per_experiment = total_runs / total_experiments

        most_active = self.db.query(Experiment).order_by(
            desc(Experiment.run_count)
        ).first()

        return {
            "total_experiments": total_experiments,
            "total_runs": total_runs,
            "avg_runs_per_experiment": round(avg_runs_per_experiment, 2),
            "most_active_experiment": {
                "name": most_active.name,
                "run_count": most_active.run_count
            } if most_active else None
        }

    def get_top_experiments(self, limit: int = 10) -> List[Experiment]:
        """Get top experiments by run count.

        Args:
            limit: Maximum number of results

        Returns:
            List of top Experiment instances
        """
        return self.db.query(Experiment).order_by(
            desc(Experiment.run_count)
        ).limit(limit).all()
