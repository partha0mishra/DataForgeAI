"""Deployment database model."""
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from src.models.base import Base, TimestampMixin


class Deployment(Base, TimestampMixin):
    """Model Deployment table."""
    
    __tablename__ = "deployments"
    
    # Primary Key
    deployment_id = Column(String(100), primary_key=True)
    
    # Foreign Key to ML Model
    model_id = Column(String(100), ForeignKey('ml_models.model_id'), nullable=False, index=True)
    
    # Deployment Info
    deployment_name = Column(String(200), nullable=False)
    environment = Column(String(50), nullable=False)  # dev, staging, production
    strategy = Column(String(50), nullable=False)  # blue_green, canary, rolling, shadow
    
    # Status
    status = Column(String(50), nullable=False, default="pending")  # pending, deploying, deployed, failed, rollback
    health_status = Column(String(50), default="unknown")  # healthy, degraded, unhealthy
    
    # Configuration
    replicas = Column(Integer, default=1)
    resource_config = Column(JSON, default=dict)  # CPU, memory, GPU
    endpoint_url = Column(String(500))
    
    # Deployment Strategy Specific
    traffic_percentage = Column(Integer, default=100)  # For canary deployments
    rollout_config = Column(JSON, default=dict)
    
    # Timestamps
    deployed_at = Column(DateTime)
    last_health_check = Column(DateTime)
    
    # Metrics
    request_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    avg_latency_ms = Column(Integer)
    
    # Metadata
    deployed_by = Column(String(100))
    deployment_notes = Column(String(1000))
    tags = Column(JSON, default=dict)
    
    # Relationship
    # model = relationship("MLModel", backref="deployments")
    
    # Indexes
    __table_args__ = (
        Index('idx_deployment_model', 'model_id'),
        Index('idx_deployment_environment', 'environment'),
        Index('idx_deployment_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Deployment(deployment_id='{self.deployment_id}', model_id='{self.model_id}', status='{self.status}')>"
