"""Unit tests for DeploymentRepository."""
import pytest
from datetime import datetime, timedelta

from src.repositories.deployment_repository import DeploymentRepository
from src.models.deployment import Deployment


class TestDeploymentRepository:
    """Test cases for DeploymentRepository."""

    def test_create_deployment(self, db_session, sample_model):
        """Test creating a new deployment."""
        repo = DeploymentRepository(db_session)

        deployment = Deployment(
            deployment_id="test-deploy-123",
            model_id=sample_model.model_id,
            deployment_name="test_deployment",
            environment="staging",
            strategy="rolling",
            status="running",
            replicas=3
        )

        created = repo.create(deployment)

        assert created.deployment_id == "test-deploy-123"
        assert created.deployment_name == "test_deployment"
        assert created.environment == "staging"
        assert created.created_at is not None

    def test_get_by_id(self, db_session, sample_deployment):
        """Test retrieving deployment by ID."""
        repo = DeploymentRepository(db_session)

        retrieved = repo.get_by_id(sample_deployment.deployment_id)

        assert retrieved is not None
        assert retrieved.deployment_id == sample_deployment.deployment_id
        assert retrieved.deployment_name == sample_deployment.deployment_name

    def test_get_by_id_not_found(self, db_session):
        """Test retrieving non-existent deployment."""
        repo = DeploymentRepository(db_session)

        retrieved = repo.get_by_id("non-existent")

        assert retrieved is None

    def test_get_by_name(self, db_session, sample_deployment):
        """Test retrieving deployment by name."""
        repo = DeploymentRepository(db_session)

        retrieved = repo.get_by_name(sample_deployment.deployment_name)

        assert retrieved is not None
        assert retrieved.deployment_id == sample_deployment.deployment_id

    def test_list_all(self, db_session, sample_deployment, canary_deployment):
        """Test listing all deployments."""
        repo = DeploymentRepository(db_session)

        deployments = repo.list_all()

        assert len(deployments) == 2
        # Should be ordered by created_at desc
        assert deployments[0].created_at >= deployments[1].created_at

    def test_list_all_with_pagination(self, db_session, sample_deployment, canary_deployment):
        """Test listing deployments with pagination."""
        repo = DeploymentRepository(db_session)

        deployments = repo.list_all(skip=0, limit=1)

        assert len(deployments) == 1

    def test_list_all_with_environment_filter(self, db_session, sample_deployment, canary_deployment):
        """Test listing deployments filtered by environment."""
        repo = DeploymentRepository(db_session)

        deployments = repo.list_all(environment="production")

        assert len(deployments) == 1
        assert deployments[0].environment == "production"

    def test_list_all_with_status_filter(self, db_session, sample_deployment):
        """Test listing deployments filtered by status."""
        repo = DeploymentRepository(db_session)

        deployments = repo.list_all(status="running")

        assert len(deployments) >= 1
        assert all(d.status == "running" for d in deployments)

    def test_get_by_model(self, db_session, sample_deployment, sample_model):
        """Test retrieving deployments for a model."""
        repo = DeploymentRepository(db_session)

        deployments = repo.get_by_model(sample_model.model_id)

        assert len(deployments) >= 1
        assert all(d.model_id == sample_model.model_id for d in deployments)

    def test_get_active_deployments(self, db_session, sample_deployment):
        """Test retrieving active deployments."""
        repo = DeploymentRepository(db_session)

        deployments = repo.get_active_deployments()

        assert len(deployments) >= 1
        assert all(d.status in ['running', 'healthy'] for d in deployments)

    def test_get_active_deployments_with_environment(self, db_session, sample_deployment):
        """Test retrieving active deployments filtered by environment."""
        repo = DeploymentRepository(db_session)

        deployments = repo.get_active_deployments(environment="staging")

        assert len(deployments) >= 1
        assert all(d.environment == "staging" for d in deployments)

    def test_get_by_environment(self, db_session, canary_deployment):
        """Test retrieving deployments by environment."""
        repo = DeploymentRepository(db_session)

        deployments = repo.get_by_environment("production")

        assert len(deployments) >= 1
        assert all(d.environment == "production" for d in deployments)

    def test_get_production_deployments(self, db_session, canary_deployment):
        """Test retrieving production deployments."""
        repo = DeploymentRepository(db_session)

        deployments = repo.get_production_deployments()

        assert len(deployments) >= 1
        assert all(d.environment == "production" for d in deployments)

    def test_get_by_strategy(self, db_session, canary_deployment):
        """Test retrieving deployments by strategy."""
        repo = DeploymentRepository(db_session)

        deployments = repo.get_by_strategy("canary")

        assert len(deployments) >= 1
        assert all(d.strategy == "canary" for d in deployments)

    def test_get_canary_deployments(self, db_session, canary_deployment):
        """Test retrieving canary deployments."""
        repo = DeploymentRepository(db_session)

        deployments = repo.get_canary_deployments()

        assert len(deployments) >= 1
        assert all(d.strategy == "canary" for d in deployments)
        assert all(d.traffic_percentage < 100 for d in deployments)
        assert all(d.status == "running" for d in deployments)

    def test_get_canary_deployments_by_model(self, db_session, canary_deployment, sample_model):
        """Test retrieving canary deployments for a model."""
        repo = DeploymentRepository(db_session)

        deployments = repo.get_canary_deployments(model_id=sample_model.model_id)

        assert len(deployments) >= 1
        assert all(d.model_id == sample_model.model_id for d in deployments)

    def test_update_deployment(self, db_session, sample_deployment):
        """Test updating deployment attributes."""
        repo = DeploymentRepository(db_session)

        updated = repo.update(
            sample_deployment.deployment_id,
            {"replicas": 5, "status": "scaling"}
        )

        assert updated is not None
        assert updated.replicas == 5
        assert updated.status == "scaling"
        assert updated.updated_at > sample_deployment.created_at

    def test_update_nonexistent_deployment(self, db_session):
        """Test updating non-existent deployment."""
        repo = DeploymentRepository(db_session)

        updated = repo.update("non-existent", {"replicas": 5})

        assert updated is None

    def test_update_status(self, db_session, sample_deployment):
        """Test updating deployment status."""
        repo = DeploymentRepository(db_session)

        updated = repo.update_status(sample_deployment.deployment_id, "stopped")

        assert updated is not None
        assert updated.status == "stopped"

    def test_update_health_status(self, db_session, sample_deployment):
        """Test updating deployment health status."""
        repo = DeploymentRepository(db_session)

        updated = repo.update_health_status(
            sample_deployment.deployment_id,
            "degraded"
        )

        assert updated is not None
        assert updated.health_status == "degraded"
        assert updated.last_health_check is not None

    def test_update_traffic_percentage(self, db_session, canary_deployment):
        """Test updating traffic percentage."""
        repo = DeploymentRepository(db_session)

        updated = repo.update_traffic_percentage(
            canary_deployment.deployment_id,
            50
        )

        assert updated is not None
        assert updated.traffic_percentage == 50

    def test_update_traffic_percentage_invalid(self, db_session, canary_deployment):
        """Test updating traffic percentage with invalid value."""
        repo = DeploymentRepository(db_session)

        with pytest.raises(ValueError):
            repo.update_traffic_percentage(canary_deployment.deployment_id, 150)

    def test_increment_request_count(self, db_session, sample_deployment):
        """Test incrementing request count."""
        repo = DeploymentRepository(db_session)

        initial_count = sample_deployment.request_count or 0
        updated = repo.increment_request_count(sample_deployment.deployment_id, 10)

        assert updated is not None
        assert updated.request_count == initial_count + 10

    def test_increment_error_count(self, db_session, sample_deployment):
        """Test incrementing error count."""
        repo = DeploymentRepository(db_session)

        initial_count = sample_deployment.error_count or 0
        updated = repo.increment_error_count(sample_deployment.deployment_id, 2)

        assert updated is not None
        assert updated.error_count == initial_count + 2

    def test_update_metrics(self, db_session, sample_deployment):
        """Test updating deployment metrics."""
        repo = DeploymentRepository(db_session)

        updated = repo.update_metrics(
            sample_deployment.deployment_id,
            request_count=5000,
            error_count=25,
            avg_latency_ms=75
        )

        assert updated is not None
        assert updated.request_count == 5000
        assert updated.error_count == 25
        assert updated.avg_latency_ms == 75

    def test_delete_deployment(self, db_session, sample_deployment):
        """Test deleting a deployment."""
        repo = DeploymentRepository(db_session)

        result = repo.delete(sample_deployment.deployment_id)

        assert result is True

        # Verify deletion
        retrieved = repo.get_by_id(sample_deployment.deployment_id)
        assert retrieved is None

    def test_delete_nonexistent_deployment(self, db_session):
        """Test deleting non-existent deployment."""
        repo = DeploymentRepository(db_session)

        result = repo.delete("non-existent")

        assert result is False

    def test_count_by_environment(self, db_session, sample_deployment, canary_deployment):
        """Test counting deployments by environment."""
        repo = DeploymentRepository(db_session)

        counts = repo.count_by_environment()

        assert counts["staging"] >= 1
        assert counts["production"] >= 1

    def test_count_by_status(self, db_session, sample_deployment, canary_deployment):
        """Test counting deployments by status."""
        repo = DeploymentRepository(db_session)

        counts = repo.count_by_status()

        assert counts["running"] >= 2

    def test_get_deployment_stats(self, db_session, sample_deployment):
        """Test getting deployment statistics."""
        repo = DeploymentRepository(db_session)

        stats = repo.get_deployment_stats(sample_deployment.deployment_id)

        assert stats is not None
        assert stats["deployment_id"] == sample_deployment.deployment_id
        assert stats["deployment_name"] == sample_deployment.deployment_name
        assert "request_count" in stats
        assert "error_count" in stats
        assert "error_rate_percentage" in stats
        assert "uptime_hours" in stats

    def test_get_deployment_stats_not_found(self, db_session):
        """Test getting stats for non-existent deployment."""
        repo = DeploymentRepository(db_session)

        stats = repo.get_deployment_stats("non-existent")

        assert stats is None

    def test_get_deployment_stats_error_rate(self, db_session, sample_deployment):
        """Test deployment stats error rate calculation."""
        repo = DeploymentRepository(db_session)

        # Update metrics to known values
        repo.update_metrics(
            sample_deployment.deployment_id,
            request_count=1000,
            error_count=50
        )

        stats = repo.get_deployment_stats(sample_deployment.deployment_id)

        assert stats["error_rate_percentage"] == 5.0

    def test_get_unhealthy_deployments(self, db_session, sample_deployment):
        """Test retrieving unhealthy deployments."""
        repo = DeploymentRepository(db_session)

        # Mark deployment as unhealthy
        repo.update_health_status(sample_deployment.deployment_id, "unhealthy")

        deployments = repo.get_unhealthy_deployments()

        assert len(deployments) >= 1
        assert any(d.health_status in ['unhealthy', 'degraded', 'unknown'] for d in deployments)

    def test_get_deployments_needing_health_check(self, db_session, sample_model):
        """Test retrieving deployments needing health check."""
        repo = DeploymentRepository(db_session)

        # Create deployment with old health check
        old_deployment = Deployment(
            deployment_id="old-health-check",
            model_id=sample_model.model_id,
            deployment_name="old_deployment",
            environment="staging",
            strategy="rolling",
            status="running",
            last_health_check=datetime.utcnow() - timedelta(minutes=10)
        )
        repo.create(old_deployment)

        deployments = repo.get_deployments_needing_health_check(minutes_since_last_check=5)

        assert len(deployments) >= 1
        assert any(d.deployment_id == "old-health-check" for d in deployments)

    def test_calculate_uptime(self, db_session, sample_deployment):
        """Test uptime calculation."""
        repo = DeploymentRepository(db_session)

        stats = repo.get_deployment_stats(sample_deployment.deployment_id)

        assert "uptime_hours" in stats
        # Should be close to 0 since just created
        assert stats["uptime_hours"] is not None
