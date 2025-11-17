"""Tests for AIOps Service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.incident import Base, Incident
from src.services.aiops_service import AIOpsService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_detect_incident(db_session):
    """Test detecting an incident."""
    service = AIOpsService(db_session)
    incident = service.detect_incident(
        title="High CPU Usage",
        severity="high",
        service="api-server"
    )

    assert incident.incident_id is not None
    assert incident.title == "High CPU Usage"
    assert incident.severity == "high"
    assert incident.service == "api-server"


def test_auto_remediation_low_severity(db_session):
    """Test auto-remediation for low severity incident."""
    service = AIOpsService(db_session)
    incident = service.detect_incident(
        title="Minor Memory Leak",
        severity="low",
        service="worker"
    )

    assert incident.auto_remediation is not None
    assert incident.auto_remediation["action"] == "restart_service"
    assert incident.auto_remediation["applied"] is True
    assert incident.status == "resolved"


def test_no_auto_remediation_high_severity(db_session):
    """Test no auto-remediation for high severity incident."""
    service = AIOpsService(db_session)
    incident = service.detect_incident(
        title="Database Down",
        severity="critical",
        service="database"
    )

    assert incident.status == "open"
    assert incident.auto_remediation is None


def test_analyze_root_cause(db_session):
    """Test root cause analysis."""
    service = AIOpsService(db_session)

    # Create incident
    incident = service.detect_incident("CPU Spike", "high", "api")

    # Analyze root cause
    analyzed = service.analyze_root_cause(incident.incident_id)

    assert analyzed is not None
    assert analyzed.root_cause is not None
    assert "category" in analyzed.root_cause
    assert "confidence" in analyzed.root_cause
