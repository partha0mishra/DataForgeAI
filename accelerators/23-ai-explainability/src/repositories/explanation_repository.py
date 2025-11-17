"""Repository for Explanation model."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from src.models.explanation import Explanation


class ExplanationRepository:
    """Repository for managing explanations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, explanation_data: Dict[str, Any]) -> Explanation:
        """
        Create a new explanation.

        Args:
            explanation_data: Dictionary containing explanation fields

        Returns:
            Created Explanation object
        """
        explanation = Explanation(**explanation_data)
        self.db.add(explanation)
        self.db.commit()
        self.db.refresh(explanation)
        return explanation

    def get_by_id(self, explanation_id: str) -> Optional[Explanation]:
        """Get explanation by ID."""
        return self.db.query(Explanation).filter(Explanation.explanation_id == explanation_id).first()

    def get_by_model_id(
        self,
        model_id: str,
        explanation_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Explanation]:
        """
        Get explanations for a specific model.

        Args:
            model_id: Model identifier
            explanation_type: Optional filter by explanation type
            limit: Maximum number of results

        Returns:
            List of explanations
        """
        query = self.db.query(Explanation).filter(Explanation.model_id == model_id)

        if explanation_type:
            query = query.filter(Explanation.explanation_type == explanation_type)

        return query.order_by(desc(Explanation.created_at)).limit(limit).all()

    def get_by_instance_id(self, instance_id: str) -> List[Explanation]:
        """Get all explanations for a specific instance."""
        return (
            self.db.query(Explanation)
            .filter(Explanation.instance_id == instance_id)
            .order_by(desc(Explanation.created_at))
            .all()
        )

    def get_global_explanations(
        self,
        model_id: Optional[str] = None,
        explanation_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Explanation]:
        """
        Get global (model-level) explanations.

        Args:
            model_id: Optional filter by model
            explanation_type: Optional filter by type
            limit: Maximum results

        Returns:
            List of global explanations
        """
        query = self.db.query(Explanation).filter(Explanation.scope == 'global')

        if model_id:
            query = query.filter(Explanation.model_id == model_id)
        if explanation_type:
            query = query.filter(Explanation.explanation_type == explanation_type)

        return query.order_by(desc(Explanation.created_at)).limit(limit).all()

    def get_local_explanations(
        self,
        model_id: str,
        explanation_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Explanation]:
        """Get local (instance-level) explanations for a model."""
        query = (
            self.db.query(Explanation)
            .filter(Explanation.model_id == model_id)
            .filter(Explanation.scope == 'local')
        )

        if explanation_type:
            query = query.filter(Explanation.explanation_type == explanation_type)

        return query.order_by(desc(Explanation.created_at)).limit(limit).all()

    def get_recent_explanations(
        self,
        hours: int = 24,
        model_id: Optional[str] = None,
        explanation_type: Optional[str] = None
    ) -> List[Explanation]:
        """
        Get explanations created in the last N hours.

        Args:
            hours: Number of hours to look back
            model_id: Optional model filter
            explanation_type: Optional type filter

        Returns:
            List of recent explanations
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        query = self.db.query(Explanation).filter(Explanation.created_at >= since)

        if model_id:
            query = query.filter(Explanation.model_id == model_id)
        if explanation_type:
            query = query.filter(Explanation.explanation_type == explanation_type)

        return query.order_by(desc(Explanation.created_at)).all()

    def get_top_features_by_model(
        self,
        model_id: str,
        explanation_type: str = 'shap',
        top_n: int = 10
    ) -> Dict[str, float]:
        """
        Get aggregated top features for a model across all explanations.

        Args:
            model_id: Model identifier
            explanation_type: Type of explanation
            top_n: Number of top features to return

        Returns:
            Dictionary of feature names to average importance
        """
        explanations = (
            self.db.query(Explanation)
            .filter(Explanation.model_id == model_id)
            .filter(Explanation.explanation_type == explanation_type)
            .filter(Explanation.scope == 'global')
            .all()
        )

        # Aggregate feature importances
        feature_sums: Dict[str, List[float]] = {}
        for exp in explanations:
            if exp.feature_importances:
                for feature, importance in exp.feature_importances.items():
                    if feature not in feature_sums:
                        feature_sums[feature] = []
                    feature_sums[feature].append(abs(importance))

        # Calculate averages
        feature_averages = {
            feature: sum(values) / len(values)
            for feature, values in feature_sums.items()
        }

        # Sort and return top N
        sorted_features = sorted(feature_averages.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_features[:top_n])

    def get_explanation_stats(
        self,
        model_id: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about explanations.

        Args:
            model_id: Optional model filter
            hours: Optional time range in hours

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(Explanation)

        if model_id:
            query = query.filter(Explanation.model_id == model_id)
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(Explanation.created_at >= since)

        total_count = query.count()

        # Count by type
        type_counts = (
            query.with_entities(
                Explanation.explanation_type,
                func.count(Explanation.explanation_id).label('count')
            )
            .group_by(Explanation.explanation_type)
            .all()
        )

        # Count by scope
        scope_counts = (
            query.with_entities(
                Explanation.scope,
                func.count(Explanation.explanation_id).label('count')
            )
            .group_by(Explanation.scope)
            .all()
        )

        # Average generation time
        avg_time = query.with_entities(
            func.avg(Explanation.generation_time_ms)
        ).scalar() or 0

        return {
            'total_explanations': total_count,
            'by_type': {t: c for t, c in type_counts},
            'by_scope': {s: c for s, c in scope_counts},
            'avg_generation_time_ms': float(avg_time),
            'unique_models': query.with_entities(
                func.count(func.distinct(Explanation.model_id))
            ).scalar()
        }

    def delete(self, explanation_id: str) -> bool:
        """Delete an explanation."""
        explanation = self.get_by_id(explanation_id)
        if explanation:
            self.db.delete(explanation)
            self.db.commit()
            return True
        return False

    def delete_old_explanations(self, days_to_keep: int = 90) -> int:
        """
        Delete explanations older than specified days.

        Args:
            days_to_keep: Number of days to retain

        Returns:
            Number of deleted explanations
        """
        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
        count = (
            self.db.query(Explanation)
            .filter(Explanation.created_at < cutoff)
            .delete()
        )
        self.db.commit()
        return count

    def update(self, explanation_id: str, updates: Dict[str, Any]) -> Optional[Explanation]:
        """Update an explanation."""
        explanation = self.get_by_id(explanation_id)
        if explanation:
            for key, value in updates.items():
                if hasattr(explanation, key):
                    setattr(explanation, key, value)
            self.db.commit()
            self.db.refresh(explanation)
        return explanation

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = 'created_at'
    ) -> List[Explanation]:
        """List all explanations with pagination."""
        query = self.db.query(Explanation)

        if order_by == 'created_at':
            query = query.order_by(desc(Explanation.created_at))
        elif order_by == 'model_id':
            query = query.order_by(Explanation.model_id)

        return query.offset(skip).limit(limit).all()
