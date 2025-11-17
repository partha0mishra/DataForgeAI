"""TrustMetric model for storing trust scorecards."""

from sqlalchemy import Column, String, Float, DateTime, JSON, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class TrustMetric(Base):
    """Model for storing comprehensive trust metrics for AI models."""

    __tablename__ = "trust_metrics"

    # Primary identification
    metric_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(100), nullable=False, index=True)
    model_name = Column(String(200), nullable=True)

    # Core trust dimensions (0-1 scale)
    explainability_score = Column(
        Float, nullable=False
    )  # How well model decisions can be explained
    fairness_score = Column(Float, nullable=False)  # Absence of bias
    robustness_score = Column(Float, nullable=False)  # Performance under adversarial conditions
    privacy_score = Column(Float, nullable=False)  # Data privacy and protection
    transparency_score = Column(Float, nullable=True)  # Model transparency and documentation
    accountability_score = Column(Float, nullable=True)  # Audit trail and governance

    # Overall assessment
    overall_trust_score = Column(
        Float, nullable=False
    )  # Weighted average of dimensions (0-1)
    trust_level = Column(String(20), nullable=False)  # 'high', 'medium', 'low', 'critical'

    # Dimension details
    dimension_details = Column(
        JSON, nullable=True
    )  # Detailed breakdown: {dimension: {subdimension: score}}
    weights = Column(JSON, nullable=True)  # Weights used in calculation

    # Assessment context
    assessment_type = Column(String(50), nullable=True)  # 'periodic', 'pre_deployment', 'incident'
    assessment_criteria = Column(JSON, nullable=True)  # Criteria and thresholds used
    regulatory_framework = Column(
        String(100), nullable=True
    )  # e.g., 'EU_AI_Act', 'NIST_AI_RMF'

    # Findings and recommendations
    strengths = Column(JSON, nullable=True)  # List of trust strengths
    weaknesses = Column(JSON, nullable=True)  # List of trust concerns
    recommendations = Column(JSON, nullable=True)  # Improvement recommendations
    certification_status = Column(
        String(50), nullable=True
    )  # 'certified', 'pending', 'not_certified'

    # Historical tracking
    previous_score = Column(Float, nullable=True)  # Previous overall trust score
    score_trend = Column(String(20), nullable=True)  # 'improving', 'stable', 'declining'
    changes_since_last = Column(
        JSON, nullable=True
    )  # {dimension: {old_score, new_score, change}}

    # Documentation
    summary_text = Column(Text, nullable=True)  # Executive summary
    detailed_report = Column(Text, nullable=True)  # Detailed assessment
    visualization_urls = Column(JSON, nullable=True)  # URLs to trust scorecard visualizations

    # Metadata
    model_version = Column(String(50), nullable=True)
    environment = Column(String(50), nullable=True)  # 'dev', 'staging', 'production'

    # Audit fields
    assessed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_model_trust_level", "model_id", "trust_level"),
        Index("idx_created_at", "created_at"),
        Index("idx_overall_score", "overall_trust_score"),
        Index("idx_environment", "environment"),
    )

    def __repr__(self):
        return f"<TrustMetric(id={self.metric_id}, model={self.model_id}, trust={self.trust_level}, score={self.overall_trust_score:.2f})>"
