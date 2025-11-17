"""TableConversion model for table format conversions."""

from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Index, Text, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class TableConversion(Base):
    """Model for tracking table format conversions."""

    __tablename__ = "table_conversions"

    # Primary identification
    conversion_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    table_name = Column(String(200), nullable=False, index=True)
    database_name = Column(String(200), nullable=True)
    schema_name = Column(String(200), nullable=True)

    # Source information
    source_path = Column(String(500), nullable=False)
    source_format = Column(String(50), nullable=False)  # iceberg, delta_lake, hudi, parquet, avro, orc
    source_platform = Column(String(50), nullable=True)
    source_size_mb = Column(Float, nullable=True)
    source_row_count = Column(BigInteger, nullable=True)

    # Target information
    target_path = Column(String(500), nullable=True)
    target_format = Column(String(50), nullable=False)
    target_platform = Column(String(50), nullable=True)
    target_size_mb = Column(Float, nullable=True)
    target_row_count = Column(BigInteger, nullable=True)

    # Conversion configuration
    preserve_partitioning = Column(Boolean, default=True)
    preserve_stats = Column(Boolean, default=True)
    preserve_metadata = Column(Boolean, default=True)
    compression_codec = Column(String(50), nullable=True)
    conversion_options = Column(JSON, nullable=True)

    # Table metadata
    schema = Column(JSON, nullable=True)  # Table schema definition
    partitions = Column(JSON, nullable=True)  # Partition columns and values
    sort_order = Column(JSON, nullable=True)
    table_properties = Column(JSON, nullable=True)

    # Conversion results
    status = Column(String(20), nullable=False, index=True)  # pending, in_progress, completed, failed
    partitions_converted = Column(Float, nullable=True)
    total_partitions = Column(Float, nullable=True)
    conversion_progress = Column(Float, nullable=True)  # 0-100

    # Quality metrics
    data_integrity_check = Column(Boolean, default=False)
    row_count_match = Column(Boolean, default=False)
    schema_compatibility = Column(Boolean, default=True)
    conversion_warnings = Column(JSON, nullable=True)
    conversion_errors = Column(JSON, nullable=True)

    # Performance metrics
    conversion_duration_ms = Column(Float, nullable=True)
    throughput_mb_per_sec = Column(Float, nullable=True)
    read_performance = Column(JSON, nullable=True)  # Benchmark results
    write_performance = Column(JSON, nullable=True)

    # Statistics
    min_values = Column(JSON, nullable=True)
    max_values = Column(JSON, nullable=True)
    null_counts = Column(JSON, nullable=True)
    distinct_counts = Column(JSON, nullable=True)

    # Optimization
    files_before = Column(Float, nullable=True)
    files_after = Column(Float, nullable=True)
    compaction_applied = Column(Boolean, default=False)
    optimization_notes = Column(JSON, nullable=True)

    # Audit fields
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_table_status", "table_name", "status"),
        Index("idx_source_target", "source_format", "target_format"),
        Index("idx_created_at", "created_at"),
        Index("idx_platform", "source_platform", "target_platform"),
    )

    def __repr__(self):
        return f"<TableConversion(id={self.conversion_id}, {self.table_name}, {self.source_format}→{self.target_format})>"
