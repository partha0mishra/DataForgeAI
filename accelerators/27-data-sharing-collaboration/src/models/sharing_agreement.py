"""Sharing Agreement model."""
from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class SharingAgreement(Base):
    __tablename__ = "sharing_agreements"
    
    agreement_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_org = Column(String(200), nullable=False)
    consumer_org = Column(String(200), nullable=False)
    data_assets = Column(JSON)  # List of shared data assets
    terms = Column(JSON)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
