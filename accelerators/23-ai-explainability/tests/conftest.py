"""Pytest configuration and fixtures."""

import pytest
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Set test environment
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['ENVIRONMENT'] = 'test'

from src.database import Base, get_db
from src.models.explanation import Explanation
from src.models.bias_report import BiasReport
from src.models.trust_metric import TrustMetric
from src.models.hallucination_check import HallucinationCheck


@pytest.fixture(scope='function')
def test_db():
    """Create test database session."""
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False}
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_explanation(test_db):
    """Create sample explanation for testing."""
    explanation = Explanation(
        explanation_id='test-exp-1',
        model_id='test-model-1',
        model_name='Test Model',
        explanation_type='shap',
        scope='global',
        feature_importances={'age': 0.35, 'tenure': 0.28, 'purchases': 0.22},
        confidence=0.87,
        base_value=0.5,
        explanation_text='Test explanation',
        num_features=3,
        created_by='test_user'
    )
    test_db.add(explanation)
    test_db.commit()
    test_db.refresh(explanation)
    return explanation


@pytest.fixture
def sample_bias_report(test_db):
    """Create sample bias report for testing."""
    report = BiasReport(
        report_id='test-bias-1',
        model_id='test-model-1',
        model_name='Test Model',
        protected_attributes=['gender', 'age'],
        metrics_analyzed=['demographic_parity', 'equalized_odds'],
        bias_metrics={'demographic_parity': {'male': 0.8, 'female': 0.75}},
        overall_fairness_score=0.77,
        compliant=True,
        issues_detected=[],
        recommendations=['Continue monitoring'],
        severity='low',
        disparate_impact_ratio=0.85,
        dataset_size=1000,
        created_by='test_user'
    )
    test_db.add(report)
    test_db.commit()
    test_db.refresh(report)
    return report


@pytest.fixture
def sample_trust_metric(test_db):
    """Create sample trust metric for testing."""
    metric = TrustMetric(
        metric_id='test-trust-1',
        model_id='test-model-1',
        model_name='Test Model',
        explainability_score=0.82,
        fairness_score=0.75,
        robustness_score=0.70,
        privacy_score=0.80,
        transparency_score=0.72,
        accountability_score=0.68,
        overall_trust_score=0.75,
        trust_level='high',
        strengths=['explainability', 'privacy'],
        weaknesses=['robustness'],
        environment='production',
        assessed_by='test_user'
    )
    test_db.add(metric)
    test_db.commit()
    test_db.refresh(metric)
    return metric


@pytest.fixture
def sample_hallucination_check(test_db):
    """Create sample hallucination check for testing."""
    check = HallucinationCheck(
        check_id='test-halluc-1',
        model_name='gpt-4',
        model_version='0613',
        prompt='What is the capital of France?',
        output='The capital of France is Paris.',
        hallucination_risk='low',
        confidence_score=0.95,
        hallucination_score=0.10,
        hallucinated=False,
        detection_methods=['self_consistency', 'confidence'],
        severity='low',
        checked_by='test_user'
    )
    test_db.add(check)
    test_db.commit()
    test_db.refresh(check)
    return check


@pytest.fixture
def mock_model():
    """Create mock ML model for testing."""
    from sklearn.ensemble import RandomForestClassifier

    model = RandomForestClassifier(n_estimators=5, random_state=42)

    # Train on simple data
    X = np.array([[1, 2], [2, 3], [3, 4], [4, 5]])
    y = np.array([0, 0, 1, 1])
    model.fit(X, y)

    return model


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    return {
        'X': np.array([[1, 2, 3], [2, 3, 4], [3, 4, 5], [4, 5, 6]]),
        'y': np.array([0, 0, 1, 1]),
        'feature_names': ['feature_1', 'feature_2', 'feature_3'],
        'sensitive_features': np.array(['A', 'A', 'B', 'B'])
    }


@pytest.fixture
def mock_genai_response():
    """Mock GenAI API response."""
    return {
        'output': 'This is a test response from the GenAI model.',
        'confidence': 0.87,
        'reasoning': 'Based on the prompt, I generated this response.',
        'sources': ['test_source_1', 'test_source_2']
    }
