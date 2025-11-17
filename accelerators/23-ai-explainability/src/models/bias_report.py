"""BiasReport model for storing fairness analysis."""

from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class BiasReport(Base):
    """Model for storing bias and fairness analysis reports."""

    __tablename__ = "bias_reports"

    # Primary identification
    report_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(100), nullable=False, index=True)
    model_name = Column(String(200), nullable=True)

    # Analysis configuration
    protected_attributes = Column(JSON, nullable=False)  # List of attributes analyzed
    reference_group = Column(String(100), nullable=True)  # Reference group for comparison
    metrics_analyzed = Column(
        JSON, nullable=False
    )  # ['demographic_parity', 'equalized_odds', ...]

    # Bias metrics results
    bias_metrics = Column(
        JSON, nullable=False
    )  # {metric_name: {group: value}} e.g., {'demographic_parity': {'male': 0.8, 'female': 0.6}}
    overall_fairness_score = Column(
        Float, nullable=False
    )  # 0-1, higher is better (weighted average)

    # Compliance and issues
    compliant = Column(Boolean, default=False, nullable=False)
    issues_detected = Column(JSON, nullable=True)  # List of detected bias issues
    recommendations = Column(JSON, nullable=True)  # List of remediation recommendations
    severity = Column(String(20), nullable=True)  # 'low', 'medium', 'high', 'critical'

    # Detailed analysis
    group_statistics = Column(
        JSON, nullable=True
    )  # Detailed stats per group: {group: {metric: value}}
    disparate_impact_ratio = Column(Float, nullable=True)  # 80% rule compliance
    statistical_parity_difference = Column(Float, nullable=True)

    # Data characteristics
    dataset_size = Column(Float, nullable=True)  # Number of samples analyzed
    group_distributions = Column(
        JSON, nullable=True
    )  # Distribution of samples per group: {group: count}

    # Interpretation
    summary_text = Column(Text, nullable=True)  # Executive summary
    detailed_findings = Column(Text, nullable=True)  # Detailed analysis
    visualization_urls = Column(JSON, nullable=True)  # URLs to bias visualization plots

    # Performance
    analysis_duration_ms = Column(Float, nullable=True)

    # Audit fields
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_model_compliant", "model_id", "compliant"),
        Index("idx_created_at", "created_at"),
        Index("idx_severity", "severity"),
        Index("idx_fairness_score", "overall_fairness_score"),
    )

    def __repr__(self):
        return f"<BiasReport(id={self.report_id}, model={self.model_id}, fairness={self.overall_fairness_score:.2f})>"
