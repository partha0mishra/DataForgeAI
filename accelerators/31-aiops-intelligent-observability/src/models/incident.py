"""Incident model."""
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    service = Column(String(100), nullable=False, index=True)
    root_cause = Column(JSON)
    auto_remediation = Column(JSON)
    status = Column(String(20), default='open')  # open, investigating, resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
