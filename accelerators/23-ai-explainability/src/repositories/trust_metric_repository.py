"""Repository for TrustMetric model."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from src.models.trust_metric import TrustMetric


class TrustMetricRepository:
    """Repository for managing trust metrics."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, metric_data: Dict[str, Any]) -> TrustMetric:
        """Create a new trust metric."""
        metric = TrustMetric(**metric_data)
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def get_by_id(self, metric_id: str) -> Optional[TrustMetric]:
        """Get trust metric by ID."""
        return self.db.query(TrustMetric).filter(TrustMetric.metric_id == metric_id).first()

    def get_by_model_id(
        self,
        model_id: str,
        limit: int = 50
    ) -> List[TrustMetric]:
        """Get all trust metrics for a model."""
        return (
            self.db.query(TrustMetric)
            .filter(TrustMetric.model_id == model_id)
            .order_by(desc(TrustMetric.created_at))
            .limit(limit)
            .all()
        )

    def get_latest_by_model(
        self,
        model_id: str,
        environment: Optional[str] = None
    ) -> Optional[TrustMetric]:
        """
        Get the most recent trust metric for a model.

        Args:
            model_id: Model identifier
            environment: Optional environment filter (dev/staging/production)

        Returns:
            Latest trust metric or None
        """
        query = self.db.query(TrustMetric).filter(TrustMetric.model_id == model_id)

        if environment:
            query = query.filter(TrustMetric.environment == environment)

        return query.order_by(desc(TrustMetric.created_at)).first()

    def get_by_trust_level(
        self,
        trust_level: str,
        environment: Optional[str] = None,
        limit: int = 100
    ) -> List[TrustMetric]:
        """
        Get trust metrics by trust level.

        Args:
            trust_level: Trust level (high/medium/low/critical)
            environment: Optional environment filter
            limit: Maximum results

        Returns:
            List of trust metrics
        """
        query = self.db.query(TrustMetric).filter(TrustMetric.trust_level == trust_level)

        if environment:
            query = query.filter(TrustMetric.environment == environment)

        return query.order_by(desc(TrustMetric.created_at)).limit(limit).all()

    def get_low_trust_models(
        self,
        threshold: float = 0.6,
        environment: Optional[str] = None
    ) -> List[TrustMetric]:
        """
        Get models with low trust scores.

        Args:
            threshold: Trust score threshold (0-1)
            environment: Optional environment filter

        Returns:
            List of low trust metrics
        """
        query = self.db.query(TrustMetric).filter(
            TrustMetric.overall_trust_score < threshold
        )

        if environment:
            query = query.filter(TrustMetric.environment == environment)

        return query.order_by(TrustMetric.overall_trust_score).all()

    def get_certified_models(
        self,
        certification_status: str = 'certified',
        limit: int = 100
    ) -> List[TrustMetric]:
        """Get models by certification status."""
        return (
            self.db.query(TrustMetric)
            .filter(TrustMetric.certification_status == certification_status)
            .order_by(desc(TrustMetric.overall_trust_score))
            .limit(limit)
            .all()
        )

    def get_declining_trust_models(self, limit: int = 50) -> List[TrustMetric]:
        """Get models with declining trust scores."""
        return (
            self.db.query(TrustMetric)
            .filter(TrustMetric.score_trend == 'declining')
            .order_by(TrustMetric.overall_trust_score)
            .limit(limit)
            .all()
        )

    def get_trust_history(
        self,
        model_id: str,
        days: int = 90
    ) -> List[TrustMetric]:
        """
        Get trust score history for a model.

        Args:
            model_id: Model identifier
            days: Number of days to look back

        Returns:
            List of trust metrics ordered by date
        """
        since = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(TrustMetric)
            .filter(TrustMetric.model_id == model_id)
            .filter(TrustMetric.created_at >= since)
            .order_by(TrustMetric.created_at)
            .all()
        )

    def get_dimension_scores(
        self,
        model_id: str
    ) -> Optional[Dict[str, float]]:
        """
        Get latest dimension scores for a model.

        Returns:
            Dictionary with dimension scores or None
        """
        latest = self.get_latest_by_model(model_id)
        if not latest:
            return None

        return {
            'explainability': latest.explainability_score,
            'fairness': latest.fairness_score,
            'robustness': latest.robustness_score,
            'privacy': latest.privacy_score,
            'transparency': latest.transparency_score or 0,
            'accountability': latest.accountability_score or 0,
            'overall': latest.overall_trust_score
        }

    def get_trust_stats(
        self,
        environment: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about trust metrics.

        Args:
            environment: Optional environment filter
            hours: Optional time range

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(TrustMetric)

        if environment:
            query = query.filter(TrustMetric.environment == environment)
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(TrustMetric.created_at >= since)

        total_count = query.count()

        # Average scores
        avg_overall = query.with_entities(
            func.avg(TrustMetric.overall_trust_score)
        ).scalar() or 0

        avg_explainability = query.with_entities(
            func.avg(TrustMetric.explainability_score)
        ).scalar() or 0

        avg_fairness = query.with_entities(
            func.avg(TrustMetric.fairness_score)
        ).scalar() or 0

        avg_robustness = query.with_entities(
            func.avg(TrustMetric.robustness_score)
        ).scalar() or 0

        avg_privacy = query.with_entities(
            func.avg(TrustMetric.privacy_score)
        ).scalar() or 0

        # Count by trust level
        level_counts = (
            query.with_entities(
                TrustMetric.trust_level,
                func.count(TrustMetric.metric_id).label('count')
            )
            .group_by(TrustMetric.trust_level)
            .all()
        )

        # Count by certification status
        cert_counts = (
            query.with_entities(
                TrustMetric.certification_status,
                func.count(TrustMetric.metric_id).label('count')
            )
            .group_by(TrustMetric.certification_status)
            .all()
        )

        return {
            'total_assessments': total_count,
            'avg_overall_trust': round(float(avg_overall), 3),
            'avg_dimensions': {
                'explainability': round(float(avg_explainability), 3),
                'fairness': round(float(avg_fairness), 3),
                'robustness': round(float(avg_robustness), 3),
                'privacy': round(float(avg_privacy), 3)
            },
            'by_trust_level': {level: count for level, count in level_counts},
            'by_certification': {cert: count for cert, count in cert_counts},
            'unique_models': query.with_entities(
                func.count(func.distinct(TrustMetric.model_id))
            ).scalar()
        }

    def get_weakest_dimension(
        self,
        model_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Identify the weakest trust dimension for a model.

        Returns:
            Dictionary with dimension name and score
        """
        latest = self.get_latest_by_model(model_id)
        if not latest:
            return None

        dimensions = {
            'explainability': latest.explainability_score,
            'fairness': latest.fairness_score,
            'robustness': latest.robustness_score,
            'privacy': latest.privacy_score,
        }

        if latest.transparency_score is not None:
            dimensions['transparency'] = latest.transparency_score
        if latest.accountability_score is not None:
            dimensions['accountability'] = latest.accountability_score

        weakest = min(dimensions.items(), key=lambda x: x[1])
        return {
            'dimension': weakest[0],
            'score': weakest[1],
            'recommendations': latest.recommendations or []
        }

    def update(self, metric_id: str, updates: Dict[str, Any]) -> Optional[TrustMetric]:
        """Update a trust metric."""
        metric = self.get_by_id(metric_id)
        if metric:
            for key, value in updates.items():
                if hasattr(metric, key):
                    setattr(metric, key, value)
            self.db.commit()
            self.db.refresh(metric)
        return metric

    def delete(self, metric_id: str) -> bool:
        """Delete a trust metric."""
        metric = self.get_by_id(metric_id)
        if metric:
            self.db.delete(metric)
            self.db.commit()
            return True
        return False

    def delete_old_metrics(self, days_to_keep: int = 365) -> int:
        """Delete metrics older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
        count = (
            self.db.query(TrustMetric)
            .filter(TrustMetric.created_at < cutoff)
            .delete()
        )
        self.db.commit()
        return count

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = 'created_at'
    ) -> List[TrustMetric]:
        """List all metrics with pagination."""
        query = self.db.query(TrustMetric)

        if order_by == 'created_at':
            query = query.order_by(desc(TrustMetric.created_at))
        elif order_by == 'trust_score':
            query = query.order_by(desc(TrustMetric.overall_trust_score))

        return query.offset(skip).limit(limit).all()
