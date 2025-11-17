"""Unit tests for ExperimentService."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from src.services.experiment_service import ExperimentService
from src.models.experiment import Experiment


class TestExperimentService:
    """Test cases for ExperimentService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_experiment_repo(self):
        """Create mock experiment repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db, mock_experiment_repo):
        """Create ExperimentService with mocked dependencies."""
        service = ExperimentService(mock_db)
        service.experiment_repo = mock_experiment_repo
        return service

    @pytest.fixture
    def sample_experiment(self):
        """Create sample experiment."""
        return Experiment(
            experiment_id="exp-1",
            name="fraud_detection_exp",
            description="Fraud detection experiments",
            mlflow_experiment_id="mlflow-exp-1",
            tags={"team": "ml", "project": "fraud"},
            run_count=5,
            created_by="test_user"
        )

    def test_init(self, mock_db):
        """Test service initialization."""
        service = ExperimentService(mock_db)

        assert service.db == mock_db
        assert service.experiment_repo is not None

    def test_create_experiment_success(self, service, mock_experiment_repo):
        """Test successful experiment creation."""
        mock_experiment_repo.get_by_name.return_value = None
        created_exp = Experiment(
            experiment_id="new-exp",
            name="test_experiment",
            description="Test experiment",
            created_by="test_user"
        )
        mock_experiment_repo.create.return_value = created_exp

        result = service.create_experiment(
            name="test_experiment",
            description="Test experiment",
            tags={"env": "test"},
            created_by="test_user"
        )

        assert result.name == "test_experiment"
        mock_experiment_repo.create.assert_called_once()

    def test_create_experiment_duplicate_name(self, service, mock_experiment_repo, sample_experiment):
        """Test creating experiment with duplicate name."""
        mock_experiment_repo.get_by_name.return_value = sample_experiment

        with pytest.raises(ValueError, match="already exists"):
            service.create_experiment(
                name="fraud_detection_exp",
                description="Duplicate",
                created_by="test_user"
            )

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_sync_experiment_from_mlflow(self, service, mock_experiment_repo):
        """Test syncing experiment from MLflow."""
        # Mock MLflow experiment
        mock_mlflow_exp = Mock()
        mock_mlflow_exp.experiment_id = "mlflow-123"
        mock_mlflow_exp.name = "mlflow_experiment"
        mock_mlflow_exp.lifecycle_stage = "active"
        mock_mlflow_exp.tags = {"description": "Test"}

        service.mlflow_client = Mock()
        service.mlflow_client.get_experiment.return_value = mock_mlflow_exp

        mock_experiment_repo.get_by_mlflow_experiment_id.return_value = None
        synced_exp = Experiment(
            experiment_id="synced-exp",
            name="mlflow_experiment",
            mlflow_experiment_id="mlflow-123"
        )
        mock_experiment_repo.create.return_value = synced_exp

        result = service.sync_experiment_from_mlflow("mlflow-123")

        assert result.mlflow_experiment_id == "mlflow-123"
        service.mlflow_client.get_experiment.assert_called_once_with("mlflow-123")
        mock_experiment_repo.create.assert_called_once()

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', False)
    def test_sync_experiment_mlflow_not_available(self, service):
        """Test syncing when MLflow is not available."""
        service.mlflow_client = None

        with pytest.raises(ValueError, match="MLflow is not available"):
            service.sync_experiment_from_mlflow("mlflow-123")

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_start_run_success(self, service, mock_experiment_repo, sample_experiment):
        """Test starting an experiment run."""
        mock_experiment_repo.get_by_id.return_value = sample_experiment
        mock_experiment_repo.increment_run_count.return_value = sample_experiment

        mock_run = Mock()
        mock_run.info.run_id = "run-123"

        service.mlflow_client = Mock()
        service.mlflow_client.create_run.return_value = mock_run

        result = service.start_run(
            experiment_id="exp-1",
            run_name="test_run",
            tags={"version": "1.0"}
        )

        assert result["run_id"] == "run-123"
        assert result["experiment_id"] == "exp-1"
        service.mlflow_client.create_run.assert_called_once()
        mock_experiment_repo.increment_run_count.assert_called_once()

    def test_start_run_experiment_not_found(self, service, mock_experiment_repo):
        """Test starting run for non-existent experiment."""
        mock_experiment_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            service.start_run(experiment_id="non-existent")

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_log_metrics(self, service):
        """Test logging metrics to MLflow."""
        service.mlflow_client = Mock()

        metrics = {"accuracy": 0.95, "precision": 0.93}

        # Should not raise exception
        service.log_metrics(run_id="run-123", metrics=metrics)

        # MLflow client should be called for each metric
        assert service.mlflow_client.log_metric.call_count == 2

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_log_parameters(self, service):
        """Test logging parameters to MLflow."""
        service.mlflow_client = Mock()

        params = {"learning_rate": 0.01, "batch_size": 32}

        # Should not raise exception
        service.log_parameters(run_id="run-123", params=params)

        # MLflow client should be called for each parameter
        assert service.mlflow_client.log_param.call_count == 2

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_end_run(self, service):
        """Test ending an experiment run."""
        service.mlflow_client = Mock()

        # Should not raise exception
        service.end_run(run_id="run-123")

        service.mlflow_client.set_terminated.assert_called_once()

    def test_get_experiment_details(self, service, mock_experiment_repo, sample_experiment):
        """Test getting experiment details."""
        mock_experiment_repo.get_by_id.return_value = sample_experiment

        result = service.get_experiment_details(experiment_id="exp-1")

        assert result["experiment_id"] == "exp-1"
        assert result["name"] == "fraud_detection_exp"
        assert result["run_count"] == 5
        assert "tags" in result

    def test_get_experiment_details_not_found(self, service, mock_experiment_repo):
        """Test getting details for non-existent experiment."""
        mock_experiment_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            service.get_experiment_details(experiment_id="non-existent")

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_get_experiment_leaderboard(self, service, mock_experiment_repo, sample_experiment):
        """Test getting experiment leaderboard."""
        mock_experiment_repo.get_by_id.return_value = sample_experiment

        # Mock MLflow runs
        mock_run1 = Mock()
        mock_run1.info.run_id = "run-1"
        mock_run1.data.metrics = {"accuracy": 0.95}
        mock_run1.data.params = {"learning_rate": 0.01}

        mock_run2 = Mock()
        mock_run2.info.run_id = "run-2"
        mock_run2.data.metrics = {"accuracy": 0.93}
        mock_run2.data.params = {"learning_rate": 0.02}

        service.mlflow_client = Mock()
        service.mlflow_client.search_runs.return_value = [mock_run1, mock_run2]

        result = service.get_experiment_leaderboard(
            experiment_id="exp-1",
            metric="accuracy",
            limit=10
        )

        assert result["experiment_id"] == "exp-1"
        assert len(result["leaderboard"]) == 2
        # Should be sorted by metric descending
        assert result["leaderboard"][0]["metrics"]["accuracy"] == 0.95

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_compare_runs(self, service):
        """Test comparing multiple runs."""
        # Mock MLflow runs
        mock_run1 = Mock()
        mock_run1.info.run_id = "run-1"
        mock_run1.info.start_time = 1000
        mock_run1.info.end_time = 2000
        mock_run1.data.metrics = {"accuracy": 0.95, "precision": 0.93}
        mock_run1.data.params = {"learning_rate": 0.01}

        mock_run2 = Mock()
        mock_run2.info.run_id = "run-2"
        mock_run2.info.start_time = 1500
        mock_run2.info.end_time = 2500
        mock_run2.data.metrics = {"accuracy": 0.93, "precision": 0.95}
        mock_run2.data.params = {"learning_rate": 0.02}

        service.mlflow_client = Mock()
        service.mlflow_client.get_run.side_effect = [mock_run1, mock_run2]

        result = service.compare_runs(run_ids=["run-1", "run-2"])

        assert len(result["runs"]) == 2
        assert "metric_comparison" in result
        assert "parameter_comparison" in result

    def test_delete_experiment_success(self, service, mock_experiment_repo, sample_experiment):
        """Test successful experiment deletion."""
        mock_experiment_repo.get_by_id.return_value = sample_experiment
        mock_experiment_repo.delete.return_value = True

        result = service.delete_experiment(experiment_id="exp-1")

        assert result is True
        mock_experiment_repo.delete.assert_called_once_with("exp-1")

    def test_delete_experiment_not_found(self, service, mock_experiment_repo):
        """Test deleting non-existent experiment."""
        mock_experiment_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            service.delete_experiment(experiment_id="non-existent")

    def test_get_all_experiments_summary(self, service, mock_experiment_repo):
        """Test getting summary of all experiments."""
        experiments = [
            Experiment(
                experiment_id="exp-1",
                name="exp_one",
                run_count=5,
                created_by="user1"
            ),
            Experiment(
                experiment_id="exp-2",
                name="exp_two",
                run_count=10,
                created_by="user2"
            )
        ]

        mock_experiment_repo.list_all.return_value = experiments
        mock_experiment_repo.get_experiment_stats.return_value = {
            "total_experiments": 2,
            "total_runs": 15,
            "avg_runs_per_experiment": 7.5
        }

        result = service.get_all_experiments_summary()

        assert result["total_experiments"] == 2
        assert result["total_runs"] == 15
        assert len(result["experiments"]) == 2

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_start_run_without_mlflow_experiment_id(self, service, mock_experiment_repo):
        """Test starting run when experiment doesn't have MLflow ID."""
        exp_without_mlflow = Experiment(
            experiment_id="exp-no-mlflow",
            name="local_experiment",
            mlflow_experiment_id=None,
            created_by="test_user"
        )

        mock_experiment_repo.get_by_id.return_value = exp_without_mlflow

        # Mock MLflow experiment creation
        service.mlflow_client = Mock()
        service.mlflow_client.create_experiment.return_value = "new-mlflow-id"
        mock_experiment_repo.update.return_value = exp_without_mlflow

        mock_run = Mock()
        mock_run.info.run_id = "run-456"
        service.mlflow_client.create_run.return_value = mock_run
        mock_experiment_repo.increment_run_count.return_value = exp_without_mlflow

        result = service.start_run(experiment_id="exp-no-mlflow")

        # Should create MLflow experiment
        service.mlflow_client.create_experiment.assert_called_once()
        assert result["run_id"] == "run-456"

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', False)
    def test_start_run_without_mlflow(self, service, mock_experiment_repo, sample_experiment):
        """Test starting run when MLflow is not available."""
        service.mlflow_client = None
        mock_experiment_repo.get_by_id.return_value = sample_experiment
        mock_experiment_repo.increment_run_count.return_value = sample_experiment

        result = service.start_run(experiment_id="exp-1")

        # Should still work but without MLflow integration
        assert result["experiment_id"] == "exp-1"
        assert result["run_id"] is None
        mock_experiment_repo.increment_run_count.assert_called_once()

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', False)
    def test_log_metrics_without_mlflow(self, service):
        """Test logging metrics when MLflow is not available."""
        service.mlflow_client = None

        # Should not raise exception, just log warning
        service.log_metrics(run_id="run-123", metrics={"accuracy": 0.95})

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_get_experiment_leaderboard_empty(self, service, mock_experiment_repo, sample_experiment):
        """Test leaderboard with no runs."""
        mock_experiment_repo.get_by_id.return_value = sample_experiment

        service.mlflow_client = Mock()
        service.mlflow_client.search_runs.return_value = []

        result = service.get_experiment_leaderboard(
            experiment_id="exp-1",
            metric="accuracy"
        )

        assert result["experiment_id"] == "exp-1"
        assert len(result["leaderboard"]) == 0

    @patch('src.services.experiment_service.MLFLOW_AVAILABLE', True)
    def test_compare_runs_single_run(self, service):
        """Test comparing with only one run."""
        mock_run = Mock()
        mock_run.info.run_id = "run-1"
        mock_run.info.start_time = 1000
        mock_run.info.end_time = 2000
        mock_run.data.metrics = {"accuracy": 0.95}
        mock_run.data.params = {"learning_rate": 0.01}

        service.mlflow_client = Mock()
        service.mlflow_client.get_run.return_value = mock_run

        result = service.compare_runs(run_ids=["run-1"])

        assert len(result["runs"]) == 1
        assert result["runs"][0]["run_id"] == "run-1"

    def test_create_experiment_with_mlflow_id(self, service, mock_experiment_repo):
        """Test creating experiment with MLflow experiment ID."""
        mock_experiment_repo.get_by_name.return_value = None
        created_exp = Experiment(
            experiment_id="new-exp",
            name="test_experiment",
            mlflow_experiment_id="mlflow-789",
            created_by="test_user"
        )
        mock_experiment_repo.create.return_value = created_exp

        result = service.create_experiment(
            name="test_experiment",
            mlflow_experiment_id="mlflow-789",
            created_by="test_user"
        )

        assert result.mlflow_experiment_id == "mlflow-789"
        mock_experiment_repo.create.assert_called_once()
