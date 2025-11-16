"""Pydantic schemas for experiment operations."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ExperimentCreate(BaseModel):
    """Schema for creating a new experiment."""

    name: str = Field(..., min_length=1, max_length=200, description="Experiment name")
    description: Optional[str] = Field(None, max_length=1000, description="Experiment description")
    tags: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Experiment tags")
    artifact_location: Optional[str] = Field(None, description="Artifact storage location")
    created_by: Optional[str] = Field(None, max_length=100, description="Creator identifier")
    sync_with_mlflow: bool = Field(True, description="Whether to create in MLflow")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "fraud_detection_v2",
                "description": "Experiment for fraud detection model v2 with new features",
                "tags": {"team": "fraud", "priority": "high"},
                "artifact_location": "s3://mlflow-artifacts/fraud-detection-v2",
                "created_by": "data-science-team",
                "sync_with_mlflow": True
            }
        }


class ExperimentResponse(BaseModel):
    """Schema for experiment response."""

    experiment_id: str
    name: str
    description: Optional[str] = None
    mlflow_experiment_id: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict)
    artifact_location: Optional[str] = None
    run_count: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_experiment(cls, experiment):
        """Create response from database model."""
        return cls(
            experiment_id=experiment.experiment_id,
            name=experiment.name,
            description=experiment.description,
            mlflow_experiment_id=experiment.mlflow_experiment_id,
            tags=experiment.tags or {},
            artifact_location=experiment.artifact_location,
            run_count=experiment.run_count or 0,
            created_by=experiment.created_by,
            created_at=experiment.created_at,
            updated_at=experiment.updated_at
        )


class ExperimentUpdate(BaseModel):
    """Schema for updating experiment."""

    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[Dict[str, Any]] = None


class ExperimentSyncRequest(BaseModel):
    """Schema for syncing experiment from MLflow."""

    mlflow_experiment_id: str = Field(..., min_length=1, description="MLflow experiment ID")

    class Config:
        json_schema_extra = {
            "example": {
                "mlflow_experiment_id": "123456789"
            }
        }


class ModelSummary(BaseModel):
    """Summary of a model in an experiment."""

    model_id: str
    name: str
    version: str
    is_production: bool
    accuracy: Optional[float] = None


class ExperimentDetailsResponse(BaseModel):
    """Schema for detailed experiment information."""

    experiment_id: str
    name: str
    description: Optional[str] = None
    mlflow_experiment_id: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict)
    artifact_location: Optional[str] = None
    run_count: int
    model_count: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    models: List[ModelSummary]


class RunCreate(BaseModel):
    """Schema for starting a new MLflow run."""

    experiment_id: str = Field(..., min_length=1, description="Experiment identifier")
    run_name: Optional[str] = Field(None, max_length=200, description="Run name")
    tags: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Run tags")

    class Config:
        json_schema_extra = {
            "example": {
                "experiment_id": "exp-123",
                "run_name": "fraud_rf_v1",
                "tags": {"algorithm": "RandomForest", "version": "1.0"}
            }
        }


class RunMetricsLog(BaseModel):
    """Schema for logging metrics to a run."""

    run_id: str = Field(..., min_length=1, description="MLflow run ID")
    metrics: Dict[str, float] = Field(..., min_length=1, description="Metrics to log")
    step: Optional[int] = Field(None, ge=0, description="Step number")

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run-abc123",
                "metrics": {
                    "accuracy": 0.95,
                    "precision": 0.92,
                    "recall": 0.89
                },
                "step": 100
            }
        }


class RunParamsLog(BaseModel):
    """Schema for logging parameters to a run."""

    run_id: str = Field(..., min_length=1, description="MLflow run ID")
    params: Dict[str, Any] = Field(..., min_length=1, description="Parameters to log")

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run-abc123",
                "params": {
                    "n_estimators": 100,
                    "max_depth": 10,
                    "learning_rate": 0.01
                }
            }
        }


class RunEndRequest(BaseModel):
    """Schema for ending a run."""

    run_id: Optional[str] = Field(None, description="Run ID (ends active run if None)")


class LeaderboardEntry(BaseModel):
    """Entry in experiment leaderboard."""

    rank: int
    model_id: str
    name: str
    version: str
    mlflow_run_id: Optional[str] = None
    metric_value: Optional[float] = None
    is_production: bool
    created_at: datetime


class ExperimentLeaderboardResponse(BaseModel):
    """Schema for experiment leaderboard response."""

    experiment_id: str
    experiment_name: str
    metric: str
    entries: List[LeaderboardEntry]


class RunComparisonData(BaseModel):
    """Data for a single run in comparison."""

    run_id: str
    run_name: str
    status: str
    metrics: Dict[str, float]
    params: Dict[str, Any]
    start_time: datetime


class RunComparisonResponse(BaseModel):
    """Schema for run comparison response."""

    experiment_id: str
    experiment_name: str
    runs: List[RunComparisonData]
    comparison_count: int


class ExperimentStatsItem(BaseModel):
    """Statistics item for an experiment."""

    experiment_id: str
    name: str
    run_count: int
    mlflow_synced: bool
    created_at: datetime


class ExperimentsSummaryResponse(BaseModel):
    """Schema for all experiments summary."""

    total_experiments: int
    total_runs: int
    avg_runs_per_experiment: float
    most_active_experiment: Optional[Dict[str, Any]] = None
    experiments: List[ExperimentStatsItem]
