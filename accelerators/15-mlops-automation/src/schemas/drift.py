"""Pydantic schemas for drift detection operations."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class DataDriftRequest(BaseModel):
    """Schema for data drift detection request."""

    model_id: str = Field(..., min_length=1, description="Model identifier")
    reference_data: List[List[float]] = Field(..., min_length=1, description="Reference dataset (training data)")
    current_data: List[List[float]] = Field(..., min_length=1, description="Current production data")
    feature_names: Optional[List[str]] = Field(None, description="Feature names")
    threshold: float = Field(0.05, ge=0, le=1, description="P-value threshold for drift detection")
    deployment_id: Optional[str] = Field(None, description="Optional deployment identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "model-123",
                "reference_data": [[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]],
                "current_data": [[2.0, 3.0, 4.0], [2.5, 3.5, 4.5]],
                "feature_names": ["feature1", "feature2", "feature3"],
                "threshold": 0.05,
                "deployment_id": "deploy-456"
            }
        }


class PredictionDriftRequest(BaseModel):
    """Schema for prediction drift detection request."""

    model_id: str = Field(..., min_length=1, description="Model identifier")
    reference_predictions: List[float] = Field(..., min_length=1, description="Historical predictions")
    current_predictions: List[float] = Field(..., min_length=1, description="Current predictions")
    threshold: float = Field(0.05, ge=0, le=1, description="Threshold for drift detection")
    deployment_id: Optional[str] = Field(None, description="Optional deployment identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "model-123",
                "reference_predictions": [0.1, 0.2, 0.3, 0.4, 0.5],
                "current_predictions": [0.6, 0.7, 0.8, 0.9, 1.0],
                "threshold": 0.05,
                "deployment_id": "deploy-456"
            }
        }


class ConceptDriftRequest(BaseModel):
    """Schema for concept drift detection request."""

    model_id: str = Field(..., min_length=1, description="Model identifier")
    true_labels: List[float] = Field(..., min_length=1, description="Ground truth labels")
    predictions: List[float] = Field(..., min_length=1, description="Model predictions")
    historical_accuracy: float = Field(..., ge=0, le=1, description="Historical accuracy baseline")
    threshold: float = Field(0.1, ge=0, le=1, description="Acceptable accuracy drop threshold")
    deployment_id: Optional[str] = Field(None, description="Optional deployment identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "model-123",
                "true_labels": [0, 1, 0, 1, 1, 0],
                "predictions": [0, 1, 1, 1, 0, 0],
                "historical_accuracy": 0.95,
                "threshold": 0.1,
                "deployment_id": "deploy-456"
            }
        }


class AffectedFeature(BaseModel):
    """Information about an affected feature."""

    name: str
    p_value: float
    ks_statistic: float


class DriftResponse(BaseModel):
    """Schema for drift detection response."""

    drift_id: str
    model_id: str
    deployment_id: Optional[str] = None
    detection_timestamp: datetime
    drift_type: str
    drift_score: float
    threshold: float
    is_drift_detected: bool
    affected_features: List[AffectedFeature] = Field(default_factory=list)
    statistical_tests: Dict[str, Any] = Field(default_factory=dict)
    severity: str
    recommendations: List[str]
    detection_method: str
    auto_retrain_triggered: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_drift_detection(cls, drift):
        """Create response from database model."""
        affected_features = [
            AffectedFeature(**feature) if isinstance(feature, dict) else feature
            for feature in (drift.affected_features or [])
        ]

        return cls(
            drift_id=drift.drift_id,
            model_id=drift.model_id,
            deployment_id=drift.deployment_id,
            detection_timestamp=drift.detection_timestamp,
            drift_type=drift.drift_type,
            drift_score=drift.drift_score,
            threshold=drift.threshold,
            is_drift_detected=drift.is_drift_detected,
            affected_features=affected_features,
            statistical_tests=drift.statistical_tests or {},
            severity=drift.severity,
            recommendations=drift.recommendations or [],
            detection_method=drift.detection_method,
            auto_retrain_triggered=drift.auto_retrain_triggered
        )


class DriftEvent(BaseModel):
    """Summary of a drift event."""

    drift_id: str
    drift_type: str
    severity: str
    drift_score: float
    timestamp: datetime
    auto_retrain_triggered: bool


class DriftStatistics(BaseModel):
    """Drift detection statistics."""

    total_detections: int
    drift_detected_count: int
    drift_rate_percentage: float
    avg_drift_score: float
    drift_by_type: Dict[str, int]
    drift_by_severity: Dict[str, int]
    auto_retrain_triggered_count: int


class DriftSummaryResponse(BaseModel):
    """Schema for drift summary response."""

    model_id: str
    time_window_hours: int
    statistics: DriftStatistics
    recent_drift_events: List[DriftEvent]
    requires_attention: bool


class DeploymentDriftType(BaseModel):
    """Drift events by type for a deployment."""

    severity: str
    score: float
    timestamp: datetime


class DeploymentDriftResponse(BaseModel):
    """Schema for deployment drift monitoring response."""

    deployment_id: str
    deployment_name: str
    model_id: str
    environment: str
    total_drift_detections: int
    drift_by_type: Dict[str, List[DeploymentDriftType]]
    high_severity_count: int
    auto_retrain_triggered: bool
    health_recommendation: str


class DriftListResponse(BaseModel):
    """Schema for paginated drift detection list."""

    drift_detections: List[DriftResponse]
    total: int
    skip: int
    limit: int
