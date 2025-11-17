"""DataContract model."""
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class DataContract(Base):
    __tablename__ = "data_contracts"
    
    contract_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    schema_definition = Column(JSON, nullable=False)
    quality_rules = Column(JSON)
    sla_guarantees = Column(JSON)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
