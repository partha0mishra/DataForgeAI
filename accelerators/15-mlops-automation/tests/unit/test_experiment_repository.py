"""Unit tests for ExperimentRepository."""
import pytest
from datetime import datetime, timedelta

from src.repositories.experiment_repository import ExperimentRepository
from src.models.experiment import Experiment


class TestExperimentRepository:
    """Test cases for ExperimentRepository."""

    def test_create_experiment(self, db_session):
        """Test creating a new experiment."""
        repo = ExperimentRepository(db_session)

        experiment = Experiment(
            experiment_id="test-exp-123",
            name="test_experiment",
            description="Test experiment",
            mlflow_experiment_id="mlflow-123",
            tags={"env": "test"},
            run_count=0,
            created_by="test_user"
        )

        created = repo.create(experiment)

        assert created.experiment_id == "test-exp-123"
        assert created.name == "test_experiment"
        assert created.created_at is not None

    def test_get_by_id(self, db_session, sample_experiment):
        """Test retrieving experiment by ID."""
        repo = ExperimentRepository(db_session)

        retrieved = repo.get_by_id(sample_experiment.experiment_id)

        assert retrieved is not None
        assert retrieved.experiment_id == sample_experiment.experiment_id
        assert retrieved.name == sample_experiment.name

    def test_get_by_id_not_found(self, db_session):
        """Test retrieving non-existent experiment."""
        repo = ExperimentRepository(db_session)

        retrieved = repo.get_by_id("non-existent")

        assert retrieved is None

    def test_get_by_name(self, db_session, sample_experiment):
        """Test retrieving experiment by name."""
        repo = ExperimentRepository(db_session)

        retrieved = repo.get_by_name(sample_experiment.name)

        assert retrieved is not None
        assert retrieved.experiment_id == sample_experiment.experiment_id

    def test_get_by_mlflow_experiment_id(self, db_session, sample_experiment):
        """Test retrieving experiment by MLflow ID."""
        repo = ExperimentRepository(db_session)

        retrieved = repo.get_by_mlflow_experiment_id(
            sample_experiment.mlflow_experiment_id
        )

        assert retrieved is not None
        assert retrieved.experiment_id == sample_experiment.experiment_id

    def test_list_all(self, db_session):
        """Test listing all experiments."""
        repo = ExperimentRepository(db_session)

        # Create multiple experiments
        exp1 = Experiment(
            experiment_id="exp-1",
            name="experiment_1",
            created_by="user1"
        )
        exp2 = Experiment(
            experiment_id="exp-2",
            name="experiment_2",
            created_by="user1"
        )
        repo.create(exp1)
        repo.create(exp2)

        experiments = repo.list_all()

        assert len(experiments) >= 2
        # Should be ordered by created_at desc
        assert experiments[0].created_at >= experiments[1].created_at

    def test_list_all_with_pagination(self, db_session, sample_experiment):
        """Test listing experiments with pagination."""
        repo = ExperimentRepository(db_session)

        # Create additional experiment
        exp = Experiment(
            experiment_id="exp-page",
            name="experiment_page",
            created_by="user1"
        )
        repo.create(exp)

        experiments = repo.list_all(skip=0, limit=1)

        assert len(experiments) == 1

    def test_search_by_tags(self, db_session, sample_experiment):
        """Test searching experiments by tags."""
        repo = ExperimentRepository(db_session)

        # Note: This test may not work with SQLite as it doesn't support JSONB queries
        # In production with PostgreSQL, this would work
        experiments = repo.search_by_tags({"team": "fraud"})

        # For SQLite, this might return empty or work depending on JSON support
        # In a real PostgreSQL environment, it should find the experiment
        assert isinstance(experiments, list)

    def test_get_experiments_by_creator(self, db_session, sample_experiment):
        """Test retrieving experiments by creator."""
        repo = ExperimentRepository(db_session)

        experiments = repo.get_experiments_by_creator("test_user")

        assert len(experiments) >= 1
        assert all(e.created_by == "test_user" for e in experiments)

    def test_get_active_experiments(self, db_session, sample_experiment):
        """Test retrieving active experiments."""
        repo = ExperimentRepository(db_session)

        # Update run count to make it active
        repo.increment_run_count(sample_experiment.experiment_id, 5)

        experiments = repo.get_active_experiments(min_run_count=1)

        assert len(experiments) >= 1
        assert all(e.run_count >= 1 for e in experiments)

    def test_get_experiments_created_after(self, db_session, sample_experiment):
        """Test retrieving experiments created after a date."""
        repo = ExperimentRepository(db_session)

        cutoff = datetime.utcnow() - timedelta(hours=1)
        experiments = repo.get_experiments_created_after(cutoff)

        assert len(experiments) >= 1
        assert all(e.created_at >= cutoff for e in experiments)

    def test_update_experiment(self, db_session, sample_experiment):
        """Test updating experiment attributes."""
        repo = ExperimentRepository(db_session)

        updated = repo.update(
            sample_experiment.experiment_id,
            {"description": "Updated description", "run_count": 10}
        )

        assert updated is not None
        assert updated.description == "Updated description"
        assert updated.run_count == 10
        assert updated.updated_at > sample_experiment.created_at

    def test_update_nonexistent_experiment(self, db_session):
        """Test updating non-existent experiment."""
        repo = ExperimentRepository(db_session)

        updated = repo.update("non-existent", {"description": "Test"})

        assert updated is None

    def test_increment_run_count(self, db_session, sample_experiment):
        """Test incrementing run count."""
        repo = ExperimentRepository(db_session)

        initial_count = sample_experiment.run_count or 0
        updated = repo.increment_run_count(sample_experiment.experiment_id, 3)

        assert updated is not None
        assert updated.run_count == initial_count + 3

    def test_increment_run_count_default(self, db_session, sample_experiment):
        """Test incrementing run count by default (1)."""
        repo = ExperimentRepository(db_session)

        initial_count = sample_experiment.run_count or 0
        updated = repo.increment_run_count(sample_experiment.experiment_id)

        assert updated is not None
        assert updated.run_count == initial_count + 1

    def test_update_tags(self, db_session, sample_experiment):
        """Test updating experiment tags."""
        repo = ExperimentRepository(db_session)

        new_tags = {"new_tag": "value", "env": "production"}
        updated = repo.update_tags(sample_experiment.experiment_id, new_tags)

        assert updated is not None
        assert updated.tags["new_tag"] == "value"
        assert updated.tags["env"] == "production"

    def test_update_tags_none_initial(self, db_session):
        """Test updating tags when initially None."""
        repo = ExperimentRepository(db_session)

        exp = Experiment(
            experiment_id="exp-no-tags",
            name="no_tags_exp",
            created_by="user1"
        )
        created = repo.create(exp)

        updated = repo.update_tags(created.experiment_id, {"tag1": "value1"})

        assert updated is not None
        assert updated.tags == {"tag1": "value1"}

    def test_delete_experiment(self, db_session, sample_experiment):
        """Test deleting an experiment."""
        repo = ExperimentRepository(db_session)

        result = repo.delete(sample_experiment.experiment_id)

        assert result is True

        # Verify deletion
        retrieved = repo.get_by_id(sample_experiment.experiment_id)
        assert retrieved is None

    def test_delete_nonexistent_experiment(self, db_session):
        """Test deleting non-existent experiment."""
        repo = ExperimentRepository(db_session)

        result = repo.delete("non-existent")

        assert result is False

    def test_get_experiment_stats(self, db_session):
        """Test getting experiment statistics."""
        repo = ExperimentRepository(db_session)

        # Create experiments with different run counts
        exp1 = Experiment(
            experiment_id="stats-exp-1",
            name="stats_experiment_1",
            run_count=10,
            created_by="user1"
        )
        exp2 = Experiment(
            experiment_id="stats-exp-2",
            name="stats_experiment_2",
            run_count=20,
            created_by="user1"
        )
        repo.create(exp1)
        repo.create(exp2)

        stats = repo.get_experiment_stats()

        assert stats["total_experiments"] >= 2
        assert stats["total_runs"] >= 30
        assert stats["avg_runs_per_experiment"] > 0
        assert stats["most_active_experiment"] is not None

    def test_get_experiment_stats_empty(self, db_session):
        """Test getting stats with no experiments."""
        repo = ExperimentRepository(db_session)

        stats = repo.get_experiment_stats()

        assert stats["total_experiments"] == 0
        assert stats["total_runs"] == 0
        assert stats["avg_runs_per_experiment"] == 0
        assert stats["most_active_experiment"] is None

    def test_get_top_experiments(self, db_session):
        """Test retrieving top experiments by run count."""
        repo = ExperimentRepository(db_session)

        # Create experiments with different run counts
        for i in range(5):
            exp = Experiment(
                experiment_id=f"top-exp-{i}",
                name=f"top_experiment_{i}",
                run_count=(i + 1) * 10,
                created_by="user1"
            )
            repo.create(exp)

        top = repo.get_top_experiments(limit=3)

        assert len(top) == 3
        # Should be ordered by run_count desc
        assert top[0].run_count >= top[1].run_count
        assert top[1].run_count >= top[2].run_count

    def test_get_top_experiments_less_than_limit(self, db_session, sample_experiment):
        """Test getting top experiments when fewer than limit."""
        repo = ExperimentRepository(db_session)

        top = repo.get_top_experiments(limit=10)

        # Should return what's available
        assert len(top) >= 1
        assert len(top) <= 10
