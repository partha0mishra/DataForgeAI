"""Drift Detection database model."""
from sqlalchemy import Column, String, Float, JSON, ForeignKey, DateTime, Boolean, Index
from src.models.base import Base, TimestampMixin


class DriftDetection(Base, TimestampMixin):
    """Model Drift Detection table."""
    
    __tablename__ = "drift_detections"
    
    # Primary Key
    drift_id = Column(String(100), primary_key=True)
    
    # Foreign Key
    model_id = Column(String(100), ForeignKey('ml_models.model_id'), nullable=False, index=True)
    deployment_id = Column(String(100), ForeignKey('deployments.deployment_id'), index=True)
    
    # Drift Analysis
    detection_timestamp = Column(DateTime, nullable=False, index=True)
    drift_type = Column(String(50), nullable=False)  # data_drift, concept_drift, prediction_drift
    
    # Metrics
    drift_score = Column(Float, nullable=False)  # 0-1 score
    threshold = Column(Float, default=0.7)
    is_drift_detected = Column(Boolean, default=False)
    
    # Details
    affected_features = Column(JSON, default=list)  # List of features with drift
    statistical_tests = Column(JSON, default=dict)  # KS test, chi-square, etc.
    comparison_window = Column(String(100))  # "last_7_days", "last_1000_predictions"
    
    # Recommendations
    severity = Column(String(20))  # low, medium, high, critical
    recommendations = Column(JSON, default=list)
    auto_retrain_triggered = Column(Boolean, default=False)
    
    # Metadata
    detection_method = Column(String(100))  # evidently, alibi_detect, custom
    config = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('idx_drift_model_timestamp', 'model_id', 'detection_timestamp'),
        Index('idx_drift_detected', 'is_drift_detected'),
    )
    
    def __repr__(self):
        return f"<DriftDetection(drift_id='{self.drift_id}', model_id='{self.model_id}', score={self.drift_score})>"
