"""DataProduct model."""
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class DataProduct(Base):
    __tablename__ = "data_products"
    
    product_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, unique=True)
    domain_id = Column(String(36), nullable=False, index=True)
    domain_name = Column(String(200), nullable=True)
    
    # Product metadata
    description = Column(Text, nullable=True)
    owner = Column(String(100), nullable=False)
    steward = Column(String(100), nullable=True)
    product_type = Column(String(50), nullable=False)  # dataset, api, stream, model
    
    # Access information
    access_type = Column(String(50), nullable=False)  # public, internal, restricted, confidential
    data_location = Column(String(500), nullable=False)
    format = Column(String(50), nullable=True)  # parquet, delta, iceberg, avro
    schema = Column(JSON, nullable=True)
    
    # Quality and SLAs
    quality_score = Column(Float, nullable=True)
    sla_tier = Column(String(20), nullable=True)  # bronze, silver, gold, platinum
    uptime_sla = Column(Float, nullable=True)  # Percentage
    latency_sla_ms = Column(Float, nullable=True)
    
    # Usage metrics
    consumer_count = Column(Float, default=0)
    query_count_daily = Column(Float, default=0)
    data_size_gb = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, index=True)  # draft, active, deprecated
    version = Column(String(20), nullable=True)
    
    # Metadata
    tags = Column(JSON, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_domain_status", "domain_id", "status"),
        Index("idx_product_type", "product_type"),
    )
