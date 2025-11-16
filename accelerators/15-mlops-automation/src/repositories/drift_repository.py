"""Repository for Drift Detection data access operations."""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from src.models.drift_detection import DriftDetection


class DriftRepository:
    """Repository for managing drift detection data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, drift: DriftDetection) -> DriftDetection:
        """Create a new drift detection record.

        Args:
            drift: DriftDetection instance to create

        Returns:
            Created DriftDetection instance
        """
        self.db.add(drift)
        self.db.commit()
        self.db.refresh(drift)
        return drift

    def get_by_id(self, drift_id: str) -> Optional[DriftDetection]:
        """Get drift detection by ID.

        Args:
            drift_id: Drift detection identifier

        Returns:
            DriftDetection instance or None if not found
        """
        return self.db.query(DriftDetection).filter(
            DriftDetection.drift_id == drift_id
        ).first()

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        drift_detected: Optional[bool] = None,
    ) -> List[DriftDetection]:
        """List all drift detections with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            drift_detected: Filter by drift detection status (optional)

        Returns:
            List of DriftDetection instances
        """
        query = self.db.query(DriftDetection)

        if drift_detected is not None:
            query = query.filter(DriftDetection.is_drift_detected == drift_detected)

        return query.order_by(
            desc(DriftDetection.detection_timestamp)
        ).offset(skip).limit(limit).all()

    def get_by_model(
        self,
        model_id: str,
        drift_detected_only: bool = False
    ) -> List[DriftDetection]:
        """Get all drift detections for a specific model.

        Args:
            model_id: Model identifier
            drift_detected_only: Only return records where drift was detected

        Returns:
            List of DriftDetection instances
        """
        query = self.db.query(DriftDetection).filter(
            DriftDetection.model_id == model_id
        )

        if drift_detected_only:
            query = query.filter(DriftDetection.is_drift_detected == True)

        return query.order_by(desc(DriftDetection.detection_timestamp)).all()

    def get_by_deployment(
        self,
        deployment_id: str,
        drift_detected_only: bool = False
    ) -> List[DriftDetection]:
        """Get all drift detections for a specific deployment.

        Args:
            deployment_id: Deployment identifier
            drift_detected_only: Only return records where drift was detected

        Returns:
            List of DriftDetection instances
        """
        query = self.db.query(DriftDetection).filter(
            DriftDetection.deployment_id == deployment_id
        )

        if drift_detected_only:
            query = query.filter(DriftDetection.is_drift_detected == True)

        return query.order_by(desc(DriftDetection.detection_timestamp)).all()

    def get_recent_detections(
        self,
        hours: int = 24,
        drift_detected_only: bool = False
    ) -> List[DriftDetection]:
        """Get recent drift detections.

        Args:
            hours: Number of hours to look back
            drift_detected_only: Only return records where drift was detected

        Returns:
            List of recent DriftDetection instances
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(DriftDetection).filter(
            DriftDetection.detection_timestamp >= cutoff_time
        )

        if drift_detected_only:
            query = query.filter(DriftDetection.is_drift_detected == True)

        return query.order_by(desc(DriftDetection.detection_timestamp)).all()

    def get_by_drift_type(
        self,
        drift_type: str,
        model_id: Optional[str] = None
    ) -> List[DriftDetection]:
        """Get drift detections by type.

        Args:
            drift_type: Type of drift (data_drift, concept_drift, prediction_drift)
            model_id: Filter by model ID (optional)

        Returns:
            List of DriftDetection instances
        """
        query = self.db.query(DriftDetection).filter(
            DriftDetection.drift_type == drift_type
        )

        if model_id:
            query = query.filter(DriftDetection.model_id == model_id)

        return query.order_by(desc(DriftDetection.detection_timestamp)).all()

    def get_high_severity_drifts(
        self,
        severity: str = "high",
        hours: int = 24
    ) -> List[DriftDetection]:
        """Get high severity drift detections.

        Args:
            severity: Severity level (high, medium, low)
            hours: Number of hours to look back

        Returns:
            List of high severity DriftDetection instances
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return self.db.query(DriftDetection).filter(
            and_(
                DriftDetection.severity == severity,
                DriftDetection.is_drift_detected == True,
                DriftDetection.detection_timestamp >= cutoff_time
            )
        ).order_by(desc(DriftDetection.detection_timestamp)).all()

    def get_auto_retrain_triggered(self, hours: int = 24) -> List[DriftDetection]:
        """Get drift detections that triggered auto-retraining.

        Args:
            hours: Number of hours to look back

        Returns:
            List of DriftDetection instances that triggered retraining
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return self.db.query(DriftDetection).filter(
            and_(
                DriftDetection.auto_retrain_triggered == True,
                DriftDetection.detection_timestamp >= cutoff_time
            )
        ).order_by(desc(DriftDetection.detection_timestamp)).all()

    def get_detections_by_threshold(
        self,
        min_score: float,
        max_score: Optional[float] = None
    ) -> List[DriftDetection]:
        """Get drift detections within a score range.

        Args:
            min_score: Minimum drift score
            max_score: Maximum drift score (optional)

        Returns:
            List of DriftDetection instances
        """
        query = self.db.query(DriftDetection).filter(
            DriftDetection.drift_score >= min_score
        )

        if max_score is not None:
            query = query.filter(DriftDetection.drift_score <= max_score)

        return query.order_by(desc(DriftDetection.drift_score)).all()

    def get_latest_detection_for_model(self, model_id: str) -> Optional[DriftDetection]:
        """Get the most recent drift detection for a model.

        Args:
            model_id: Model identifier

        Returns:
            Latest DriftDetection instance or None
        """
        return self.db.query(DriftDetection).filter(
            DriftDetection.model_id == model_id
        ).order_by(desc(DriftDetection.detection_timestamp)).first()

    def update(self, drift_id: str, updates: Dict[str, Any]) -> Optional[DriftDetection]:
        """Update drift detection attributes.

        Args:
            drift_id: Drift detection identifier
            updates: Dictionary of attributes to update

        Returns:
            Updated DriftDetection instance or None if not found
        """
        drift = self.get_by_id(drift_id)
        if not drift:
            return None

        for key, value in updates.items():
            if hasattr(drift, key):
                setattr(drift, key, value)

        drift.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(drift)
        return drift

    def mark_auto_retrain_triggered(self, drift_id: str) -> Optional[DriftDetection]:
        """Mark that auto-retrain was triggered for a drift detection.

        Args:
            drift_id: Drift detection identifier

        Returns:
            Updated DriftDetection instance or None if not found
        """
        return self.update(drift_id, {"auto_retrain_triggered": True})

    def delete(self, drift_id: str) -> bool:
        """Delete a drift detection record.

        Args:
            drift_id: Drift detection identifier

        Returns:
            True if deleted, False if not found
        """
        drift = self.get_by_id(drift_id)
        if not drift:
            return False

        self.db.delete(drift)
        self.db.commit()
        return True

    def get_drift_statistics(
        self,
        model_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get drift detection statistics.

        Args:
            model_id: Filter by model ID (optional)
            hours: Number of hours to analyze

        Returns:
            Dictionary with drift statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(DriftDetection).filter(
            DriftDetection.detection_timestamp >= cutoff_time
        )

        if model_id:
            query = query.filter(DriftDetection.model_id == model_id)

        all_detections = query.all()
        drift_detected_count = sum(1 for d in all_detections if d.is_drift_detected)

        drift_rate = 0.0
        if len(all_detections) > 0:
            drift_rate = (drift_detected_count / len(all_detections)) * 100

        # Count by drift type
        drift_types = {}
        for detection in all_detections:
            if detection.is_drift_detected:
                drift_types[detection.drift_type] = drift_types.get(
                    detection.drift_type, 0
                ) + 1

        # Count by severity
        severity_counts = {}
        for detection in all_detections:
            if detection.is_drift_detected and detection.severity:
                severity_counts[detection.severity] = severity_counts.get(
                    detection.severity, 0
                ) + 1

        avg_drift_score = 0.0
        if all_detections:
            avg_drift_score = sum(d.drift_score for d in all_detections) / len(all_detections)

        return {
            "total_detections": len(all_detections),
            "drift_detected_count": drift_detected_count,
            "drift_rate_percentage": round(drift_rate, 2),
            "avg_drift_score": round(avg_drift_score, 4),
            "drift_by_type": drift_types,
            "drift_by_severity": severity_counts,
            "auto_retrain_triggered_count": sum(
                1 for d in all_detections if d.auto_retrain_triggered
            ),
        }

    def count_by_drift_type(self) -> Dict[str, int]:
        """Get count of drift detections grouped by type.

        Returns:
            Dictionary mapping drift type to count
        """
        results = self.db.query(
            DriftDetection.drift_type,
            func.count(DriftDetection.drift_id).label('count')
        ).filter(
            DriftDetection.is_drift_detected == True
        ).group_by(DriftDetection.drift_type).all()

        return {drift_type: count for drift_type, count in results}

    def count_by_severity(self) -> Dict[str, int]:
        """Get count of drift detections grouped by severity.

        Returns:
            Dictionary mapping severity to count
        """
        results = self.db.query(
            DriftDetection.severity,
            func.count(DriftDetection.drift_id).label('count')
        ).filter(
            DriftDetection.is_drift_detected == True
        ).group_by(DriftDetection.severity).all()

        return {severity: count for severity, count in results if severity}

    def cleanup_old_detections(self, days_to_keep: int = 90) -> int:
        """Delete drift detections older than specified days.

        Args:
            days_to_keep: Number of days to keep records

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        deleted_count = self.db.query(DriftDetection).filter(
            DriftDetection.detection_timestamp < cutoff_date
        ).delete()

        self.db.commit()
        return deleted_count
