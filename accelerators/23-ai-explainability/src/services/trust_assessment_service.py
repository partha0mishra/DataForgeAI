"""Service for assessing overall trust in AI models."""

from typing import Dict, List, Optional, Any
import numpy as np
from datetime import datetime
import time
import logging

from sqlalchemy.orm import Session

from src.repositories.trust_metric_repository import TrustMetricRepository
from src.repositories.explanation_repository import ExplanationRepository
from src.repositories.bias_report_repository import BiasReportRepository
from src.models.trust_metric import TrustMetric

logger = logging.getLogger(__name__)


class TrustAssessmentService:
    """Service for comprehensive trust assessment of AI models."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.trust_repo = TrustMetricRepository(db)
        self.explanation_repo = ExplanationRepository(db)
        self.bias_repo = BiasReportRepository(db)

    def assess_model_trust(
        self,
        model_id: str,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        environment: str = 'production',
        assessment_type: str = 'periodic',
        regulatory_framework: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None,
        assessed_by: Optional[str] = None
    ) -> TrustMetric:
        """
        Perform comprehensive trust assessment.

        Args:
            model_id: Model identifier
            model_name: Model name
            model_version: Model version
            environment: Deployment environment
            assessment_type: Type of assessment
            regulatory_framework: Regulatory framework to comply with
            weights: Custom weights for dimensions
            assessed_by: User performing assessment

        Returns:
            TrustMetric object with trust scores
        """
        start_time = time.time()

        try:
            # Calculate individual dimension scores
            explainability_score = self._assess_explainability(model_id)
            fairness_score = self._assess_fairness(model_id)
            robustness_score = self._assess_robustness(model_id)
            privacy_score = self._assess_privacy(model_id)
            transparency_score = self._assess_transparency(model_id)
            accountability_score = self._assess_accountability(model_id)

            # Default weights if not provided
            if weights is None:
                weights = {
                    'explainability': 0.20,
                    'fairness': 0.25,
                    'robustness': 0.20,
                    'privacy': 0.15,
                    'transparency': 0.10,
                    'accountability': 0.10
                }

            # Calculate overall trust score
            overall_trust_score = (
                explainability_score * weights['explainability'] +
                fairness_score * weights['fairness'] +
                robustness_score * weights['robustness'] +
                privacy_score * weights['privacy'] +
                transparency_score * weights['transparency'] +
                accountability_score * weights['accountability']
            )

            # Determine trust level
            trust_level = self._determine_trust_level(overall_trust_score)

            # Get previous score for trend analysis
            previous_metric = self.trust_repo.get_latest_by_model(model_id, environment)
            previous_score = previous_metric.overall_trust_score if previous_metric else None
            score_trend = self._calculate_trend(overall_trust_score, previous_score)

            # Calculate changes since last assessment
            changes_since_last = None
            if previous_metric:
                changes_since_last = {
                    'explainability': {
                        'old': previous_metric.explainability_score,
                        'new': explainability_score,
                        'change': explainability_score - previous_metric.explainability_score
                    },
                    'fairness': {
                        'old': previous_metric.fairness_score,
                        'new': fairness_score,
                        'change': fairness_score - previous_metric.fairness_score
                    },
                    'robustness': {
                        'old': previous_metric.robustness_score,
                        'new': robustness_score,
                        'change': robustness_score - previous_metric.robustness_score
                    },
                    'privacy': {
                        'old': previous_metric.privacy_score,
                        'new': privacy_score,
                        'change': privacy_score - previous_metric.privacy_score
                    }
                }

            # Identify strengths and weaknesses
            dimension_scores = {
                'explainability': explainability_score,
                'fairness': fairness_score,
                'robustness': robustness_score,
                'privacy': privacy_score,
                'transparency': transparency_score,
                'accountability': accountability_score
            }

            strengths = [dim for dim, score in dimension_scores.items() if score >= 0.8]
            weaknesses = [dim for dim, score in dimension_scores.items() if score < 0.6]

            # Generate recommendations
            recommendations = self._generate_trust_recommendations(
                dimension_scores, weaknesses, regulatory_framework
            )

            # Determine certification status
            certification_status = self._determine_certification(
                overall_trust_score, trust_level, regulatory_framework
            )

            # Generate summary
            summary_text = self._generate_trust_summary(
                overall_trust_score, trust_level, strengths, weaknesses
            )

            # Create detailed dimension breakdown
            dimension_details = {
                'explainability': {
                    'score': explainability_score,
                    'has_explanations': self._has_explanations(model_id),
                    'explanation_coverage': self._get_explanation_coverage(model_id)
                },
                'fairness': {
                    'score': fairness_score,
                    'has_bias_reports': self._has_bias_reports(model_id),
                    'compliant': self._is_bias_compliant(model_id)
                },
                'robustness': {
                    'score': robustness_score,
                    'estimated': True  # Placeholder
                },
                'privacy': {
                    'score': privacy_score,
                    'estimated': True  # Placeholder
                }
            }

            # Create trust metric record
            metric_data = {
                'model_id': model_id,
                'model_name': model_name,
                'explainability_score': explainability_score,
                'fairness_score': fairness_score,
                'robustness_score': robustness_score,
                'privacy_score': privacy_score,
                'transparency_score': transparency_score,
                'accountability_score': accountability_score,
                'overall_trust_score': overall_trust_score,
                'trust_level': trust_level,
                'dimension_details': dimension_details,
                'weights': weights,
                'assessment_type': assessment_type,
                'regulatory_framework': regulatory_framework,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'recommendations': recommendations,
                'certification_status': certification_status,
                'previous_score': previous_score,
                'score_trend': score_trend,
                'changes_since_last': changes_since_last,
                'summary_text': summary_text,
                'model_version': model_version,
                'environment': environment,
                'assessed_by': assessed_by
            }

            return self.trust_repo.create(metric_data)

        except Exception as e:
            logger.error(f"Error in trust assessment: {str(e)}")
            raise

    def _assess_explainability(self, model_id: str) -> float:
        """Assess explainability dimension."""
        try:
            # Check for existence of explanations
            recent_explanations = self.explanation_repo.get_recent_explanations(
                hours=720,  # 30 days
                model_id=model_id
            )

            if not recent_explanations:
                return 0.3  # Base score for models without explanations

            # Score based on:
            # - Number of explanations
            # - Types of explanations (SHAP, LIME, etc.)
            # - Coverage (global + local)

            explanation_types = set(exp.explanation_type for exp in recent_explanations)
            has_global = any(exp.scope == 'global' for exp in recent_explanations)
            has_local = any(exp.scope == 'local' for exp in recent_explanations)

            score = 0.5  # Base score for having any explanations

            # Bonus for multiple explanation types
            if len(explanation_types) >= 2:
                score += 0.2
            elif len(explanation_types) == 1:
                score += 0.1

            # Bonus for both global and local explanations
            if has_global and has_local:
                score += 0.2
            elif has_global or has_local:
                score += 0.1

            # Bonus for recent activity
            if len(recent_explanations) >= 10:
                score += 0.1

            return min(score, 1.0)

        except Exception as e:
            logger.warning(f"Error assessing explainability: {e}")
            return 0.5  # Default neutral score

    def _assess_fairness(self, model_id: str) -> float:
        """Assess fairness dimension."""
        try:
            # Check for bias reports
            latest_report = self.bias_repo.get_latest_by_model(model_id)

            if not latest_report:
                return 0.5  # Neutral score without bias assessment

            # Use fairness score from bias report
            fairness_score = latest_report.overall_fairness_score

            # Penalize if non-compliant
            if not latest_report.compliant:
                fairness_score *= 0.8

            # Penalize based on severity
            severity_penalty = {
                'low': 1.0,
                'medium': 0.9,
                'high': 0.7,
                'critical': 0.5
            }
            penalty = severity_penalty.get(latest_report.severity, 0.8)
            fairness_score *= penalty

            return min(max(fairness_score, 0.0), 1.0)

        except Exception as e:
            logger.warning(f"Error assessing fairness: {e}")
            return 0.5

    def _assess_robustness(self, model_id: str) -> float:
        """Assess robustness dimension (placeholder)."""
        # This would integrate with adversarial testing, performance monitoring, etc.
        # For now, return a reasonable default
        return 0.7

    def _assess_privacy(self, model_id: str) -> float:
        """Assess privacy dimension (placeholder)."""
        # This would check for differential privacy, data anonymization, etc.
        # For now, return a reasonable default
        return 0.75

    def _assess_transparency(self, model_id: str) -> float:
        """Assess transparency dimension."""
        # Check for documentation, model cards, etc.
        # Placeholder implementation
        return 0.7

    def _assess_accountability(self, model_id: str) -> float:
        """Assess accountability dimension."""
        # Check for audit trails, governance processes, etc.
        # Placeholder implementation
        return 0.7

    def _has_explanations(self, model_id: str) -> bool:
        """Check if model has explanations."""
        explanations = self.explanation_repo.get_by_model_id(model_id, limit=1)
        return len(explanations) > 0

    def _get_explanation_coverage(self, model_id: str) -> str:
        """Get explanation coverage level."""
        explanations = self.explanation_repo.get_recent_explanations(hours=720, model_id=model_id)
        if len(explanations) >= 10:
            return "high"
        elif len(explanations) >= 3:
            return "medium"
        else:
            return "low"

    def _has_bias_reports(self, model_id: str) -> bool:
        """Check if model has bias reports."""
        reports = self.bias_repo.get_by_model_id(model_id, limit=1)
        return len(reports) > 0

    def _is_bias_compliant(self, model_id: str) -> bool:
        """Check if model is bias compliant."""
        latest_report = self.bias_repo.get_latest_by_model(model_id)
        return latest_report.compliant if latest_report else False

    def _determine_trust_level(self, score: float) -> str:
        """Determine trust level from score."""
        if score >= 0.85:
            return "high"
        elif score >= 0.70:
            return "medium"
        elif score >= 0.50:
            return "low"
        else:
            return "critical"

    def _calculate_trend(
        self,
        current_score: float,
        previous_score: Optional[float]
    ) -> str:
        """Calculate score trend."""
        if previous_score is None:
            return "stable"

        diff = current_score - previous_score
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"

    def _generate_trust_recommendations(
        self,
        dimension_scores: Dict[str, float],
        weaknesses: List[str],
        regulatory_framework: Optional[str]
    ) -> List[str]:
        """Generate trust improvement recommendations."""
        recommendations = []

        if 'explainability' in weaknesses:
            recommendations.append("Implement SHAP or LIME explanations for model decisions")
            recommendations.append("Create model documentation and interpretation guides")

        if 'fairness' in weaknesses:
            recommendations.append("Conduct comprehensive bias assessment across protected groups")
            recommendations.append("Apply fairness constraints during model training")

        if 'robustness' in weaknesses:
            recommendations.append("Perform adversarial testing to identify vulnerabilities")
            recommendations.append("Implement model monitoring for performance degradation")

        if 'privacy' in weaknesses:
            recommendations.append("Apply differential privacy techniques")
            recommendations.append("Review data handling and storage practices")

        if regulatory_framework == 'EU_AI_Act':
            recommendations.append("Ensure compliance with EU AI Act high-risk system requirements")
            recommendations.append("Maintain comprehensive technical documentation")

        if not recommendations:
            recommendations.append("Maintain current trust practices")
            recommendations.append("Continue regular trust assessments")

        return recommendations

    def _determine_certification(
        self,
        score: float,
        trust_level: str,
        regulatory_framework: Optional[str]
    ) -> str:
        """Determine certification status."""
        if trust_level == "high" and score >= 0.85:
            return "certified"
        elif trust_level in ["medium", "high"]:
            return "pending"
        else:
            return "not_certified"

    def _generate_trust_summary(
        self,
        score: float,
        level: str,
        strengths: List[str],
        weaknesses: List[str]
    ) -> str:
        """Generate trust assessment summary."""
        summary = f"""
Trust Assessment Summary
========================

Overall Trust Score: {score:.2f}/1.00
Trust Level: {level.upper()}

Strengths: {', '.join(strengths) if strengths else 'None identified'}
Weaknesses: {', '.join(weaknesses) if weaknesses else 'None identified'}

"""

        if level == "high":
            summary += "This model demonstrates high trustworthiness across key dimensions. "
            summary += "Continue maintaining these standards."
        elif level == "medium":
            summary += "This model shows moderate trustworthiness. "
            summary += "Address identified weaknesses to improve trust."
        else:
            summary += "This model has significant trust concerns that require immediate attention. "
            summary += "Implement recommended improvements before production deployment."

        return summary

    def get_trust_metric(self, metric_id: str) -> Optional[TrustMetric]:
        """Get trust metric by ID."""
        return self.trust_repo.get_by_id(metric_id)

    def get_model_trust_history(
        self,
        model_id: str,
        days: int = 90
    ) -> List[TrustMetric]:
        """Get trust score history for a model."""
        return self.trust_repo.get_trust_history(model_id, days)

    def get_low_trust_models(
        self,
        threshold: float = 0.6,
        environment: Optional[str] = None
    ) -> List[TrustMetric]:
        """Get models with low trust scores."""
        return self.trust_repo.get_low_trust_models(threshold, environment)

    def get_trust_stats(
        self,
        environment: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get trust statistics."""
        return self.trust_repo.get_trust_stats(environment, hours)

    def delete_trust_metric(self, metric_id: str) -> bool:
        """Delete a trust metric."""
        return self.trust_repo.delete(metric_id)
