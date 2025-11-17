"""Explanation model for storing model explanations."""

from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class Explanation(Base):
    """Model for storing ML model explanations (SHAP, LIME, etc.)."""

    __tablename__ = "explanations"

    # Primary identification
    explanation_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(100), nullable=False, index=True)
    model_name = Column(String(200), nullable=True)

    # Explanation metadata
    explanation_type = Column(
        String(50), nullable=False
    )  # 'shap', 'lime', 'alibi', 'counterfactual', 'feature_importance'
    scope = Column(String(20), nullable=False)  # 'global' or 'local'

    # Explanation data
    feature_importances = Column(JSON, nullable=False)  # {feature_name: importance_value}
    prediction = Column(JSON, nullable=True)  # Model prediction for local explanations
    confidence = Column(Float, nullable=True)  # Prediction confidence
    base_value = Column(Float, nullable=True)  # Base/expected value for SHAP

    # Instance data (for local explanations)
    instance_data = Column(JSON, nullable=True)  # The input instance that was explained
    instance_id = Column(String(100), nullable=True, index=True)

    # Visualization and interpretation
    explanation_text = Column(Text, nullable=True)  # Human-readable explanation
    visualization_urls = Column(JSON, nullable=True)  # List of URLs to plots/charts
    metadata = Column(JSON, nullable=True)  # Additional metadata

    # Performance tracking
    generation_time_ms = Column(Float, nullable=True)  # Time to generate explanation
    num_features = Column(Float, nullable=True)  # Number of features explained

    # Audit fields
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_model_type", "model_id", "explanation_type"),
        Index("idx_created_at", "created_at"),
        Index("idx_scope", "scope"),
    )

    def __repr__(self):
        return f"<Explanation(id={self.explanation_id}, model={self.model_id}, type={self.explanation_type})>"
