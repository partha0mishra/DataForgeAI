"""Tests for Synthesis Service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.synthetic_dataset import Base, SyntheticDataset
from src.services.synthesis_service import SynthesisService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_generate_dataset(db_session):
    """Test generating synthetic dataset."""
    service = SynthesisService(db_session)
    dataset = service.generate_dataset(
        name="Test Dataset",
        method="faker",
        schema={"columns": ["name", "email", "age"]},
        num_records=1000,
        constraints={"min_age": 18}
    )

    assert dataset.dataset_id is not None
    assert dataset.name == "Test Dataset"
    assert dataset.generation_method == "faker"
    assert dataset.num_records == 1000
    assert dataset.status == "completed"
    assert dataset.quality_score is not None


def test_validate_synthetic_data(db_session):
    """Test validating synthetic data."""
    service = SynthesisService(db_session)

    # Generate dataset first
    dataset = service.generate_dataset("Test", "faker", {}, 100, {})

    # Validate
    validated = service.validate_synthetic_data(dataset.dataset_id)

    assert validated is not None
    assert validated.quality_score is not None
    assert validated.quality_score > 0


def test_privacy_score(db_session):
    """Test privacy score assignment."""
    service = SynthesisService(db_session)
    dataset = service.generate_dataset("Test", "faker", {}, 100, {})

    assert dataset.privacy_score is not None
    assert 0 <= dataset.privacy_score <= 1.0
