"""Unit tests for DriftRepository."""
import pytest
from datetime import datetime, timedelta

from src.repositories.drift_repository import DriftRepository
from src.models.drift_detection import DriftDetection


class TestDriftRepository:
    """Test cases for DriftRepository."""

    def test_create_drift_detection(self, db_session, sample_model):
        """Test creating a new drift detection."""
        repo = DriftRepository(db_session)

        drift = DriftDetection(
            drift_id="test-drift-123",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow(),
            drift_type="data_drift",
            drift_score=0.15,
            threshold=0.05,
            is_drift_detected=True,
            affected_features=[{"name": "feature1", "p_value": 0.02}],
            severity="medium"
        )

        created = repo.create(drift)

        assert created.drift_id == "test-drift-123"
        assert created.drift_type == "data_drift"
        assert created.is_drift_detected is True

    def test_get_by_id(self, db_session, sample_drift_detection):
        """Test retrieving drift detection by ID."""
        repo = DriftRepository(db_session)

        retrieved = repo.get_by_id(sample_drift_detection.drift_id)

        assert retrieved is not None
        assert retrieved.drift_id == sample_drift_detection.drift_id
        assert retrieved.model_id == sample_drift_detection.model_id

    def test_get_by_id_not_found(self, db_session):
        """Test retrieving non-existent drift detection."""
        repo = DriftRepository(db_session)

        retrieved = repo.get_by_id("non-existent")

        assert retrieved is None

    def test_list_all(self, db_session, sample_drift_detection):
        """Test listing all drift detections."""
        repo = DriftRepository(db_session)

        detections = repo.list_all()

        assert len(detections) >= 1

    def test_list_all_with_drift_filter(self, db_session, sample_model):
        """Test listing detections filtered by drift status."""
        repo = DriftRepository(db_session)

        # Create one with drift and one without
        drift_yes = DriftDetection(
            drift_id="drift-yes",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.15,
            is_drift_detected=True
        )
        drift_no = DriftDetection(
            drift_id="drift-no",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.02,
            is_drift_detected=False
        )
        repo.create(drift_yes)
        repo.create(drift_no)

        detected_only = repo.list_all(drift_detected=True)

        assert len(detected_only) >= 1
        assert all(d.is_drift_detected for d in detected_only)

    def test_get_by_model(self, db_session, sample_drift_detection, sample_model):
        """Test retrieving drift detections for a model."""
        repo = DriftRepository(db_session)

        detections = repo.get_by_model(sample_model.model_id)

        assert len(detections) >= 1
        assert all(d.model_id == sample_model.model_id for d in detections)

    def test_get_by_model_drift_only(self, db_session, sample_model):
        """Test retrieving only drift detections for a model."""
        repo = DriftRepository(db_session)

        # Create drift and non-drift detections
        drift_yes = DriftDetection(
            drift_id="model-drift-yes",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.15,
            is_drift_detected=True
        )
        drift_no = DriftDetection(
            drift_id="model-drift-no",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.02,
            is_drift_detected=False
        )
        repo.create(drift_yes)
        repo.create(drift_no)

        detections = repo.get_by_model(sample_model.model_id, drift_detected_only=True)

        assert len(detections) >= 1
        assert all(d.is_drift_detected for d in detections)

    def test_get_by_deployment(self, db_session, sample_drift_detection):
        """Test retrieving drift detections for a deployment."""
        repo = DriftRepository(db_session)

        # Assuming sample_drift_detection has deployment_id set
        if sample_drift_detection.deployment_id:
            detections = repo.get_by_deployment(sample_drift_detection.deployment_id)
            assert isinstance(detections, list)

    def test_get_recent_detections(self, db_session, sample_drift_detection):
        """Test retrieving recent drift detections."""
        repo = DriftRepository(db_session)

        detections = repo.get_recent_detections(hours=24)

        assert len(detections) >= 1
        # All should be within the last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        assert all(d.detection_timestamp >= cutoff for d in detections)

    def test_get_recent_detections_drift_only(self, db_session, sample_model):
        """Test retrieving recent drift detections with drift filter."""
        repo = DriftRepository(db_session)

        # Create recent drift
        drift = DriftDetection(
            drift_id="recent-drift",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow(),
            drift_type="data_drift",
            drift_score=0.15,
            is_drift_detected=True
        )
        repo.create(drift)

        detections = repo.get_recent_detections(hours=1, drift_detected_only=True)

        assert len(detections) >= 1
        assert all(d.is_drift_detected for d in detections)

    def test_get_by_drift_type(self, db_session, sample_drift_detection):
        """Test retrieving drift detections by type."""
        repo = DriftRepository(db_session)

        detections = repo.get_by_drift_type("data_drift")

        assert len(detections) >= 1
        assert all(d.drift_type == "data_drift" for d in detections)

    def test_get_by_drift_type_with_model_filter(self, db_session, sample_drift_detection, sample_model):
        """Test retrieving drift detections by type and model."""
        repo = DriftRepository(db_session)

        detections = repo.get_by_drift_type("data_drift", model_id=sample_model.model_id)

        assert len(detections) >= 1
        assert all(d.drift_type == "data_drift" for d in detections)
        assert all(d.model_id == sample_model.model_id for d in detections)

    def test_get_high_severity_drifts(self, db_session, sample_model):
        """Test retrieving high severity drifts."""
        repo = DriftRepository(db_session)

        # Create high severity drift
        drift = DriftDetection(
            drift_id="high-severity",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow(),
            drift_type="concept_drift",
            drift_score=0.35,
            is_drift_detected=True,
            severity="high"
        )
        repo.create(drift)

        detections = repo.get_high_severity_drifts(severity="high", hours=24)

        assert len(detections) >= 1
        assert all(d.severity == "high" for d in detections)
        assert all(d.is_drift_detected for d in detections)

    def test_get_auto_retrain_triggered(self, db_session, sample_model):
        """Test retrieving drift detections that triggered retraining."""
        repo = DriftRepository(db_session)

        # Create drift with auto-retrain triggered
        drift = DriftDetection(
            drift_id="auto-retrain",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow(),
            drift_type="concept_drift",
            drift_score=0.40,
            is_drift_detected=True,
            severity="high",
            auto_retrain_triggered=True
        )
        repo.create(drift)

        detections = repo.get_auto_retrain_triggered(hours=24)

        assert len(detections) >= 1
        assert all(d.auto_retrain_triggered for d in detections)

    def test_get_detections_by_threshold(self, db_session, sample_model):
        """Test retrieving drift detections by score threshold."""
        repo = DriftRepository(db_session)

        # Create drifts with different scores
        drift1 = DriftDetection(
            drift_id="drift-score-1",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.10,
            is_drift_detected=True
        )
        drift2 = DriftDetection(
            drift_id="drift-score-2",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.25,
            is_drift_detected=True
        )
        repo.create(drift1)
        repo.create(drift2)

        detections = repo.get_detections_by_threshold(min_score=0.15)

        assert len(detections) >= 1
        assert all(d.drift_score >= 0.15 for d in detections)

    def test_get_detections_by_threshold_range(self, db_session, sample_model):
        """Test retrieving drift detections within score range."""
        repo = DriftRepository(db_session)

        # Create drifts with different scores
        drift1 = DriftDetection(
            drift_id="range-drift-1",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.10,
            is_drift_detected=True
        )
        drift2 = DriftDetection(
            drift_id="range-drift-2",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.25,
            is_drift_detected=True
        )
        drift3 = DriftDetection(
            drift_id="range-drift-3",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.40,
            is_drift_detected=True
        )
        repo.create(drift1)
        repo.create(drift2)
        repo.create(drift3)

        detections = repo.get_detections_by_threshold(min_score=0.15, max_score=0.30)

        assert len(detections) >= 1
        assert all(0.15 <= d.drift_score <= 0.30 for d in detections)

    def test_get_latest_detection_for_model(self, db_session, sample_model):
        """Test retrieving latest drift detection for a model."""
        repo = DriftRepository(db_session)

        # Create multiple detections at different times
        drift1 = DriftDetection(
            drift_id="latest-drift-1",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow() - timedelta(hours=2),
            drift_type="data_drift",
            drift_score=0.10,
            is_drift_detected=True
        )
        drift2 = DriftDetection(
            drift_id="latest-drift-2",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow(),
            drift_type="data_drift",
            drift_score=0.15,
            is_drift_detected=True
        )
        repo.create(drift1)
        repo.create(drift2)

        latest = repo.get_latest_detection_for_model(sample_model.model_id)

        assert latest is not None
        assert latest.drift_id == "latest-drift-2"

    def test_update_drift_detection(self, db_session, sample_drift_detection):
        """Test updating drift detection attributes."""
        repo = DriftRepository(db_session)

        updated = repo.update(
            sample_drift_detection.drift_id,
            {"severity": "high", "auto_retrain_triggered": True}
        )

        assert updated is not None
        assert updated.severity == "high"
        assert updated.auto_retrain_triggered is True

    def test_update_nonexistent_drift(self, db_session):
        """Test updating non-existent drift detection."""
        repo = DriftRepository(db_session)

        updated = repo.update("non-existent", {"severity": "high"})

        assert updated is None

    def test_mark_auto_retrain_triggered(self, db_session, sample_drift_detection):
        """Test marking auto-retrain as triggered."""
        repo = DriftRepository(db_session)

        updated = repo.mark_auto_retrain_triggered(sample_drift_detection.drift_id)

        assert updated is not None
        assert updated.auto_retrain_triggered is True

    def test_delete_drift_detection(self, db_session, sample_drift_detection):
        """Test deleting a drift detection."""
        repo = DriftRepository(db_session)

        result = repo.delete(sample_drift_detection.drift_id)

        assert result is True

        # Verify deletion
        retrieved = repo.get_by_id(sample_drift_detection.drift_id)
        assert retrieved is None

    def test_delete_nonexistent_drift(self, db_session):
        """Test deleting non-existent drift detection."""
        repo = DriftRepository(db_session)

        result = repo.delete("non-existent")

        assert result is False

    def test_get_drift_statistics(self, db_session, sample_model):
        """Test getting drift statistics."""
        repo = DriftRepository(db_session)

        # Create multiple drift detections
        drift1 = DriftDetection(
            drift_id="stats-drift-1",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow(),
            drift_type="data_drift",
            drift_score=0.15,
            is_drift_detected=True,
            severity="medium"
        )
        drift2 = DriftDetection(
            drift_id="stats-drift-2",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow(),
            drift_type="concept_drift",
            drift_score=0.25,
            is_drift_detected=True,
            severity="high",
            auto_retrain_triggered=True
        )
        drift3 = DriftDetection(
            drift_id="stats-drift-3",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow(),
            drift_type="data_drift",
            drift_score=0.02,
            is_drift_detected=False
        )
        repo.create(drift1)
        repo.create(drift2)
        repo.create(drift3)

        stats = repo.get_drift_statistics(model_id=sample_model.model_id, hours=24)

        assert stats["total_detections"] >= 3
        assert stats["drift_detected_count"] >= 2
        assert "drift_rate_percentage" in stats
        assert "avg_drift_score" in stats
        assert "drift_by_type" in stats
        assert "drift_by_severity" in stats
        assert "auto_retrain_triggered_count" in stats

    def test_get_drift_statistics_empty(self, db_session):
        """Test getting stats with no drift detections."""
        repo = DriftRepository(db_session)

        stats = repo.get_drift_statistics(hours=24)

        assert stats["total_detections"] == 0
        assert stats["drift_detected_count"] == 0
        assert stats["drift_rate_percentage"] == 0.0

    def test_count_by_drift_type(self, db_session, sample_model):
        """Test counting drift detections by type."""
        repo = DriftRepository(db_session)

        # Create detections of different types
        drift1 = DriftDetection(
            drift_id="count-type-1",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.15,
            is_drift_detected=True
        )
        drift2 = DriftDetection(
            drift_id="count-type-2",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.20,
            is_drift_detected=True
        )
        drift3 = DriftDetection(
            drift_id="count-type-3",
            model_id=sample_model.model_id,
            drift_type="concept_drift",
            drift_score=0.25,
            is_drift_detected=True
        )
        repo.create(drift1)
        repo.create(drift2)
        repo.create(drift3)

        counts = repo.count_by_drift_type()

        assert counts["data_drift"] >= 2
        assert counts["concept_drift"] >= 1

    def test_count_by_severity(self, db_session, sample_model):
        """Test counting drift detections by severity."""
        repo = DriftRepository(db_session)

        # Create detections with different severities
        drift1 = DriftDetection(
            drift_id="count-sev-1",
            model_id=sample_model.model_id,
            drift_type="data_drift",
            drift_score=0.15,
            is_drift_detected=True,
            severity="medium"
        )
        drift2 = DriftDetection(
            drift_id="count-sev-2",
            model_id=sample_model.model_id,
            drift_type="concept_drift",
            drift_score=0.35,
            is_drift_detected=True,
            severity="high"
        )
        repo.create(drift1)
        repo.create(drift2)

        counts = repo.count_by_severity()

        assert counts.get("medium", 0) >= 1
        assert counts.get("high", 0) >= 1

    def test_cleanup_old_detections(self, db_session, sample_model):
        """Test cleaning up old drift detections."""
        repo = DriftRepository(db_session)

        # Create old detection
        old_drift = DriftDetection(
            drift_id="old-drift",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow() - timedelta(days=100),
            drift_type="data_drift",
            drift_score=0.10,
            is_drift_detected=True
        )
        repo.create(old_drift)

        # Create recent detection
        recent_drift = DriftDetection(
            drift_id="recent-drift",
            model_id=sample_model.model_id,
            detection_timestamp=datetime.utcnow(),
            drift_type="data_drift",
            drift_score=0.15,
            is_drift_detected=True
        )
        repo.create(recent_drift)

        # Cleanup detections older than 90 days
        deleted_count = repo.cleanup_old_detections(days_to_keep=90)

        assert deleted_count >= 1

        # Verify old detection is gone
        old = repo.get_by_id("old-drift")
        assert old is None

        # Verify recent detection still exists
        recent = repo.get_by_id("recent-drift")
        assert recent is not None
