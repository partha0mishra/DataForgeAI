"""Pydantic schemas for ML model operations."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ModelCreate(BaseModel):
    """Schema for creating a new ML model."""

    name: str = Field(..., min_length=1, max_length=200, description="Model name")
    version: str = Field(..., min_length=1, max_length=50, description="Model version")
    framework: str = Field(..., min_length=1, max_length=50, description="ML framework (sklearn, tensorflow, pytorch, etc.)")
    algorithm: Optional[str] = Field(None, max_length=100, description="Algorithm name")
    description: Optional[str] = Field(None, max_length=1000, description="Model description")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Model hyperparameters")
    metrics: Optional[Dict[str, float]] = Field(default_factory=dict, description="Performance metrics")
    tags: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Model tags")
    created_by: Optional[str] = Field(None, max_length=100, description="Creator identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "fraud_detector",
                "version": "1.0.0",
                "framework": "sklearn",
                "algorithm": "RandomForest",
                "description": "Fraud detection model for credit card transactions",
                "parameters": {
                    "n_estimators": 100,
                    "max_depth": 10,
                    "random_state": 42
                },
                "metrics": {
                    "accuracy": 0.95,
                    "precision": 0.92,
                    "recall": 0.89,
                    "f1_score": 0.905,
                    "auc_roc": 0.96
                },
                "tags": {"team": "fraud", "env": "production"},
                "created_by": "data-science-team"
            }
        }


class ModelCreateFromMLflow(BaseModel):
    """Schema for registering a model from MLflow run."""

    mlflow_run_id: str = Field(..., min_length=1, description="MLflow run identifier")
    model_name: str = Field(..., min_length=1, max_length=200, description="Model name")
    version: str = Field(..., min_length=1, max_length=50, description="Model version")
    tags: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional tags")

    class Config:
        json_schema_extra = {
            "example": {
                "mlflow_run_id": "abc123def456",
                "model_name": "fraud_detector",
                "version": "2.0.0",
                "tags": {"team": "fraud"}
            }
        }


class ModelMetrics(BaseModel):
    """Model performance metrics."""

    accuracy: Optional[float] = Field(None, ge=0, le=1)
    precision: Optional[float] = Field(None, ge=0, le=1)
    recall: Optional[float] = Field(None, ge=0, le=1)
    f1_score: Optional[float] = Field(None, ge=0, le=1)
    auc_roc: Optional[float] = Field(None, ge=0, le=1)
    custom_metrics: Optional[Dict[str, float]] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    """Schema for ML model response."""

    model_id: str
    name: str
    version: str
    framework: str
    algorithm: Optional[str] = None
    description: Optional[str] = None
    status: str
    is_production: bool
    mlflow_run_id: Optional[str] = None
    mlflow_experiment_id: Optional[str] = None
    mlflow_model_uri: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, Any] = Field(default_factory=dict)
    metrics: ModelMetrics
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, model):
        """Create response from database model."""
        return cls(
            model_id=model.model_id,
            name=model.name,
            version=model.version,
            framework=model.framework,
            algorithm=model.algorithm,
            description=model.description,
            status=model.status,
            is_production=model.is_production,
            mlflow_run_id=model.mlflow_run_id,
            mlflow_experiment_id=model.mlflow_experiment_id,
            mlflow_model_uri=model.mlflow_model_uri,
            parameters=model.parameters or {},
            tags=model.tags or {},
            metrics=ModelMetrics(
                accuracy=model.accuracy,
                precision=model.precision,
                recall=model.recall,
                f1_score=model.f1_score,
                auc_roc=model.auc_roc,
                custom_metrics=model.custom_metrics or {}
            ),
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


class ModelUpdate(BaseModel):
    """Schema for updating model metadata."""

    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(registered|deployed|archived)$")


class ModelMetricsUpdate(BaseModel):
    """Schema for updating model metrics."""

    metrics: Dict[str, float] = Field(..., min_length=1, description="Metrics to update")

    class Config:
        json_schema_extra = {
            "example": {
                "metrics": {
                    "accuracy": 0.96,
                    "precision": 0.94,
                    "custom_metric": 0.88
                }
            }
        }


class ModelListResponse(BaseModel):
    """Schema for paginated model list response."""

    models: List[ModelResponse]
    total: int
    skip: int
    limit: int


class ModelComparisonItem(BaseModel):
    """Schema for model comparison item."""

    model_id: str
    name: str
    version: str
    framework: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_roc: Optional[float] = None
    is_production: bool


class ModelComparisonResponse(BaseModel):
    """Schema for model comparison response."""

    models: List[ModelComparisonItem]
    winner_by_metric: Dict[str, str] = Field(
        description="Maps metric name to winning model_id"
    )


class ModelPromoteRequest(BaseModel):
    """Schema for promoting model to production."""

    demote_current: bool = Field(
        True,
        description="Whether to demote current production models of the same name"
    )
