"""Domain model."""
from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Domain(Base):
    __tablename__ = "domains"
    
    domain_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    owner = Column(String(100), nullable=False)
    business_area = Column(String(100))
    product_count = Column(Float, default=0)
    metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
