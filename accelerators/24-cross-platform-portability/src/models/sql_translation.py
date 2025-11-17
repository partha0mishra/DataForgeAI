"""SQLTranslation model for cross-platform SQL translation."""

from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid
import hashlib

Base = declarative_base()


class SQLTranslation(Base):
    """Model for tracking SQL translations across platforms."""

    __tablename__ = "sql_translations"

    # Primary identification
    translation_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_hash = Column(String(64), nullable=True, index=True)  # For deduplication

    # Source SQL
    source_sql = Column(Text, nullable=False)
    source_platform = Column(String(50), nullable=False, index=True)
    source_dialect = Column(String(50), nullable=True)

    # Target SQL
    target_sql = Column(Text, nullable=True)
    target_platform = Column(String(50), nullable=False, index=True)
    target_dialect = Column(String(50), nullable=True)

    # Translation configuration
    validate_equivalence = Column(Boolean, default=True)
    preserve_formatting = Column(Boolean, default=False)
    translation_options = Column(JSON, nullable=True)

    # Translation results
    status = Column(String(20), nullable=False, index=True)  # pending, completed, failed
    equivalence_guaranteed = Column(Boolean, default=False)
    confidence_score = Column(Float, nullable=True)  # 0-1

    # Analysis
    translation_notes = Column(JSON, nullable=True)  # List of notes
    optimization_opportunities = Column(JSON, nullable=True)
    compatibility_issues = Column(JSON, nullable=True)
    unsupported_features = Column(JSON, nullable=True)

    # Complexity metrics
    query_complexity = Column(String(20), nullable=True)  # simple, moderate, complex
    estimated_execution_time_source = Column(Float, nullable=True)
    estimated_execution_time_target = Column(Float, nullable=True)
    performance_impact = Column(String(20), nullable=True)  # improved, neutral, degraded

    # Query characteristics
    query_type = Column(String(50), nullable=True)  # SELECT, INSERT, UPDATE, DELETE, DDL
    tables_referenced = Column(JSON, nullable=True)
    functions_used = Column(JSON, nullable=True)
    joins_count = Column(Float, nullable=True)

    # Validation
    syntax_valid = Column(Boolean, default=False)
    semantic_valid = Column(Boolean, default=False)
    test_results = Column(JSON, nullable=True)

    # Performance
    translation_duration_ms = Column(Float, nullable=True)

    # Usage tracking
    execution_count = Column(Float, default=0)
    last_executed = Column(DateTime(timezone=True), nullable=True)

    # Audit fields
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("idx_platform_translation", "source_platform", "target_platform"),
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<SQLTranslation(id={self.translation_id}, {self.source_platform}→{self.target_platform})>"

    def generate_query_hash(self):
        """Generate hash for query deduplication."""
        normalized = self.source_sql.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()
