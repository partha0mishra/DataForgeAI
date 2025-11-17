"""AccessControl model."""
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class AccessControl(Base):
    __tablename__ = "access_controls"
    
    control_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    principal_id = Column(String(100), nullable=False, index=True)  # user, service, role
    principal_type = Column(String(50))
    resource_id = Column(String(100), nullable=False, index=True)
    permissions = Column(JSON)  # [read, write, delete, admin]
    conditions = Column(JSON)  # IP ranges, time windows, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
