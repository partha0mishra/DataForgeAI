"""Schemas for explanation endpoints."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ExplanationType(str, Enum):
    """Types of explanations."""
    SHAP = "shap"
    LIME = "lime"
    ALIBI = "alibi"
    COUNTERFACTUAL = "counterfactual"
    FEATURE_IMPORTANCE = "feature_importance"


class ExplanationScope(str, Enum):
    """Scope of explanation."""
    GLOBAL = "global"
    LOCAL = "local"


class ExplanationRequest(BaseModel):
    """Request for generating model explanation."""
    model_id: str = Field(..., description="Model identifier")
    model_name: Optional[str] = Field(None, description="Model name")
    explanation_type: ExplanationType = Field(
        default=ExplanationType.SHAP,
        description="Type of explanation to generate"
    )
    instance: Optional[List[float]] = Field(
        None,
        description="Single instance for local explanation (optional)"
    )
    background_data: Optional[List[List[float]]] = Field(
        None,
        description="Background dataset for SHAP (optional)"
    )
    training_data: Optional[List[List[float]]] = Field(
        None,
        description="Training data for LIME (optional)"
    )
    feature_names: Optional[List[str]] = Field(
        None,
        description="Names of features"
    )
    num_features: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of top features to include"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "fraud_detector_v1",
                "model_name": "Fraud Detection Model",
                "explanation_type": "shap",
                "instance": [35, 12.5, 2, 450],
                "feature_names": ["age", "tenure", "support_calls", "purchases"],
                "num_features": 10
            }
        }


class ExplanationResponse(BaseModel):
    """Response containing model explanation."""
    explanation_id: str
    model_id: str
    model_name: Optional[str]
    explanation_type: str
    scope: str
    feature_importances: Dict[str, float]
    prediction: Optional[Any] = None
    confidence: Optional[float] = None
    base_value: Optional[float] = None
    explanation_text: Optional[str]
    visualization_urls: Optional[List[str]] = None
    generation_time_ms: Optional[float]
    num_features: Optional[int]
    created_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "explanation_id": "exp-123",
                "model_id": "fraud_detector_v1",
                "explanation_type": "shap",
                "scope": "local",
                "feature_importances": {
                    "age": 0.35,
                    "tenure": 0.28,
                    "purchases": 0.22,
                    "support_calls": -0.15
                },
                "prediction": 0,
                "confidence": 0.87,
                "explanation_text": "Instance-level SHAP analysis...",
                "generation_time_ms": 234.5,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class TopFeaturesResponse(BaseModel):
    """Response containing top features for a model."""
    model_id: str
    explanation_type: str
    top_features: Dict[str, float]
    total_explanations: int

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "fraud_detector_v1",
                "explanation_type": "shap",
                "top_features": {
                    "age": 0.42,
                    "tenure": 0.31,
                    "purchases": 0.27
                },
                "total_explanations": 156
            }
        }


class ExplanationStatsResponse(BaseModel):
    """Response containing explanation statistics."""
    total_explanations: int
    by_type: Dict[str, int]
    by_scope: Dict[str, int]
    avg_generation_time_ms: float
    unique_models: int

    class Config:
        json_schema_extra = {
            "example": {
                "total_explanations": 1250,
                "by_type": {"shap": 800, "lime": 350, "feature_importance": 100},
                "by_scope": {"global": 200, "local": 1050},
                "avg_generation_time_ms": 187.3,
                "unique_models": 15
            }
        }
