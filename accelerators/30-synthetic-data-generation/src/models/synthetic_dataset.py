"""Synthetic dataset model."""
from sqlalchemy import Column, String, DateTime, JSON, Integer, Float
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class SyntheticDataset(Base):
    __tablename__ = "synthetic_datasets"

    dataset_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    generation_method = Column(String(50), nullable=False)  # gan, vae, smote, faker
    source_schema = Column(JSON)
    constraints = Column(JSON)  # Privacy constraints, distributions
    num_records = Column(Integer, nullable=False)
    quality_score = Column(Float)
    privacy_score = Column(Float)  # Differential privacy epsilon
    status = Column(String(20), default='pending')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
