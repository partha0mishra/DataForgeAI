"""Experiment database model."""
from sqlalchemy import Column, String, JSON, Integer, Index
from src.models.base import Base, TimestampMixin


class Experiment(Base, TimestampMixin):
    """ML Experiment table."""
    
    __tablename__ = "experiments"
    
    # Primary Key
    experiment_id = Column(String(100), primary_key=True)
    
    # Basic Info
    name = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(String(1000))
    
    # MLflow Integration
    mlflow_experiment_id = Column(String(100), unique=True)
    
    # Metadata
    tags = Column(JSON, default=dict)
    artifact_location = Column(String(500))
    
    # Stats
    run_count = Column(Integer, default=0)
    
    # Owner
    created_by = Column(String(100))
    
    def __repr__(self):
        return f"<Experiment(experiment_id='{self.experiment_id}', name='{self.name}')>"
