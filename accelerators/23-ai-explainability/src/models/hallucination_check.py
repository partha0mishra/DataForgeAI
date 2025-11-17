"""HallucinationCheck model for GenAI output verification."""

from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class HallucinationCheck(Base):
    """Model for storing GenAI hallucination detection results."""

    __tablename__ = "hallucination_checks"

    # Primary identification
    check_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name = Column(String(200), nullable=False, index=True)
    model_version = Column(String(50), nullable=True)

    # Input/Output
    prompt = Column(Text, nullable=False)  # The input prompt
    output = Column(Text, nullable=False)  # The generated output
    prompt_hash = Column(String(64), nullable=True, index=True)  # For deduplication

    # Hallucination analysis
    hallucination_risk = Column(
        String(20), nullable=False
    )  # 'none', 'low', 'medium', 'high', 'critical'
    confidence_score = Column(Float, nullable=False)  # Model's confidence in the output (0-1)
    hallucination_score = Column(
        Float, nullable=False
    )  # Hallucination detector's score (0-1, higher = more likely hallucinated)

    # Reasoning and attribution
    reasoning = Column(Text, nullable=True)  # Chain-of-thought explanation
    prompt_attribution = Column(
        JSON, nullable=True
    )  # {prompt_segment: influence_weight} - which parts of prompt influenced output

    # Fact checking
    fact_checks = Column(
        JSON, nullable=True
    )  # List of fact check results: [{claim, verified, source, confidence}]
    sources = Column(JSON, nullable=True)  # List of sources/references used
    grounding_quality = Column(Float, nullable=True)  # How well grounded in sources (0-1)

    # Detection methods
    detection_methods = Column(
        JSON, nullable=True
    )  # Methods used: ['self_consistency', 'knowledge_retrieval', 'perplexity']
    detection_details = Column(
        JSON, nullable=True
    )  # Detailed results from each detection method

    # Flags and issues
    hallucinated = Column(Boolean, default=False, nullable=False)
    issues_detected = Column(JSON, nullable=True)  # List of specific hallucination issues
    severity = Column(String(20), nullable=True)  # 'low', 'medium', 'high', 'critical'

    # Recommendations
    recommendations = Column(
        JSON, nullable=True
    )  # Recommendations for improving output quality
    alternative_responses = Column(JSON, nullable=True)  # Suggested alternative responses

    # Context
    domain = Column(String(100), nullable=True)  # Domain/topic of the query
    use_case = Column(String(100), nullable=True)  # e.g., 'customer_support', 'content_generation'
    user_context = Column(JSON, nullable=True)  # Additional user/session context

    # Performance
    check_duration_ms = Column(Float, nullable=True)  # Time to perform check

    # Explanation
    explanation_text = Column(Text, nullable=True)  # Human-readable explanation of findings
    visualization_urls = Column(JSON, nullable=True)  # URLs to attention/attribution visualizations

    # Audit fields
    checked_by = Column(String(100), nullable=True)  # User or system that requested check
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_model_risk", "model_name", "hallucination_risk"),
        Index("idx_created_at", "created_at"),
        Index("idx_hallucinated", "hallucinated"),
        Index("idx_severity", "severity"),
    )

    def __repr__(self):
        return f"<HallucinationCheck(id={self.check_id}, model={self.model_name}, risk={self.hallucination_risk})>"
