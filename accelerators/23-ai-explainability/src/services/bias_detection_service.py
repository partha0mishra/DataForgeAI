"""Service for detecting bias and assessing fairness in AI models."""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from datetime import datetime
import time
import logging

from sqlalchemy.orm import Session

from src.repositories.bias_report_repository import BiasReportRepository
from src.models.bias_report import BiasReport

# Try to import fairness libraries
try:
    from fairlearn.metrics import (
        demographic_parity_difference,
        demographic_parity_ratio,
        equalized_odds_difference,
        MetricFrame
    )
    FAIRLEARN_AVAILABLE = True
except ImportError:
    FAIRLEARN_AVAILABLE = False

try:
    from aif360.datasets import BinaryLabelDataset
    from aif360.metrics import BinaryLabelDatasetMetric, ClassificationMetric
    AIF360_AVAILABLE = True
except ImportError:
    AIF360_AVAILABLE = False

logger = logging.getLogger(__name__)


class BiasDetectionService:
    """Service for bias detection and fairness assessment."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.bias_repo = BiasReportRepository(db)

    def analyze_bias(
        self,
        model: Any,
        X: np.ndarray,
        y_true: np.ndarray,
        y_pred: Optional[np.ndarray],
        protected_attributes: List[str],
        sensitive_features: np.ndarray,
        model_id: Optional[str] = None,
        model_name: Optional[str] = None,
        reference_group: Optional[str] = None,
        metrics: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> BiasReport:
        """
        Analyze bias in model predictions.

        Args:
            model: The ML model to analyze
            X: Feature data
            y_true: True labels
            y_pred: Predicted labels (if None, will be generated)
            protected_attributes: Names of protected attributes
            sensitive_features: Values of sensitive features
            model_id: Model identifier
            model_name: Model name
            reference_group: Reference group for comparison
            metrics: List of fairness metrics to compute
            created_by: User who requested analysis

        Returns:
            BiasReport object with fairness metrics
        """
        if not FAIRLEARN_AVAILABLE:
            logger.warning("Fairlearn not available, using simplified bias detection")
            return self._simplified_bias_analysis(
                model, X, y_true, y_pred, protected_attributes, sensitive_features,
                model_id, model_name, created_by
            )

        start_time = time.time()

        try:
            # Generate predictions if not provided
            if y_pred is None:
                if hasattr(model, 'predict'):
                    y_pred = model.predict(X)
                else:
                    raise ValueError("Model must have predict method or predictions must be provided")

            if metrics is None:
                metrics = ['demographic_parity', 'equalized_odds', 'calibration']

            # Calculate bias metrics
            bias_metrics = {}
            group_statistics = {}

            # Demographic Parity
            if 'demographic_parity' in metrics:
                dp_diff = demographic_parity_difference(
                    y_true, y_pred, sensitive_features=sensitive_features
                )
                dp_ratio = demographic_parity_ratio(
                    y_true, y_pred, sensitive_features=sensitive_features
                )

                bias_metrics['demographic_parity'] = {
                    'difference': float(dp_diff),
                    'ratio': float(dp_ratio)
                }

            # Equalized Odds
            if 'equalized_odds' in metrics:
                eo_diff = equalized_odds_difference(
                    y_true, y_pred, sensitive_features=sensitive_features
                )

                bias_metrics['equalized_odds'] = {
                    'difference': float(eo_diff)
                }

            # Per-group statistics using MetricFrame
            from sklearn.metrics import accuracy_score, precision_score, recall_score

            metric_frame = MetricFrame(
                metrics={
                    'accuracy': accuracy_score,
                    'precision': lambda yt, yp: precision_score(yt, yp, average='binary', zero_division=0),
                    'recall': lambda yt, yp: recall_score(yt, yp, average='binary', zero_division=0)
                },
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_features
            )

            # Convert group statistics to dict
            for group in metric_frame.by_group.index:
                group_key = str(group)
                group_statistics[group_key] = {
                    'accuracy': float(metric_frame.by_group.loc[group, 'accuracy']),
                    'precision': float(metric_frame.by_group.loc[group, 'precision']),
                    'recall': float(metric_frame.by_group.loc[group, 'recall'])
                }

            # Group distributions
            unique, counts = np.unique(sensitive_features, return_counts=True)
            group_distributions = {str(u): int(c) for u, c in zip(unique, counts)}

            # Disparate Impact Ratio (80% rule)
            disparate_impact = self._calculate_disparate_impact(y_pred, sensitive_features)

            # Calculate overall fairness score
            overall_fairness_score = self._calculate_fairness_score(bias_metrics, disparate_impact)

            # Detect issues
            issues_detected = self._detect_issues(bias_metrics, disparate_impact, group_statistics)

            # Generate recommendations
            recommendations = self._generate_recommendations(issues_detected, bias_metrics)

            # Determine severity and compliance
            severity = self._determine_severity(overall_fairness_score, len(issues_detected))
            compliant = overall_fairness_score >= 0.7 and disparate_impact >= 0.8

            # Generate summary
            summary_text = self._generate_bias_summary(
                overall_fairness_score, compliant, len(issues_detected), protected_attributes
            )

            analysis_duration = (time.time() - start_time) * 1000

            # Create bias report
            report_data = {
                'model_id': model_id or 'unknown',
                'model_name': model_name,
                'protected_attributes': protected_attributes,
                'reference_group': reference_group,
                'metrics_analyzed': metrics,
                'bias_metrics': bias_metrics,
                'overall_fairness_score': overall_fairness_score,
                'compliant': compliant,
                'issues_detected': issues_detected,
                'recommendations': recommendations,
                'severity': severity,
                'group_statistics': group_statistics,
                'disparate_impact_ratio': disparate_impact,
                'dataset_size': len(X),
                'group_distributions': group_distributions,
                'summary_text': summary_text,
                'analysis_duration_ms': analysis_duration,
                'created_by': created_by
            }

            return self.bias_repo.create(report_data)

        except Exception as e:
            logger.error(f"Error in bias analysis: {str(e)}")
            raise

    def _simplified_bias_analysis(
        self,
        model: Any,
        X: np.ndarray,
        y_true: np.ndarray,
        y_pred: Optional[np.ndarray],
        protected_attributes: List[str],
        sensitive_features: np.ndarray,
        model_id: Optional[str],
        model_name: Optional[str],
        created_by: Optional[str]
    ) -> BiasReport:
        """Simplified bias analysis when fairness libraries not available."""
        start_time = time.time()

        if y_pred is None:
            y_pred = model.predict(X)

        # Calculate simple metrics per group
        unique_groups = np.unique(sensitive_features)
        group_statistics = {}
        positive_rates = {}

        for group in unique_groups:
            group_mask = sensitive_features == group
            group_pred = y_pred[group_mask]
            group_true = y_true[group_mask]

            # Simple accuracy
            accuracy = np.mean(group_pred == group_true)

            # Positive prediction rate
            positive_rate = np.mean(group_pred == 1) if len(group_pred) > 0 else 0

            group_key = str(group)
            group_statistics[group_key] = {
                'accuracy': float(accuracy),
                'positive_rate': float(positive_rate),
                'count': int(np.sum(group_mask))
            }
            positive_rates[group_key] = positive_rate

        # Simple disparate impact
        if len(positive_rates) >= 2:
            rates = list(positive_rates.values())
            disparate_impact = min(rates) / max(rates) if max(rates) > 0 else 1.0
        else:
            disparate_impact = 1.0

        # Simple fairness score based on group accuracy variance
        accuracies = [stats['accuracy'] for stats in group_statistics.values()]
        fairness_score = 1.0 - np.std(accuracies)  # Lower variance = higher fairness

        compliant = fairness_score >= 0.7 and disparate_impact >= 0.8
        issues_detected = [] if compliant else ["Potential bias detected in group outcomes"]
        recommendations = ["Consider rebalancing training data", "Review model features for bias"]
        severity = "low" if compliant else "medium"

        analysis_duration = (time.time() - start_time) * 1000

        report_data = {
            'model_id': model_id or 'unknown',
            'model_name': model_name,
            'protected_attributes': protected_attributes,
            'metrics_analyzed': ['accuracy', 'positive_rate'],
            'bias_metrics': {'group_statistics': group_statistics},
            'overall_fairness_score': fairness_score,
            'compliant': compliant,
            'issues_detected': issues_detected,
            'recommendations': recommendations,
            'severity': severity,
            'group_statistics': group_statistics,
            'disparate_impact_ratio': disparate_impact,
            'dataset_size': len(X),
            'summary_text': f"Simplified bias analysis completed. Fairness score: {fairness_score:.2f}",
            'analysis_duration_ms': analysis_duration,
            'created_by': created_by
        }

        return self.bias_repo.create(report_data)

    def _calculate_disparate_impact(
        self,
        y_pred: np.ndarray,
        sensitive_features: np.ndarray
    ) -> float:
        """Calculate disparate impact ratio (80% rule)."""
        unique_groups = np.unique(sensitive_features)
        if len(unique_groups) < 2:
            return 1.0

        positive_rates = []
        for group in unique_groups:
            group_mask = sensitive_features == group
            group_pred = y_pred[group_mask]
            if len(group_pred) > 0:
                positive_rate = np.mean(group_pred == 1)
                positive_rates.append(positive_rate)

        if len(positive_rates) < 2 or max(positive_rates) == 0:
            return 1.0

        return min(positive_rates) / max(positive_rates)

    def _calculate_fairness_score(
        self,
        bias_metrics: Dict[str, Any],
        disparate_impact: float
    ) -> float:
        """Calculate overall fairness score (0-1, higher is better)."""
        scores = []

        # Demographic parity contribution
        if 'demographic_parity' in bias_metrics:
            dp_diff = abs(bias_metrics['demographic_parity'].get('difference', 0))
            dp_score = max(0, 1.0 - dp_diff)
            scores.append(dp_score)

        # Equalized odds contribution
        if 'equalized_odds' in bias_metrics:
            eo_diff = abs(bias_metrics['equalized_odds'].get('difference', 0))
            eo_score = max(0, 1.0 - eo_diff)
            scores.append(eo_score)

        # Disparate impact contribution
        di_score = disparate_impact
        scores.append(di_score)

        return sum(scores) / len(scores) if scores else 0.5

    def _detect_issues(
        self,
        bias_metrics: Dict[str, Any],
        disparate_impact: float,
        group_statistics: Dict[str, Any]
    ) -> List[str]:
        """Detect specific bias issues."""
        issues = []

        # Check disparate impact (80% rule)
        if disparate_impact < 0.8:
            issues.append(f"Disparate impact violation: {disparate_impact:.2f} < 0.80")

        # Check demographic parity
        if 'demographic_parity' in bias_metrics:
            dp_diff = abs(bias_metrics['demographic_parity'].get('difference', 0))
            if dp_diff > 0.1:
                issues.append(f"Demographic parity difference: {dp_diff:.2f} > 0.10")

        # Check equalized odds
        if 'equalized_odds' in bias_metrics:
            eo_diff = abs(bias_metrics['equalized_odds'].get('difference', 0))
            if eo_diff > 0.1:
                issues.append(f"Equalized odds difference: {eo_diff:.2f} > 0.10")

        # Check performance disparities across groups
        if group_statistics:
            accuracies = [stats.get('accuracy', 0) for stats in group_statistics.values()]
            if max(accuracies) - min(accuracies) > 0.1:
                issues.append(f"Large accuracy disparity across groups: {max(accuracies) - min(accuracies):.2f}")

        return issues

    def _generate_recommendations(
        self,
        issues: List[str],
        bias_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on detected issues."""
        recommendations = []

        if not issues:
            recommendations.append("No significant bias detected. Continue monitoring.")
            return recommendations

        if any("Disparate impact" in issue for issue in issues):
            recommendations.append("Consider rebalancing training data to ensure equal representation")
            recommendations.append("Review feature selection for potentially biased variables")

        if any("Demographic parity" in issue for issue in issues):
            recommendations.append("Apply fairness constraints during model training")
            recommendations.append("Consider post-processing adjustments to equalize positive rates")

        if any("Equalized odds" in issue for issue in issues):
            recommendations.append("Investigate false positive/negative rates across groups")
            recommendations.append("Consider threshold optimization per group")

        if any("accuracy disparity" in issue for issue in issues):
            recommendations.append("Collect more training data for underperforming groups")
            recommendations.append("Use stratified sampling to ensure balanced evaluation")

        return recommendations

    def _determine_severity(
        self,
        fairness_score: float,
        num_issues: int
    ) -> str:
        """Determine severity level of bias."""
        if fairness_score >= 0.9 and num_issues == 0:
            return "low"
        elif fairness_score >= 0.7 and num_issues <= 2:
            return "medium"
        elif fairness_score >= 0.5:
            return "high"
        else:
            return "critical"

    def _generate_bias_summary(
        self,
        fairness_score: float,
        compliant: bool,
        num_issues: int,
        protected_attributes: List[str]
    ) -> str:
        """Generate executive summary of bias analysis."""
        compliance_status = "COMPLIANT" if compliant else "NON-COMPLIANT"
        attributes_str = ", ".join(protected_attributes)

        summary = f"""
Bias Analysis Summary
====================

Overall Fairness Score: {fairness_score:.2f}/1.00
Compliance Status: {compliance_status}
Protected Attributes Analyzed: {attributes_str}
Issues Detected: {num_issues}

"""

        if compliant:
            summary += "The model demonstrates acceptable fairness across analyzed groups. "
            summary += "Continue regular monitoring to maintain fairness standards."
        else:
            summary += "The model shows evidence of bias that requires attention. "
            summary += "Review detailed findings and implement recommended mitigations."

        return summary

    def get_report_by_id(self, report_id: str) -> Optional[BiasReport]:
        """Get bias report by ID."""
        return self.bias_repo.get_by_id(report_id)

    def get_model_reports(
        self,
        model_id: str,
        limit: int = 50
    ) -> List[BiasReport]:
        """Get all bias reports for a model."""
        return self.bias_repo.get_by_model_id(model_id, limit)

    def get_latest_report(self, model_id: str) -> Optional[BiasReport]:
        """Get the most recent bias report for a model."""
        return self.bias_repo.get_latest_by_model(model_id)

    def get_non_compliant_models(
        self,
        severity: Optional[str] = None,
        hours: Optional[int] = None
    ) -> List[BiasReport]:
        """Get non-compliant bias reports."""
        return self.bias_repo.get_non_compliant_reports(severity, hours)

    def get_bias_stats(
        self,
        model_id: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get bias report statistics."""
        return self.bias_repo.get_report_stats(model_id, hours)

    def delete_report(self, report_id: str) -> bool:
        """Delete a bias report."""
        return self.bias_repo.delete(report_id)
