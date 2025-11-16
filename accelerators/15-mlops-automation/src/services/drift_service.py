"""Drift Detection Service for monitoring model performance and data drift."""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import logging
import numpy as np
from sqlalchemy.orm import Session

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. Install with: pip install scipy")

from src.models.drift_detection import DriftDetection
from src.repositories.drift_repository import DriftRepository
from src.repositories.model_repository import ModelRepository
from src.repositories.deployment_repository import DeploymentRepository

logger = logging.getLogger(__name__)


class DriftService:
    """Service for detecting and monitoring model drift."""

    def __init__(self, db: Session):
        """Initialize drift detection service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.drift_repo = DriftRepository(db)
        self.model_repo = ModelRepository(db)
        self.deployment_repo = DeploymentRepository(db)

    def detect_data_drift(
        self,
        model_id: str,
        reference_data: np.ndarray,
        current_data: np.ndarray,
        feature_names: Optional[List[str]] = None,
        threshold: float = 0.05,
        deployment_id: Optional[str] = None
    ) -> DriftDetection:
        """Detect data drift using statistical tests.

        Args:
            model_id: Model identifier
            reference_data: Reference dataset (training data)
            current_data: Current production data
            feature_names: Optional feature names
            threshold: P-value threshold for drift detection
            deployment_id: Optional deployment identifier

        Returns:
            Created DriftDetection instance

        Raises:
            ValueError: If model not found or data invalid
        """
        # Validate model exists
        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        # Validate data shapes match
        if reference_data.shape[1] != current_data.shape[1]:
            raise ValueError("Reference and current data must have same number of features")

        n_features = reference_data.shape[1]
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(n_features)]

        # Perform statistical tests for each feature
        affected_features = []
        statistical_tests = {}

        if not SCIPY_AVAILABLE:
            logger.warning("SciPy not available, using simplified drift detection")
            drift_score = self._simple_drift_score(reference_data, current_data)
        else:
            for i, feature_name in enumerate(feature_names):
                ref_feature = reference_data[:, i]
                curr_feature = current_data[:, i]

                # Kolmogorov-Smirnov test
                ks_stat, p_value = stats.ks_2samp(ref_feature, curr_feature)

                statistical_tests[feature_name] = {
                    "test": "kolmogorov_smirnov",
                    "statistic": float(ks_stat),
                    "p_value": float(p_value),
                    "drift_detected": p_value < threshold
                }

                if p_value < threshold:
                    affected_features.append({
                        "name": feature_name,
                        "p_value": float(p_value),
                        "ks_statistic": float(ks_stat)
                    })

            # Calculate overall drift score
            drift_score = np.mean([test["ks_statistic"]
                                  for test in statistical_tests.values()])

        is_drift_detected = len(affected_features) > 0
        severity = self._calculate_severity(drift_score, len(affected_features), n_features)

        # Generate recommendations
        recommendations = self._generate_drift_recommendations(
            is_drift_detected,
            severity,
            affected_features
        )

        # Create drift detection record
        drift = DriftDetection(
            drift_id=str(uuid.uuid4()),
            model_id=model_id,
            deployment_id=deployment_id,
            detection_timestamp=datetime.utcnow(),
            drift_type='data_drift',
            drift_score=float(drift_score),
            threshold=threshold,
            is_drift_detected=is_drift_detected,
            affected_features=affected_features,
            statistical_tests=statistical_tests,
            severity=severity,
            recommendations=recommendations,
            detection_method='kolmogorov_smirnov'
        )

        created = self.drift_repo.create(drift)
        logger.info(f"Data drift detection completed for model {model_id}: "
                   f"drift_detected={is_drift_detected}, severity={severity}")

        # Trigger auto-retrain if high severity drift
        if is_drift_detected and severity == 'high':
            self._trigger_auto_retrain(created)

        return created

    def detect_prediction_drift(
        self,
        model_id: str,
        reference_predictions: np.ndarray,
        current_predictions: np.ndarray,
        threshold: float = 0.05,
        deployment_id: Optional[str] = None
    ) -> DriftDetection:
        """Detect prediction drift.

        Args:
            model_id: Model identifier
            reference_predictions: Historical predictions
            current_predictions: Current predictions
            threshold: Threshold for drift detection
            deployment_id: Optional deployment identifier

        Returns:
            Created DriftDetection instance
        """
        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        if SCIPY_AVAILABLE:
            # Statistical test on prediction distributions
            ks_stat, p_value = stats.ks_2samp(reference_predictions, current_predictions)
            drift_score = float(ks_stat)
            is_drift_detected = p_value < threshold

            statistical_tests = {
                "predictions": {
                    "test": "kolmogorov_smirnov",
                    "statistic": float(ks_stat),
                    "p_value": float(p_value),
                    "drift_detected": is_drift_detected
                }
            }
        else:
            drift_score = self._simple_drift_score(
                reference_predictions.reshape(-1, 1),
                current_predictions.reshape(-1, 1)
            )
            is_drift_detected = drift_score > threshold
            statistical_tests = {}

        severity = self._calculate_severity(drift_score, 1 if is_drift_detected else 0, 1)

        drift = DriftDetection(
            drift_id=str(uuid.uuid4()),
            model_id=model_id,
            deployment_id=deployment_id,
            detection_timestamp=datetime.utcnow(),
            drift_type='prediction_drift',
            drift_score=drift_score,
            threshold=threshold,
            is_drift_detected=is_drift_detected,
            statistical_tests=statistical_tests,
            severity=severity,
            recommendations=self._generate_drift_recommendations(
                is_drift_detected, severity, []
            ),
            detection_method='prediction_distribution_analysis'
        )

        created = self.drift_repo.create(drift)
        logger.info(f"Prediction drift detection completed for model {model_id}: "
                   f"drift_detected={is_drift_detected}")

        if is_drift_detected and severity == 'high':
            self._trigger_auto_retrain(created)

        return created

    def detect_concept_drift(
        self,
        model_id: str,
        true_labels: np.ndarray,
        predictions: np.ndarray,
        historical_accuracy: float,
        threshold: float = 0.1,
        deployment_id: Optional[str] = None
    ) -> DriftDetection:
        """Detect concept drift by monitoring model performance.

        Args:
            model_id: Model identifier
            true_labels: Ground truth labels
            predictions: Model predictions
            historical_accuracy: Historical accuracy baseline
            threshold: Acceptable accuracy drop threshold
            deployment_id: Optional deployment identifier

        Returns:
            Created DriftDetection instance
        """
        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        # Calculate current accuracy
        current_accuracy = np.mean(predictions == true_labels)
        accuracy_drop = historical_accuracy - current_accuracy

        is_drift_detected = accuracy_drop > threshold
        drift_score = float(accuracy_drop)

        severity = self._calculate_severity(drift_score, 1 if is_drift_detected else 0, 1)

        drift = DriftDetection(
            drift_id=str(uuid.uuid4()),
            model_id=model_id,
            deployment_id=deployment_id,
            detection_timestamp=datetime.utcnow(),
            drift_type='concept_drift',
            drift_score=drift_score,
            threshold=threshold,
            is_drift_detected=is_drift_detected,
            statistical_tests={
                "accuracy": {
                    "historical": historical_accuracy,
                    "current": float(current_accuracy),
                    "drop": float(accuracy_drop)
                }
            },
            severity=severity,
            recommendations=self._generate_drift_recommendations(
                is_drift_detected, severity, []
            ),
            detection_method='performance_monitoring'
        )

        created = self.drift_repo.create(drift)
        logger.info(f"Concept drift detection completed for model {model_id}: "
                   f"accuracy_drop={accuracy_drop:.4f}")

        if is_drift_detected and severity == 'high':
            self._trigger_auto_retrain(created)

        return created

    def _simple_drift_score(
        self,
        reference_data: np.ndarray,
        current_data: np.ndarray
    ) -> float:
        """Calculate simplified drift score without scipy.

        Args:
            reference_data: Reference dataset
            current_data: Current dataset

        Returns:
            Drift score between 0 and 1
        """
        # Compare means and standard deviations
        ref_mean = np.mean(reference_data, axis=0)
        curr_mean = np.mean(current_data, axis=0)

        ref_std = np.std(reference_data, axis=0)
        curr_std = np.std(current_data, axis=0)

        # Normalized difference
        mean_diff = np.abs(ref_mean - curr_mean) / (ref_std + 1e-10)
        std_diff = np.abs(ref_std - curr_std) / (ref_std + 1e-10)

        drift_score = np.mean(mean_diff + std_diff) / 2
        return float(np.clip(drift_score, 0, 1))

    def _calculate_severity(
        self,
        drift_score: float,
        affected_features_count: int,
        total_features: int
    ) -> str:
        """Calculate drift severity level.

        Args:
            drift_score: Overall drift score
            affected_features_count: Number of features with drift
            total_features: Total number of features

        Returns:
            Severity level: low, medium, or high
        """
        affected_ratio = affected_features_count / total_features if total_features > 0 else 0

        if drift_score > 0.7 or affected_ratio > 0.5:
            return 'high'
        elif drift_score > 0.4 or affected_ratio > 0.25:
            return 'medium'
        else:
            return 'low'

    def _generate_drift_recommendations(
        self,
        is_drift_detected: bool,
        severity: str,
        affected_features: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on drift detection.

        Args:
            is_drift_detected: Whether drift was detected
            severity: Drift severity level
            affected_features: List of affected features

        Returns:
            List of recommendation strings
        """
        if not is_drift_detected:
            return ["No significant drift detected. Continue monitoring."]

        recommendations = []

        if severity == 'high':
            recommendations.append("🔴 High severity drift detected. Immediate action required.")
            recommendations.append("Consider triggering model retraining with recent data.")
            recommendations.append("Review data pipeline for potential issues.")
        elif severity == 'medium':
            recommendations.append("🟡 Medium severity drift detected. Schedule model retraining.")
            recommendations.append("Investigate root causes of drift.")
        else:
            recommendations.append("🟢 Low severity drift detected. Monitor closely.")

        if affected_features:
            feature_names = [f["name"] for f in affected_features[:5]]
            recommendations.append(
                f"Most affected features: {', '.join(feature_names)}"
            )

        recommendations.append("Set up alerts for continued monitoring.")
        recommendations.append("Document drift analysis for future reference.")

        return recommendations

    def _trigger_auto_retrain(self, drift: DriftDetection) -> None:
        """Trigger automatic model retraining.

        Args:
            drift: DriftDetection instance
        """
        logger.warning(f"Auto-retrain triggered for model {drift.model_id} "
                      f"due to {drift.severity} severity {drift.drift_type}")

        # Mark as triggered
        self.drift_repo.mark_auto_retrain_triggered(drift.drift_id)

        # In production, this would:
        # 1. Fetch latest training data
        # 2. Queue retraining job
        # 3. Notify ML engineers
        # 4. Update experiment tracking

    def get_drift_summary(
        self,
        model_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get drift detection summary for a model.

        Args:
            model_id: Model identifier
            hours: Time window in hours

        Returns:
            Dictionary with drift summary
        """
        statistics = self.drift_repo.get_drift_statistics(model_id, hours)
        recent_drifts = self.drift_repo.get_recent_detections(hours, drift_detected_only=True)

        model_drifts = [d for d in recent_drifts if d.model_id == model_id]

        return {
            "model_id": model_id,
            "time_window_hours": hours,
            "statistics": statistics,
            "recent_drift_events": [
                {
                    "drift_id": d.drift_id,
                    "drift_type": d.drift_type,
                    "severity": d.severity,
                    "drift_score": d.drift_score,
                    "timestamp": d.detection_timestamp.isoformat(),
                    "auto_retrain_triggered": d.auto_retrain_triggered
                }
                for d in model_drifts
            ],
            "requires_attention": any(d.severity == 'high' for d in model_drifts)
        }

    def monitor_deployment_drift(
        self,
        deployment_id: str,
        data_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Monitor drift for a specific deployment.

        Args:
            deployment_id: Deployment identifier
            data_window_hours: Time window for drift analysis

        Returns:
            Dictionary with deployment drift monitoring data
        """
        deployment = self.deployment_repo.get_by_id(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        drift_detections = self.drift_repo.get_by_deployment(deployment_id)
        recent_drifts = [
            d for d in drift_detections
            if d.detection_timestamp >= datetime.utcnow() - timedelta(hours=data_window_hours)
        ]

        drift_by_type = {}
        for drift in recent_drifts:
            if drift.drift_type not in drift_by_type:
                drift_by_type[drift.drift_type] = []
            drift_by_type[drift.drift_type].append({
                "severity": drift.severity,
                "score": drift.drift_score,
                "timestamp": drift.detection_timestamp.isoformat()
            })

        return {
            "deployment_id": deployment_id,
            "deployment_name": deployment.deployment_name,
            "model_id": deployment.model_id,
            "environment": deployment.environment,
            "total_drift_detections": len(recent_drifts),
            "drift_by_type": drift_by_type,
            "high_severity_count": sum(1 for d in recent_drifts if d.severity == 'high'),
            "auto_retrain_triggered": any(d.auto_retrain_triggered for d in recent_drifts),
            "health_recommendation": self._get_health_recommendation(recent_drifts)
        }

    def _get_health_recommendation(
        self,
        recent_drifts: List[DriftDetection]
    ) -> str:
        """Get health recommendation based on recent drifts.

        Args:
            recent_drifts: List of recent drift detections

        Returns:
            Health recommendation string
        """
        high_severity_count = sum(1 for d in recent_drifts if d.severity == 'high')

        if high_severity_count > 0:
            return "CRITICAL: High severity drift detected. Immediate investigation required."
        elif len(recent_drifts) > 5:
            return "WARNING: Multiple drift events detected. Review model performance."
        elif len(recent_drifts) > 0:
            return "MONITORING: Some drift detected. Continue monitoring."
        else:
            return "HEALTHY: No significant drift detected."
