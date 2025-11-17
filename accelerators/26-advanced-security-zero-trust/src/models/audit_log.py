"""AuditLog model."""
from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    log_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action = Column(String(50), nullable=False, index=True)
    principal = Column(String(100), nullable=False)
    resource = Column(String(200))
    result = Column(String(20))  # success, failure, denied
    details = Column(JSON)
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
