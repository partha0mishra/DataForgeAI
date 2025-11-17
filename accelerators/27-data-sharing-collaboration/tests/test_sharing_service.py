"""Tests for Sharing Service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.sharing_agreement import Base, SharingAgreement
from src.services.sharing_service import SharingService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_sharing_agreement(db_session):
    """Test creating a sharing agreement."""
    service = SharingService(db_session)
    agreement = service.create_agreement(
        provider_org="OrgA",
        consumer_org="OrgB",
        data_assets=["dataset1", "dataset2"],
        terms={"duration_days": 365}
    )

    assert agreement.agreement_id is not None
    assert agreement.provider_org == "OrgA"
    assert agreement.consumer_org == "OrgB"
    assert agreement.active is True


def test_get_agreement(db_session):
    """Test retrieving a sharing agreement."""
    service = SharingService(db_session)
    agreement = service.create_agreement(
        provider_org="OrgA",
        consumer_org="OrgB",
        data_assets=["dataset1"],
        terms={}
    )

    retrieved = service.get_agreement(agreement.agreement_id)
    assert retrieved is not None
    assert retrieved.agreement_id == agreement.agreement_id


def test_deactivate_agreement(db_session):
    """Test deactivating a sharing agreement."""
    service = SharingService(db_session)
    agreement = service.create_agreement(
        provider_org="OrgA",
        consumer_org="OrgB",
        data_assets=["dataset1"],
        terms={}
    )

    service.deactivate_agreement(agreement.agreement_id)
    retrieved = service.get_agreement(agreement.agreement_id)
    assert retrieved.active is False
