"""Drift detection for model monitoring."""

import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime
import numpy as np

from dataforge_common.logging import get_logger
from dataforge_common.tracing import trace_method

logger = get_logger(__name__)


class DriftDetectionManager:
    """Manages drift detection for deployed models."""

    def __init__(self):
        """Initialize drift detection manager."""
        self.analyses: Dict[str, List[Dict]] = {}
        logger.info("DriftDetectionManager initialized")

    @trace_method()
    async def analyze(
        self,
        model_id: str,
        reference_data_uri: Optional[str] = None,
        current_data_uri: Optional[str] = None,
        features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform drift analysis."""
        analysis_id = f"drift_{secrets.token_hex(8)}"

        # Simulate drift detection (use Evidently AI in production)
        drift_scores = self._calculate_drift_scores(features or ["feature1", "feature2", "feature3"])

        analysis = {
            "analysis_id": analysis_id,
            "model_id": model_id,
            "has_drift": any(score > 0.05 for score in drift_scores.values()),
            "drift_score": max(drift_scores.values()),
            "features_with_drift": [f for f, score in drift_scores.items() if score > 0.05],
            "drift_scores": drift_scores,
            "analysis_timestamp": datetime.utcnow(),
            "recommendations": self._generate_recommendations(drift_scores)
        }

        # Store analysis
        if model_id not in self.analyses:
            self.analyses[model_id] = []
        self.analyses[model_id].append(analysis)

        logger.info(f"Drift analysis completed for {model_id}: drift={analysis['has_drift']}")

        return analysis

    def _calculate_drift_scores(self, features: List[str]) -> Dict[str, float]:
        """Calculate drift scores using KS test or PSI."""
        # Simulate drift scores (use scipy.stats in production)
        return {feature: np.random.uniform(0, 0.15) for feature in features}

    def _generate_recommendations(self, drift_scores: Dict[str, float]) -> List[str]:
        """Generate recommendations based on drift analysis."""
        recommendations = []

        for feature, score in drift_scores.items():
            if score > 0.1:
                recommendations.append(f"Critical drift in {feature} (score: {score:.3f}) - immediate retraining recommended")
            elif score > 0.05:
                recommendations.append(f"Moderate drift in {feature} (score: {score:.3f}) - monitor closely")

        if not recommendations:
            recommendations.append("No significant drift detected - model performance stable")

        return recommendations

    @trace_method()
    async def get_latest_analysis(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get latest drift analysis for model."""
        if model_id not in self.analyses or not self.analyses[model_id]:
            return None

        return self.analyses[model_id][-1]
