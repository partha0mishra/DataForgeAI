"""Tests for DR Service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.backup import Base, Backup
from src.services.dr_service import DRService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_backup(db_session):
    """Test creating a backup."""
    service = DRService(db_session)
    backup = service.create_backup(
        resource_id="prod-db-001",
        backup_type="full",
        region="us-east-1"
    )

    assert backup.backup_id is not None
    assert backup.resource_id == "prod-db-001"
    assert backup.backup_type == "full"
    assert backup.region == "us-east-1"
    assert backup.status == "completed"
    assert backup.verified is True
    assert backup.size_gb > 0


def test_failover_to_region(db_session):
    """Test failover to another region."""
    service = DRService(db_session)

    # Create some backups in failover region
    service.create_backup("resource1", "full", "us-west-2")
    service.create_backup("resource2", "full", "us-west-2")

    # Execute failover
    result = service.failover_to_region("us-east-1", "us-west-2")

    assert result["status"] == "success"
    assert result["failover_region"] == "us-west-2"
    assert result["available_backups"] == 2


def test_backup_verification(db_session):
    """Test backup verification status."""
    service = DRService(db_session)
    backup = service.create_backup("db1", "incremental", "us-east-1")

    assert backup.verified is True


def test_multiple_backups(db_session):
    """Test creating multiple backups."""
    service = DRService(db_session)

    backup1 = service.create_backup("db1", "full", "us-east-1")
    backup2 = service.create_backup("db1", "incremental", "us-east-1")
    backup3 = service.create_backup("db2", "full", "us-west-2")

    assert backup1.backup_id != backup2.backup_id
    assert backup2.backup_id != backup3.backup_id
    assert backup1.resource_id == backup2.resource_id
    assert backup1.resource_id != backup3.resource_id
