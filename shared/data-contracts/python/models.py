"""Pydantic models for data contracts."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PipelineStatus(str, Enum):
    """Pipeline run status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataSourceConfig(BaseModel):
    """Data source configuration."""

    type: str = Field(..., description="Source type (e.g., postgresql, s3)")
    connection: str = Field(..., description="Connection identifier")
    path: str = Field(..., description="Source path/table name")


class ErrorInfo(BaseModel):
    """Error information."""

    message: str
    type: str
    traceback: Optional[str] = None


class PipelineMetadata(BaseModel):
    """Pipeline execution metadata."""

    pipeline_id: str = Field(..., description="Unique pipeline identifier")
    run_id: str = Field(..., description="Unique run identifier")
    name: str = Field(..., description="Pipeline name")
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    records_processed: Optional[int] = None
    source: Optional[DataSourceConfig] = None
    destination: Optional[DataSourceConfig] = None
    error: Optional[ErrorInfo] = None

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class QualityStatus(str, Enum):
    """Quality check status."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class QualityCheck(BaseModel):
    """Individual quality check result."""

    check_name: str
    check_type: str
    status: QualityStatus
    expectation: Optional[str] = None
    actual: Optional[str] = None
    message: Optional[str] = None


class QualityMetrics(BaseModel):
    """Quality report metrics."""

    total_rows: int
    total_checks: int
    passed_checks: int
    failed_checks: int
    warnings: int


class QualityReport(BaseModel):
    """Data quality validation report."""

    report_id: str
    dataset: str
    timestamp: datetime
    overall_status: QualityStatus
    checks: List[QualityCheck]
    metrics: QualityMetrics

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class CatalogEntry(BaseModel):
    """Data catalog entry."""

    entry_id: str
    name: str
    description: Optional[str] = None
    type: str = Field(..., description="Asset type (table, file, model, etc.)")
    owner: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    schema_fields: Optional[List[Dict[str, Any]]] = None
    lineage: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ModelMetadata(BaseModel):
    """ML model metadata."""

    model_id: str
    name: str
    version: str
    framework: str = Field(..., description="ML framework (sklearn, pytorch, etc.)")
    metrics: Dict[str, float] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    features: List[str] = Field(default_factory=list)
    target: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    registered_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}
