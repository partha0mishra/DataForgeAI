"""Pytest configuration and fixtures for MLOps Accelerator tests."""
import os
import sys
from typing import Generator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import Base, get_db
from src.main import app
from src.models.ml_model import MLModel
from src.models.deployment import Deployment
from src.models.experiment import Experiment
from src.models.drift_detection import DriftDetection


# Test database URL (in-memory SQLite for fast tests)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    return create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Create a new database session for a test.

    This fixture creates tables before the test and drops them after.
    Each test gets a fresh database.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ==================== Model Fixtures ====================

@pytest.fixture
def sample_model(db_session: Session) -> MLModel:
    """Create a sample ML model for testing."""
    model = MLModel(
        model_id="test-model-1",
        name="fraud_detector",
        version="1.0.0",
        framework="sklearn",
        algorithm="RandomForest",
        description="Test fraud detection model",
        status="registered",
        is_production=False,
        accuracy=0.95,
        precision=0.92,
        recall=0.89,
        f1_score=0.905,
        auc_roc=0.96,
        parameters={"n_estimators": 100, "max_depth": 10},
        tags={"team": "fraud", "env": "test"},
        custom_metrics={"specificity": 0.94},
        created_by="test_user"
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def production_model(db_session: Session) -> MLModel:
    """Create a production ML model for testing."""
    model = MLModel(
        model_id="test-model-prod",
        name="fraud_detector",
        version="2.0.0",
        framework="sklearn",
        algorithm="XGBoost",
        status="deployed",
        is_production=True,
        accuracy=0.97,
        precision=0.95,
        recall=0.93,
        f1_score=0.94,
        auc_roc=0.98,
        created_by="test_user"
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def sample_deployment(db_session: Session, sample_model: MLModel) -> Deployment:
    """Create a sample deployment for testing."""
    deployment = Deployment(
        deployment_id="test-deployment-1",
        model_id=sample_model.model_id,
        deployment_name="fraud-detector-staging",
        environment="staging",
        strategy="rolling",
        status="running",
        health_status="healthy",
        replicas=2,
        resource_config={"cpu": "1000m", "memory": "2Gi"},
        traffic_percentage=100,
        request_count=1000,
        error_count=5,
        avg_latency_ms=50,
        deployed_by="test_user",
        deployed_at=datetime.utcnow()
    )
    db_session.add(deployment)
    db_session.commit()
    db_session.refresh(deployment)
    return deployment


@pytest.fixture
def canary_deployment(db_session: Session, sample_model: MLModel) -> Deployment:
    """Create a canary deployment for testing."""
    deployment = Deployment(
        deployment_id="test-canary-1",
        model_id=sample_model.model_id,
        deployment_name="fraud-detector-canary",
        environment="production",
        strategy="canary",
        status="running",
        health_status="healthy",
        replicas=3,
        traffic_percentage=10,
        deployed_by="test_user",
        deployed_at=datetime.utcnow()
    )
    db_session.add(deployment)
    db_session.commit()
    db_session.refresh(deployment)
    return deployment


@pytest.fixture
def sample_experiment(db_session: Session) -> Experiment:
    """Create a sample experiment for testing."""
    experiment = Experiment(
        experiment_id="test-exp-1",
        name="fraud_detection_v1",
        description="Test experiment for fraud detection",
        mlflow_experiment_id="12345",
        tags={"team": "fraud", "priority": "high"},
        artifact_location="s3://test-bucket/experiments",
        run_count=5,
        created_by="test_user"
    )
    db_session.add(experiment)
    db_session.commit()
    db_session.refresh(experiment)
    return experiment


@pytest.fixture
def sample_drift_detection(db_session: Session, sample_model: MLModel) -> DriftDetection:
    """Create a sample drift detection for testing."""
    drift = DriftDetection(
        drift_id="test-drift-1",
        model_id=sample_model.model_id,
        detection_timestamp=datetime.utcnow(),
        drift_type="data_drift",
        drift_score=0.12,
        threshold=0.05,
        is_drift_detected=True,
        affected_features=[
            {"name": "amount", "p_value": 0.02, "ks_statistic": 0.15},
            {"name": "frequency", "p_value": 0.03, "ks_statistic": 0.12}
        ],
        statistical_tests={
            "amount": {"test": "ks", "statistic": 0.15, "p_value": 0.02},
            "frequency": {"test": "ks", "statistic": 0.12, "p_value": 0.03}
        },
        severity="medium",
        recommendations=[
            "Medium severity drift detected. Schedule model retraining.",
            "Investigate root causes of drift.",
            "Most affected features: amount, frequency"
        ],
        detection_method="kolmogorov_smirnov",
        auto_retrain_triggered=False
    )
    db_session.add(drift)
    db_session.commit()
    db_session.refresh(drift)
    return drift


# ==================== Mock MLflow Fixtures ====================

@pytest.fixture
def mock_mlflow_client(monkeypatch):
    """Mock MLflow client for testing without real MLflow server."""
    class MockRun:
        def __init__(self):
            self.info = type('obj', (object,), {
                'run_id': 'mock-run-123',
                'experiment_id': 'mock-exp-456',
                'start_time': 1640000000000
            })()
            self.data = type('obj', (object,), {
                'metrics': {
                    'accuracy': 0.95,
                    'precision': 0.92,
                    'recall': 0.89,
                    'f1_score': 0.905
                },
                'params': {
                    'framework': 'sklearn',
                    'algorithm': 'RandomForest',
                    'n_estimators': '100'
                },
                'tags': {
                    'mlflow.user': 'test_user',
                    'mlflow.note.content': 'Test model description'
                }
            })()

    class MockExperiment:
        def __init__(self):
            self.name = "test_experiment"
            self.experiment_id = "mock-exp-456"
            self.artifact_location = "s3://test-bucket/mlflow"
            self.tags = {"env": "test"}

    class MockMlflowClient:
        def get_run(self, run_id):
            return MockRun()

        def get_experiment(self, experiment_id):
            return MockExperiment()

        def search_runs(self, experiment_ids):
            return [MockRun() for _ in range(3)]

    # Mock MLflow availability
    import src.services.mlops_service as mlops_module
    import src.services.experiment_service as exp_module

    monkeypatch.setattr(mlops_module, 'MLFLOW_AVAILABLE', True)
    monkeypatch.setattr(exp_module, 'MLFLOW_AVAILABLE', True)
    monkeypatch.setattr(mlops_module, 'MlflowClient', MockMlflowClient)
    monkeypatch.setattr(exp_module, 'MlflowClient', MockMlflowClient)

    return MockMlflowClient()


# ==================== Utility Fixtures ====================

@pytest.fixture
def sample_drift_data():
    """Sample data for drift detection testing."""
    import numpy as np
    return {
        "reference_data": np.random.normal(0, 1, (100, 3)),
        "current_data": np.random.normal(0.5, 1, (100, 3)),  # Shifted distribution
        "feature_names": ["feature1", "feature2", "feature3"]
    }


@pytest.fixture
def cleanup_test_data(db_session):
    """Cleanup fixture to remove test data after tests."""
    yield
    # Cleanup is handled by db_session fixture dropping tables
    pass
