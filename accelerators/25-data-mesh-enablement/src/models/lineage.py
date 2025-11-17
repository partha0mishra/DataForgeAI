"""DataLineage model."""
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class DataLineage(Base):
    __tablename__ = "data_lineage"
    
    lineage_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_product_id = Column(String(36), nullable=False, index=True)
    target_product_id = Column(String(36), nullable=False, index=True)
    lineage_type = Column(String(50))  # direct, derived, aggregated
    transformation_logic = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
