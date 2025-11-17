"""ML Model database model."""
from sqlalchemy import Column, String, Integer, Float, JSON, Boolean, Index
from src.models.base import Base, TimestampMixin


class MLModel(Base, TimestampMixin):
    """ML Model table."""
    
    __tablename__ = "ml_models"
    
    # Primary Key
    model_id = Column(String(100), primary_key=True)
    
    # Basic Info
    name = Column(String(200), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    framework = Column(String(50), nullable=False)  # tensorflow, pytorch, sklearn, etc.
    algorithm = Column(String(100))
    
    # MLflow Integration
    mlflow_run_id = Column(String(100), unique=True, index=True)
    mlflow_model_uri = Column(String(500))
    mlflow_experiment_id = Column(String(100))
    
    # Model Metadata
    description = Column(String(1000))
    tags = Column(JSON, default=dict)
    parameters = Column(JSON, default=dict)
    
    # Performance Metrics
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    auc_roc = Column(Float)
    custom_metrics = Column(JSON, default=dict)
    
    # Status
    status = Column(String(50), nullable=False, default="registered")  # registered, deployed, archived
    is_production = Column(Boolean, default=False)
    
    # Storage
    artifact_path = Column(String(500))
    model_size_bytes = Column(Integer)
    
    # Owner
    created_by = Column(String(100))
    
    # Indexes
    __table_args__ = (
        Index('idx_model_name_version', 'name', 'version'),
        Index('idx_model_status', 'status'),
        Index('idx_model_production', 'is_production'),
    )
    
    def __repr__(self):
        return f"<MLModel(model_id='{self.model_id}', name='{self.name}', version='{self.version}')>"
