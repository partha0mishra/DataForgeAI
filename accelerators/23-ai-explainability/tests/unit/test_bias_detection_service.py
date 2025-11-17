"""Unit tests for BiasDetectionService."""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.services.bias_detection_service import BiasDetectionService


class TestBiasDetectionService:
    """Test cases for BiasDetectionService."""

    def test_service_initialization(self, test_db):
        """Test service initialization."""
        service = BiasDetectionService(test_db)

        assert service.db == test_db
        assert service.bias_repo is not None

    @patch('src.services.bias_detection_service.FAIRLEARN_AVAILABLE', False)
    def test_simplified_bias_analysis(self, test_db, mock_model, sample_data):
        """Test simplified bias analysis when Fairlearn is not available."""
        service = BiasDetectionService(test_db)

        X = sample_data['X']
        y_true = sample_data['y']
        y_pred = np.array([0, 0, 1, 1])
        sensitive_features = sample_data['sensitive_features']

        report = service.analyze_bias(
            model=mock_model,
            X=X,
            y_true=y_true,
            y_pred=y_pred,
            protected_attributes=['group'],
            sensitive_features=sensitive_features,
            model_id='test-model',
            created_by='test_user'
        )

        assert report is not None
        assert report.model_id == 'test-model'
        assert report.overall_fairness_score is not None
        assert 0 <= report.overall_fairness_score <= 1
        assert report.disparate_impact_ratio is not None

    def test_calculate_disparate_impact(self, test_db):
        """Test disparate impact calculation."""
        service = BiasDetectionService(test_db)

        y_pred = np.array([1, 1, 0, 0, 1, 0])
        sensitive_features = np.array(['A', 'A', 'A', 'B', 'B', 'B'])

        di_ratio = service._calculate_disparate_impact(y_pred, sensitive_features)

        assert di_ratio is not None
        assert 0 <= di_ratio <= 1

    def test_calculate_fairness_score(self, test_db):
        """Test fairness score calculation."""
        service = BiasDetectionService(test_db)

        bias_metrics = {
            'demographic_parity': {'difference': 0.05, 'ratio': 0.95},
            'equalized_odds': {'difference': 0.08}
        }
        disparate_impact = 0.85

        fairness_score = service._calculate_fairness_score(bias_metrics, disparate_impact)

        assert 0 <= fairness_score <= 1

    def test_detect_issues(self, test_db):
        """Test bias issue detection."""
        service = BiasDetectionService(test_db)

        bias_metrics = {
            'demographic_parity': {'difference': 0.15},  # > 0.10 threshold
            'equalized_odds': {'difference': 0.12}  # > 0.10 threshold
        }
        disparate_impact = 0.75  # < 0.80 threshold
        group_statistics = {
            'A': {'accuracy': 0.9},
            'B': {'accuracy': 0.6}  # Large disparity
        }

        issues = service._detect_issues(bias_metrics, disparate_impact, group_statistics)

        assert len(issues) >= 1
        assert any('Disparate impact' in issue for issue in issues)

    def test_generate_recommendations(self, test_db):
        """Test recommendation generation."""
        service = BiasDetectionService(test_db)

        issues = [
            'Disparate impact violation',
            'Demographic parity difference > 0.10'
        ]
        bias_metrics = {'demographic_parity': {'difference': 0.15}}

        recommendations = service._generate_recommendations(issues, bias_metrics)

        assert len(recommendations) > 0
        assert any('rebalancing' in rec.lower() for rec in recommendations)

    def test_determine_severity(self, test_db):
        """Test severity determination."""
        service = BiasDetectionService(test_db)

        # High fairness, no issues
        severity_low = service._determine_severity(fairness_score=0.95, num_issues=0)
        assert severity_low == 'low'

        # Low fairness, many issues
        severity_high = service._determine_severity(fairness_score=0.45, num_issues=5)
        assert severity_high in ['high', 'critical']

    def test_get_latest_report(self, test_db, sample_bias_report):
        """Test getting latest bias report."""
        service = BiasDetectionService(test_db)

        report = service.get_latest_report('test-model-1')

        assert report is not None
        assert report.model_id == 'test-model-1'

    def test_get_non_compliant_models(self, test_db):
        """Test getting non-compliant models."""
        service = BiasDetectionService(test_db)

        # Create non-compliant report
        service.bias_repo.create({
            'model_id': 'bad-model',
            'protected_attributes': ['gender'],
            'metrics_analyzed': ['demographic_parity'],
            'bias_metrics': {},
            'overall_fairness_score': 0.45,
            'compliant': False,
            'severity': 'high'
        })

        non_compliant = service.get_non_compliant_models()

        assert len(non_compliant) >= 1
        assert all(not report.compliant for report in non_compliant)

    def test_get_bias_stats(self, test_db, sample_bias_report):
        """Test getting bias statistics."""
        service = BiasDetectionService(test_db)

        stats = service.get_bias_stats()

        assert stats['total_reports'] >= 1
        assert 'compliant_count' in stats
        assert 'compliance_rate' in stats
        assert stats['avg_fairness_score'] >= 0
