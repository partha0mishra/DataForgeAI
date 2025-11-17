"""Unit tests for DriftService."""
import pytest
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.services.drift_service import DriftService
from src.models.drift_detection import DriftDetection
from src.models.ml_model import MLModel
from src.models.deployment import Deployment


class TestDriftService:
    """Test cases for DriftService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_drift_repo(self):
        """Create mock drift repository."""
        return Mock()

    @pytest.fixture
    def mock_model_repo(self):
        """Create mock model repository."""
        return Mock()

    @pytest.fixture
    def mock_deployment_repo(self):
        """Create mock deployment repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db, mock_drift_repo, mock_model_repo, mock_deployment_repo):
        """Create DriftService with mocked dependencies."""
        service = DriftService(mock_db)
        service.drift_repo = mock_drift_repo
        service.model_repo = mock_model_repo
        service.deployment_repo = mock_deployment_repo
        return service

    @pytest.fixture
    def sample_model(self):
        """Create sample ML model."""
        return MLModel(
            model_id="test-model-1",
            name="fraud_detector",
            version="1.0.0",
            framework="sklearn",
            accuracy=0.95
        )

    @pytest.fixture
    def sample_drift(self):
        """Create sample drift detection."""
        return DriftDetection(
            drift_id="drift-1",
            model_id="test-model-1",
            drift_type="data_drift",
            drift_score=0.15,
            threshold=0.05,
            is_drift_detected=True,
            severity="medium"
        )

    def test_init(self, mock_db):
        """Test service initialization."""
        service = DriftService(mock_db)

        assert service.db == mock_db
        assert service.drift_repo is not None
        assert service.model_repo is not None
        assert service.deployment_repo is not None

    @patch('src.services.drift_service.SCIPY_AVAILABLE', True)
    @patch('src.services.drift_service.stats')
    def test_detect_data_drift_with_scipy(self, mock_stats, service, mock_model_repo, mock_drift_repo, sample_model):
        """Test data drift detection with SciPy available."""
        mock_model_repo.get_by_id.return_value = sample_model

        # Mock K-S test results
        mock_stats.ks_2samp.return_value = (0.2, 0.01)  # High drift

        reference_data = np.random.rand(100, 3)
        current_data = np.random.rand(100, 3)

        created_drift = DriftDetection(
            drift_id="new-drift",
            model_id="test-model-1",
            drift_type="data_drift",
            drift_score=0.2,
            is_drift_detected=True
        )
        mock_drift_repo.create.return_value = created_drift
        mock_drift_repo.mark_auto_retrain_triggered.return_value = None

        result = service.detect_data_drift(
            model_id="test-model-1",
            reference_data=reference_data,
            current_data=current_data,
            feature_names=["feature_0", "feature_1", "feature_2"]
        )

        assert result == created_drift
        mock_drift_repo.create.assert_called_once()
        # K-S test should be called for each feature
        assert mock_stats.ks_2samp.call_count == 3

    @patch('src.services.drift_service.SCIPY_AVAILABLE', False)
    def test_detect_data_drift_without_scipy(self, service, mock_model_repo, mock_drift_repo, sample_model):
        """Test data drift detection without SciPy (fallback mode)."""
        mock_model_repo.get_by_id.return_value = sample_model

        reference_data = np.random.rand(100, 3)
        current_data = np.random.rand(100, 3)

        created_drift = DriftDetection(
            drift_id="new-drift",
            model_id="test-model-1",
            drift_type="data_drift",
            drift_score=0.1,
            is_drift_detected=False
        )
        mock_drift_repo.create.return_value = created_drift

        result = service.detect_data_drift(
            model_id="test-model-1",
            reference_data=reference_data,
            current_data=current_data
        )

        assert result == created_drift
        mock_drift_repo.create.assert_called_once()

    def test_detect_data_drift_model_not_found(self, service, mock_model_repo):
        """Test drift detection with non-existent model."""
        mock_model_repo.get_by_id.return_value = None

        reference_data = np.random.rand(100, 3)
        current_data = np.random.rand(100, 3)

        with pytest.raises(ValueError, match="not found"):
            service.detect_data_drift(
                model_id="non-existent",
                reference_data=reference_data,
                current_data=current_data
            )

    def test_detect_data_drift_shape_mismatch(self, service, mock_model_repo, sample_model):
        """Test drift detection with mismatched data shapes."""
        mock_model_repo.get_by_id.return_value = sample_model

        reference_data = np.random.rand(100, 3)
        current_data = np.random.rand(100, 5)  # Different shape

        with pytest.raises(ValueError, match="same number of features"):
            service.detect_data_drift(
                model_id="test-model-1",
                reference_data=reference_data,
                current_data=current_data
            )

    @patch('src.services.drift_service.SCIPY_AVAILABLE', True)
    @patch('src.services.drift_service.stats')
    def test_detect_data_drift_high_severity_triggers_retrain(self, mock_stats, service, mock_model_repo, mock_drift_repo, sample_model):
        """Test that high severity drift triggers auto-retrain."""
        mock_model_repo.get_by_id.return_value = sample_model

        # Mock K-S test showing severe drift (high statistic, low p-value)
        mock_stats.ks_2samp.return_value = (0.8, 0.001)

        reference_data = np.random.rand(100, 2)
        current_data = np.random.rand(100, 2)

        created_drift = DriftDetection(
            drift_id="high-drift",
            model_id="test-model-1",
            drift_type="data_drift",
            drift_score=0.8,
            is_drift_detected=True,
            severity="high"
        )
        mock_drift_repo.create.return_value = created_drift
        mock_drift_repo.mark_auto_retrain_triggered.return_value = created_drift

        result = service.detect_data_drift(
            model_id="test-model-1",
            reference_data=reference_data,
            current_data=current_data
        )

        # Auto-retrain should be triggered for high severity
        mock_drift_repo.mark_auto_retrain_triggered.assert_called_once_with("high-drift")

    @patch('src.services.drift_service.SCIPY_AVAILABLE', True)
    @patch('src.services.drift_service.stats')
    def test_detect_prediction_drift_with_scipy(self, mock_stats, service, mock_model_repo, mock_drift_repo, sample_model):
        """Test prediction drift detection with SciPy."""
        mock_model_repo.get_by_id.return_value = sample_model

        # Mock K-S test
        mock_stats.ks_2samp.return_value = (0.15, 0.02)

        reference_predictions = np.random.rand(100)
        current_predictions = np.random.rand(100)

        created_drift = DriftDetection(
            drift_id="pred-drift",
            model_id="test-model-1",
            drift_type="prediction_drift",
            drift_score=0.15,
            is_drift_detected=True
        )
        mock_drift_repo.create.return_value = created_drift

        result = service.detect_prediction_drift(
            model_id="test-model-1",
            reference_predictions=reference_predictions,
            current_predictions=current_predictions
        )

        assert result == created_drift
        mock_drift_repo.create.assert_called_once()
        mock_stats.ks_2samp.assert_called_once()

    @patch('src.services.drift_service.SCIPY_AVAILABLE', False)
    def test_detect_prediction_drift_without_scipy(self, service, mock_model_repo, mock_drift_repo, sample_model):
        """Test prediction drift detection without SciPy."""
        mock_model_repo.get_by_id.return_value = sample_model

        reference_predictions = np.random.rand(100)
        current_predictions = np.random.rand(100)

        created_drift = DriftDetection(
            drift_id="pred-drift",
            model_id="test-model-1",
            drift_type="prediction_drift",
            drift_score=0.1,
            is_drift_detected=False
        )
        mock_drift_repo.create.return_value = created_drift

        result = service.detect_prediction_drift(
            model_id="test-model-1",
            reference_predictions=reference_predictions,
            current_predictions=current_predictions
        )

        assert result == created_drift
        mock_drift_repo.create.assert_called_once()

    def test_detect_concept_drift(self, service, mock_model_repo, mock_drift_repo, sample_model):
        """Test concept drift detection (performance degradation)."""
        mock_model_repo.get_by_id.return_value = sample_model

        true_labels = np.array([1, 0, 1, 1, 0, 1, 0, 0, 1, 1])
        predictions = np.array([1, 0, 0, 1, 0, 1, 1, 0, 1, 0])  # 70% accuracy
        historical_accuracy = 0.95  # Significant drop from 95%

        created_drift = DriftDetection(
            drift_id="concept-drift",
            model_id="test-model-1",
            drift_type="concept_drift",
            drift_score=0.25,  # 25% drop
            is_drift_detected=True
        )
        mock_drift_repo.create.return_value = created_drift
        mock_drift_repo.mark_auto_retrain_triggered.return_value = created_drift

        result = service.detect_concept_drift(
            model_id="test-model-1",
            true_labels=true_labels,
            predictions=predictions,
            historical_accuracy=historical_accuracy
        )

        assert result == created_drift
        mock_drift_repo.create.assert_called_once()

    def test_simple_drift_score(self, service):
        """Test simple drift score calculation (fallback method)."""
        reference_data = np.array([[1.0, 2.0], [1.5, 2.5], [1.2, 2.2]])
        current_data = np.array([[2.0, 3.0], [2.5, 3.5], [2.2, 3.2]])

        score = service._simple_drift_score(reference_data, current_data)

        # Score should be a float between 0 and 1
        assert isinstance(score, (float, np.floating))
        assert 0 <= score <= 1

    def test_calculate_severity_high(self, service):
        """Test severity calculation - high severity."""
        severity = service._calculate_severity(drift_score=0.7, affected_count=8, total_count=10)
        assert severity == "high"

    def test_calculate_severity_medium(self, service):
        """Test severity calculation - medium severity."""
        severity = service._calculate_severity(drift_score=0.4, affected_count=3, total_count=10)
        assert severity == "medium"

    def test_calculate_severity_low(self, service):
        """Test severity calculation - low severity."""
        severity = service._calculate_severity(drift_score=0.2, affected_count=1, total_count=10)
        assert severity == "low"

    def test_generate_drift_recommendations_high_severity(self, service):
        """Test drift recommendations for high severity."""
        recommendations = service._generate_drift_recommendations(
            is_drift_detected=True,
            severity="high",
            affected_features=[{"name": "feature1"}, {"name": "feature2"}]
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should recommend immediate action for high severity
        assert any("immediate" in rec.lower() or "retrain" in rec.lower() for rec in recommendations)

    def test_generate_drift_recommendations_no_drift(self, service):
        """Test drift recommendations when no drift detected."""
        recommendations = service._generate_drift_recommendations(
            is_drift_detected=False,
            severity="low",
            affected_features=[]
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) >= 0

    def test_get_drift_summary(self, service, mock_drift_repo):
        """Test getting drift summary for model."""
        sample_drifts = [
            DriftDetection(
                drift_id="drift-1",
                model_id="test-model-1",
                drift_type="data_drift",
                drift_score=0.15,
                is_drift_detected=True,
                severity="medium"
            ),
            DriftDetection(
                drift_id="drift-2",
                model_id="test-model-1",
                drift_type="prediction_drift",
                drift_score=0.25,
                is_drift_detected=True,
                severity="high"
            )
        ]

        mock_drift_repo.get_drift_statistics.return_value = {
            "total_detections": 10,
            "drift_detected_count": 5,
            "drift_rate_percentage": 50.0
        }
        mock_drift_repo.get_by_model.return_value = sample_drifts

        result = service.get_drift_summary(model_id="test-model-1", hours=24)

        assert "statistics" in result
        assert "recent_detections" in result
        mock_drift_repo.get_drift_statistics.assert_called_once()
        mock_drift_repo.get_by_model.assert_called_once()

    def test_monitor_deployment_drift(self, service, mock_deployment_repo, mock_drift_repo):
        """Test monitoring drift for a deployment."""
        deployment = Deployment(
            deployment_id="deploy-1",
            model_id="test-model-1",
            deployment_name="test-deploy",
            environment="production",
            status="running",
            health_status="healthy"
        )

        sample_drifts = [
            DriftDetection(
                drift_id="drift-1",
                model_id="test-model-1",
                deployment_id="deploy-1",
                drift_type="data_drift",
                drift_score=0.15,
                is_drift_detected=True,
                severity="medium"
            )
        ]

        mock_deployment_repo.get_by_id.return_value = deployment
        mock_drift_repo.get_by_deployment.return_value = sample_drifts
        mock_drift_repo.get_drift_statistics.return_value = {
            "total_detections": 5,
            "drift_detected_count": 2
        }

        result = service.monitor_deployment_drift(deployment_id="deploy-1", hours=24)

        assert result["deployment"]["deployment_id"] == "deploy-1"
        assert "drift_detections" in result
        assert "drift_statistics" in result
        mock_deployment_repo.get_by_id.assert_called_once()

    def test_monitor_deployment_drift_not_found(self, service, mock_deployment_repo):
        """Test monitoring drift for non-existent deployment."""
        mock_deployment_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            service.monitor_deployment_drift(deployment_id="non-existent")

    def test_get_health_recommendation_healthy(self, service):
        """Test health recommendation for healthy deployment."""
        recommendation = service._get_health_recommendation(drift_rate=10.0)

        assert "healthy" in recommendation.lower() or "good" in recommendation.lower()

    def test_get_health_recommendation_warning(self, service):
        """Test health recommendation for warning state."""
        recommendation = service._get_health_recommendation(drift_rate=35.0)

        assert "monitor" in recommendation.lower() or "warning" in recommendation.lower()

    def test_get_health_recommendation_critical(self, service):
        """Test health recommendation for critical state."""
        recommendation = service._get_health_recommendation(drift_rate=60.0)

        assert "action" in recommendation.lower() or "critical" in recommendation.lower()

    def test_trigger_auto_retrain(self, service, mock_drift_repo, sample_drift):
        """Test triggering auto-retrain."""
        mock_drift_repo.mark_auto_retrain_triggered.return_value = sample_drift

        # Should not raise exception
        service._trigger_auto_retrain(sample_drift)

        mock_drift_repo.mark_auto_retrain_triggered.assert_called_once_with("drift-1")

    @patch('src.services.drift_service.SCIPY_AVAILABLE', True)
    @patch('src.services.drift_service.stats')
    def test_detect_data_drift_with_deployment_id(self, mock_stats, service, mock_model_repo, mock_drift_repo, sample_model):
        """Test data drift detection with deployment ID."""
        mock_model_repo.get_by_id.return_value = sample_model
        mock_stats.ks_2samp.return_value = (0.1, 0.3)  # No drift

        reference_data = np.random.rand(50, 2)
        current_data = np.random.rand(50, 2)

        created_drift = DriftDetection(
            drift_id="drift-with-deploy",
            model_id="test-model-1",
            deployment_id="deploy-1",
            drift_type="data_drift",
            drift_score=0.1,
            is_drift_detected=False
        )
        mock_drift_repo.create.return_value = created_drift

        result = service.detect_data_drift(
            model_id="test-model-1",
            reference_data=reference_data,
            current_data=current_data,
            deployment_id="deploy-1"
        )

        # Verify deployment_id was passed to created drift
        assert result.deployment_id == "deploy-1"
