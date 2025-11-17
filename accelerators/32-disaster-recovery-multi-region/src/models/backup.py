"""Backup model."""
from sqlalchemy import Column, String, DateTime, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Backup(Base):
    __tablename__ = "backups"

    backup_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_id = Column(String(100), nullable=False, index=True)
    backup_type = Column(String(20), nullable=False)  # full, incremental, differential
    region = Column(String(50), nullable=False)
    size_gb = Column(Float, nullable=False)
    status = Column(String(20), default='pending')  # pending, completed, failed
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
