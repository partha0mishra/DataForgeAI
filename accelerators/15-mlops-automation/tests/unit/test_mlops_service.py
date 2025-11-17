"""Unit tests for MLOpsService."""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from src.services.mlops_service import MLOpsService
from src.models.ml_model import MLModel
from src.models.deployment import Deployment


class TestMLOpsService:
    """Test cases for MLOpsService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_model_repo(self):
        """Create mock model repository."""
        return Mock()

    @pytest.fixture
    def mock_deployment_repo(self):
        """Create mock deployment repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db, mock_model_repo, mock_deployment_repo):
        """Create MLOpsService with mocked dependencies."""
        service = MLOpsService(mock_db)
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
            status="registered",
            accuracy=0.95,
            precision=0.92
        )

    @pytest.fixture
    def sample_deployment(self):
        """Create sample deployment."""
        return Deployment(
            deployment_id="test-deploy-1",
            model_id="test-model-1",
            deployment_name="fraud-staging",
            environment="staging",
            strategy="rolling",
            status="running"
        )

    def test_init(self, mock_db):
        """Test service initialization."""
        service = MLOpsService(mock_db)

        assert service.db == mock_db
        assert service.model_repo is not None
        assert service.deployment_repo is not None

    def test_register_model_success(self, service, mock_model_repo):
        """Test successful model registration."""
        mock_model_repo.get_by_name_and_version.return_value = None
        mock_model_repo.create.return_value = MLModel(
            model_id="new-model",
            name="test_model",
            version="1.0.0",
            framework="sklearn",
            status="registered"
        )

        result = service.register_model(
            name="test_model",
            version="1.0.0",
            framework="sklearn",
            algorithm="random_forest",
            metrics={"accuracy": 0.95, "custom_metric": 0.88}
        )

        assert result.name == "test_model"
        assert result.version == "1.0.0"
        mock_model_repo.create.assert_called_once()

    def test_register_model_duplicate_version(self, service, mock_model_repo, sample_model):
        """Test registering duplicate model version."""
        mock_model_repo.get_by_name_and_version.return_value = sample_model

        with pytest.raises(ValueError, match="already exists"):
            service.register_model(
                name="fraud_detector",
                version="1.0.0",
                framework="sklearn"
            )

    def test_register_model_with_all_metrics(self, service, mock_model_repo):
        """Test registering model with all metric types."""
        mock_model_repo.get_by_name_and_version.return_value = None
        created_model = Mock()
        mock_model_repo.create.return_value = created_model

        service.register_model(
            name="test_model",
            version="1.0.0",
            framework="tensorflow",
            metrics={
                "accuracy": 0.95,
                "precision": 0.93,
                "recall": 0.94,
                "f1_score": 0.935,
                "auc_roc": 0.97,
                "custom_metric": 0.88
            }
        )

        # Verify create was called
        mock_model_repo.create.assert_called_once()

    def test_promote_to_production_success(self, service, mock_model_repo, sample_model):
        """Test promoting model to production."""
        mock_model_repo.get_by_id.return_value = sample_model
        mock_model_repo.get_production_models.return_value = []
        mock_model_repo.set_production_status.return_value = sample_model

        result = service.promote_to_production("test-model-1")

        assert result == sample_model
        mock_model_repo.set_production_status.assert_called_once_with("test-model-1", True)

    def test_promote_to_production_with_demotion(self, service, mock_model_repo, sample_model):
        """Test promoting model while demoting current production model."""
        # Create production model with same name
        prod_model = MLModel(
            model_id="prod-model",
            name="fraud_detector",
            version="0.9.0",
            framework="sklearn",
            is_production=True
        )

        mock_model_repo.get_by_id.return_value = sample_model
        mock_model_repo.get_production_models.return_value = [prod_model]
        mock_model_repo.set_production_status.return_value = sample_model

        result = service.promote_to_production("test-model-1", demote_current=True)

        # Should demote old production model
        assert mock_model_repo.set_production_status.call_count == 2
        # First call demotes old model
        mock_model_repo.set_production_status.assert_any_call("prod-model", False)
        # Second call promotes new model
        mock_model_repo.set_production_status.assert_any_call("test-model-1", True)

    def test_promote_to_production_model_not_found(self, service, mock_model_repo):
        """Test promoting non-existent model."""
        mock_model_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            service.promote_to_production("non-existent")

    def test_create_deployment_success(self, service, mock_model_repo, mock_deployment_repo, sample_model):
        """Test successful deployment creation."""
        mock_model_repo.get_by_id.return_value = sample_model
        mock_deployment_repo.get_by_name.return_value = None
        created_deployment = Deployment(
            deployment_id="new-deploy",
            model_id="test-model-1",
            deployment_name="test-deployment",
            environment="staging",
            strategy="rolling",
            status="pending"
        )
        mock_deployment_repo.create.return_value = created_deployment
        mock_deployment_repo.update_status.return_value = None
        mock_deployment_repo.update.return_value = None

        result = service.create_deployment(
            model_id="test-model-1",
            deployment_name="test-deployment",
            environment="staging",
            strategy="rolling",
            replicas=3
        )

        assert result.deployment_name == "test-deployment"
        mock_deployment_repo.create.assert_called_once()

    def test_create_deployment_invalid_environment(self, service, mock_model_repo, sample_model):
        """Test deployment with invalid environment."""
        mock_model_repo.get_by_id.return_value = sample_model

        with pytest.raises(ValueError, match="Invalid environment"):
            service.create_deployment(
                model_id="test-model-1",
                deployment_name="test-deployment",
                environment="invalid",
                strategy="rolling"
            )

    def test_create_deployment_invalid_strategy(self, service, mock_model_repo, sample_model):
        """Test deployment with invalid strategy."""
        mock_model_repo.get_by_id.return_value = sample_model

        with pytest.raises(ValueError, match="Invalid strategy"):
            service.create_deployment(
                model_id="test-model-1",
                deployment_name="test-deployment",
                environment="staging",
                strategy="invalid"
            )

    def test_create_deployment_model_not_found(self, service, mock_model_repo):
        """Test deployment with non-existent model."""
        mock_model_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Model .* not found"):
            service.create_deployment(
                model_id="non-existent",
                deployment_name="test-deployment",
                environment="staging",
                strategy="rolling"
            )

    def test_create_deployment_duplicate_name(self, service, mock_model_repo, mock_deployment_repo, sample_model, sample_deployment):
        """Test deployment with duplicate name."""
        mock_model_repo.get_by_id.return_value = sample_model
        mock_deployment_repo.get_by_name.return_value = sample_deployment

        with pytest.raises(ValueError, match="already exists"):
            service.create_deployment(
                model_id="test-model-1",
                deployment_name="fraud-staging",
                environment="staging",
                strategy="rolling"
            )

    def test_update_canary_traffic_success(self, service, mock_deployment_repo):
        """Test updating canary traffic percentage."""
        canary_deployment = Deployment(
            deployment_id="canary-deploy",
            model_id="test-model-1",
            deployment_name="canary-test",
            environment="production",
            strategy="canary",
            traffic_percentage=10
        )
        mock_deployment_repo.get_by_id.return_value = canary_deployment
        updated_deployment = Deployment(
            deployment_id="canary-deploy",
            model_id="test-model-1",
            deployment_name="canary-test",
            environment="production",
            strategy="canary",
            traffic_percentage=50
        )
        mock_deployment_repo.update_traffic_percentage.return_value = updated_deployment

        result = service.update_canary_traffic("canary-deploy", 50)

        assert result.traffic_percentage == 50
        mock_deployment_repo.update_traffic_percentage.assert_called_once_with("canary-deploy", 50)

    def test_update_canary_traffic_not_canary(self, service, mock_deployment_repo, sample_deployment):
        """Test updating traffic for non-canary deployment."""
        mock_deployment_repo.get_by_id.return_value = sample_deployment

        with pytest.raises(ValueError, match="not a canary deployment"):
            service.update_canary_traffic("test-deploy-1", 50)

    def test_update_canary_traffic_deployment_not_found(self, service, mock_deployment_repo):
        """Test updating traffic for non-existent deployment."""
        mock_deployment_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            service.update_canary_traffic("non-existent", 50)

    def test_rollback_deployment_success(self, service, mock_deployment_repo, sample_deployment):
        """Test successful deployment rollback."""
        mock_deployment_repo.get_by_id.return_value = sample_deployment
        rolled_back = Deployment(
            deployment_id="test-deploy-1",
            model_id="test-model-1",
            deployment_name="fraud-staging",
            environment="staging",
            strategy="rolling",
            status="rolled_back"
        )
        mock_deployment_repo.update_status.return_value = rolled_back

        result = service.rollback_deployment("test-deploy-1")

        assert result.status == "rolled_back"
        mock_deployment_repo.update_status.assert_called_once_with("test-deploy-1", "rolled_back")

    def test_rollback_deployment_not_found(self, service, mock_deployment_repo):
        """Test rolling back non-existent deployment."""
        mock_deployment_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            service.rollback_deployment("non-existent")

    def test_get_model_with_deployments(self, service, mock_model_repo, mock_deployment_repo, sample_model, sample_deployment):
        """Test getting model with its deployments."""
        # Ensure created_at is set
        sample_model.created_at = datetime.utcnow()

        mock_model_repo.get_by_id.return_value = sample_model
        mock_deployment_repo.get_by_model.return_value = [sample_deployment]

        result = service.get_model_with_deployments("test-model-1")

        assert result["model"]["model_id"] == "test-model-1"
        assert result["model"]["name"] == "fraud_detector"
        assert result["deployment_count"] == 1
        assert len(result["deployments"]) == 1
        assert result["deployments"][0]["deployment_id"] == "test-deploy-1"

    def test_get_model_with_deployments_not_found(self, service, mock_model_repo):
        """Test getting non-existent model with deployments."""
        mock_model_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            service.get_model_with_deployments("non-existent")

    def test_compare_models_success(self, service, mock_model_repo):
        """Test comparing multiple models."""
        model1 = MLModel(
            model_id="model-1",
            name="model_a",
            version="1.0.0",
            framework="sklearn",
            accuracy=0.95,
            precision=0.93
        )
        model2 = MLModel(
            model_id="model-2",
            name="model_b",
            version="1.0.0",
            framework="tensorflow",
            accuracy=0.97,
            precision=0.91
        )

        mock_model_repo.get_by_id.side_effect = [model1, model2]

        result = service.compare_models(["model-1", "model-2"])

        assert len(result["models"]) == 2
        assert "winner_by_metric" in result
        assert result["winner_by_metric"]["accuracy"] == "model-2"
        assert result["winner_by_metric"]["precision"] == "model-1"

    def test_compare_models_not_found(self, service, mock_model_repo):
        """Test comparing with non-existent model."""
        mock_model_repo.get_by_id.side_effect = [None]

        with pytest.raises(ValueError, match="not found"):
            service.compare_models(["non-existent"])

    def test_determine_winners(self, service):
        """Test determining best model for each metric."""
        models = [
            MLModel(
                model_id="model-1",
                name="model_a",
                version="1.0.0",
                framework="sklearn",
                accuracy=0.95,
                precision=0.93,
                recall=0.92,
                f1_score=0.925,
                auc_roc=0.96
            ),
            MLModel(
                model_id="model-2",
                name="model_b",
                version="1.0.0",
                framework="tensorflow",
                accuracy=0.97,
                precision=0.91,
                recall=0.94,
                f1_score=0.920,
                auc_roc=0.95
            )
        ]

        winners = service._determine_winners(models)

        assert winners["accuracy"] == "model-2"
        assert winners["precision"] == "model-1"
        assert winners["recall"] == "model-2"
        assert winners["f1_score"] == "model-1"
        assert winners["auc_roc"] == "model-1"

    def test_determine_winners_with_none_metrics(self, service):
        """Test determining winners when some metrics are None."""
        models = [
            MLModel(
                model_id="model-1",
                name="model_a",
                version="1.0.0",
                framework="sklearn",
                accuracy=0.95,
                precision=None
            ),
            MLModel(
                model_id="model-2",
                name="model_b",
                version="1.0.0",
                framework="tensorflow",
                accuracy=None,
                precision=0.91
            )
        ]

        winners = service._determine_winners(models)

        assert winners.get("accuracy") == "model-1"
        assert winners.get("precision") == "model-2"

    @patch('src.services.mlops_service.MLFLOW_AVAILABLE', True)
    def test_register_model_from_mlflow_success(self, service, mock_model_repo):
        """Test registering model from MLflow."""
        # Mock MLflow run
        mock_run = Mock()
        mock_run.info.experiment_id = "exp-123"
        mock_run.data.metrics = {
            "accuracy": 0.95,
            "precision": 0.93,
            "custom_metric": 0.88
        }
        mock_run.data.params = {
            "framework": "sklearn",
            "algorithm": "random_forest"
        }
        mock_run.data.tags = {
            "mlflow.user": "test_user",
            "mlflow.note.content": "Test model"
        }

        service.mlflow_client = Mock()
        service.mlflow_client.get_run.return_value = mock_run
        mock_model_repo.create.return_value = MLModel(
            model_id="mlflow-model",
            name="test_model",
            version="1.0.0",
            framework="sklearn"
        )

        result = service.register_model_from_mlflow(
            mlflow_run_id="run-123",
            model_name="test_model",
            version="1.0.0"
        )

        assert result.name == "test_model"
        service.mlflow_client.get_run.assert_called_once_with("run-123")
        mock_model_repo.create.assert_called_once()

    @patch('src.services.mlops_service.MLFLOW_AVAILABLE', False)
    def test_register_model_from_mlflow_not_available(self, service):
        """Test registering from MLflow when not available."""
        service.mlflow_client = None

        with pytest.raises(ValueError, match="MLflow is not available"):
            service.register_model_from_mlflow(
                mlflow_run_id="run-123",
                model_name="test_model",
                version="1.0.0"
            )

    def test_execute_deployment_strategies(self, service, mock_deployment_repo):
        """Test execution of different deployment strategies."""
        strategies = ["blue_green", "canary", "rolling", "shadow"]

        for strategy in strategies:
            deployment = Deployment(
                deployment_id=f"deploy-{strategy}",
                model_id="test-model-1",
                deployment_name=f"test-{strategy}",
                environment="staging",
                strategy=strategy,
                status="pending"
            )

            mock_deployment_repo.update_status.return_value = None
            mock_deployment_repo.update.return_value = None

            # Should not raise exception
            service._execute_deployment(deployment)

            # Verify status updates were called
            assert mock_deployment_repo.update_status.called
            assert mock_deployment_repo.update.called

            # Reset mocks for next iteration
            mock_deployment_repo.reset_mock()
