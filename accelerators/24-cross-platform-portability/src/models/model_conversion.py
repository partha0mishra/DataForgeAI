"""ModelConversion model for tracking model format conversions."""

from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class ModelConversion(Base):
    """Model for tracking ML model format conversions."""

    __tablename__ = "model_conversions"

    # Primary identification
    conversion_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String(100), nullable=False, index=True)
    model_name = Column(String(200), nullable=True)

    # Source information
    source_uri = Column(String(500), nullable=False)
    source_format = Column(String(50), nullable=False)  # onnx, pmml, mlflow, tensorflow, pytorch, etc.
    source_platform = Column(String(50), nullable=True)
    source_size_mb = Column(Float, nullable=True)

    # Target information
    target_format = Column(String(50), nullable=False)
    target_platform = Column(String(50), nullable=False)  # databricks, snowflake, bigquery, etc.
    target_uri = Column(String(500), nullable=True)
    target_size_mb = Column(Float, nullable=True)

    # Conversion configuration
    optimization_level = Column(String(20), nullable=True)  # none, basic, aggressive
    preserve_metadata = Column(Boolean, default=True)
    conversion_options = Column(JSON, nullable=True)

    # Conversion results
    status = Column(String(20), nullable=False, index=True)  # pending, in_progress, completed, failed
    download_url = Column(String(500), nullable=True)
    metadata_preserved = Column(Boolean, default=True)

    # Quality metrics
    conversion_warnings = Column(JSON, nullable=True)  # List of warnings
    conversion_errors = Column(JSON, nullable=True)  # List of errors
    accuracy_degradation = Column(Float, nullable=True)  # Percentage
    performance_metrics = Column(JSON, nullable=True)  # {latency_ms, throughput, memory_mb}

    # Model metadata
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    model_signature = Column(JSON, nullable=True)
    framework_version = Column(String(50), nullable=True)

    # Performance
    conversion_duration_ms = Column(Float, nullable=True)
    estimated_inference_latency_ms = Column(Float, nullable=True)

    # Validation
    validation_passed = Column(Boolean, default=False)
    validation_metrics = Column(JSON, nullable=True)
    test_predictions = Column(JSON, nullable=True)

    # Audit fields
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_model_status", "model_id", "status"),
        Index("idx_target_platform", "target_platform"),
        Index("idx_created_at", "created_at"),
        Index("idx_source_target", "source_format", "target_format"),
    )

    def __repr__(self):
        return f"<ModelConversion(id={self.conversion_id}, {self.source_format}→{self.target_format}, status={self.status})>"
