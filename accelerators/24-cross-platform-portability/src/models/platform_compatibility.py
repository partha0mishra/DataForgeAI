"""PlatformCompatibility model for compatibility analysis."""

from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class PlatformCompatibility(Base):
    """Model for platform compatibility analysis results."""

    __tablename__ = "platform_compatibility"

    # Primary identification
    analysis_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_id = Column(String(100), nullable=False, index=True)  # Model, pipeline, or query ID
    resource_type = Column(String(50), nullable=False)  # model, pipeline, query, table
    resource_name = Column(String(200), nullable=True)

    # Source information
    source_platform = Column(String(50), nullable=False, index=True)
    source_uri = Column(String(500), nullable=True)

    # Compatibility results
    target_platforms = Column(JSON, nullable=False)  # List of platforms analyzed
    platform_compatibility = Column(JSON, nullable=False)  # {platform: {compatible, blockers, warnings}}

    # Recommendations
    recommended_platform = Column(String(50), nullable=True)
    recommended_format = Column(String(50), nullable=True)
    portability_score = Column(Float, nullable=True)  # 0-1
    migration_effort = Column(String(20), nullable=True)  # low, medium, high, very_high

    # Analysis details
    compatibility_matrix = Column(JSON, nullable=True)  # Detailed compatibility info
    feature_support = Column(JSON, nullable=True)  # {feature: [supported_platforms]}
    blockers = Column(JSON, nullable=True)  # List of blocking issues
    warnings = Column(JSON, nullable=True)  # List of warnings

    # Migration guidance
    migration_steps = Column(JSON, nullable=True)
    estimated_migration_hours = Column(Float, nullable=True)
    required_changes = Column(JSON, nullable=True)
    risk_level = Column(String(20), nullable=True)  # low, medium, high, critical

    # Platform-specific details
    platform_features = Column(JSON, nullable=True)
    platform_limitations = Column(JSON, nullable=True)
    platform_costs = Column(JSON, nullable=True)  # Estimated costs per platform

    # Performance comparison
    performance_comparison = Column(JSON, nullable=True)  # {platform: {latency, throughput, cost}}
    scalability_comparison = Column(JSON, nullable=True)

    # Metadata
    analysis_duration_ms = Column(Float, nullable=True)
    analysis_version = Column(String(20), nullable=True)

    # Audit fields
    analyzed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("idx_resource_type", "resource_id", "resource_type"),
        Index("idx_source_platform", "source_platform"),
        Index("idx_created_at", "created_at"),
        Index("idx_portability_score", "portability_score"),
    )

    def __repr__(self):
        return f"<PlatformCompatibility(id={self.analysis_id}, resource={self.resource_id}, score={self.portability_score})>"
