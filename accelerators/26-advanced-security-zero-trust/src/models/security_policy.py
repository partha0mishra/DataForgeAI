"""SecurityPolicy model."""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class SecurityPolicy(Base):
    __tablename__ = "security_policies"
    
    policy_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, unique=True)
    policy_type = Column(String(50), nullable=False)  # authentication, authorization, encryption, network
    scope = Column(String(50))  # global, domain, resource
    rules = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True)
    priority = Column(Float, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
