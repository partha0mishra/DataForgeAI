"""Schemas for trust assessment endpoints."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class TrustAssessmentRequest(BaseModel):
    """Request for trust assessment."""
    model_id: str = Field(..., description="Model identifier")
    model_name: Optional[str] = Field(None, description="Model name")
    model_version: Optional[str] = Field(None, description="Model version")
    environment: str = Field(
        default="production",
        description="Deployment environment (dev/staging/production)"
    )
    assessment_type: str = Field(
        default="periodic",
        description="Type of assessment (periodic/pre_deployment/incident)"
    )
    regulatory_framework: Optional[str] = Field(
        None,
        description="Regulatory framework (e.g., EU_AI_Act, NIST_AI_RMF)"
    )
    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for trust dimensions"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "fraud_detector_v1",
                "model_name": "Fraud Detection Model",
                "model_version": "2.1.0",
                "environment": "production",
                "assessment_type": "periodic",
                "regulatory_framework": "EU_AI_Act"
            }
        }


class TrustMetricResponse(BaseModel):
    """Response containing trust assessment."""
    metric_id: str
    model_id: str
    model_name: Optional[str]
    explainability_score: float = Field(..., ge=0, le=1)
    fairness_score: float = Field(..., ge=0, le=1)
    robustness_score: float = Field(..., ge=0, le=1)
    privacy_score: float = Field(..., ge=0, le=1)
    transparency_score: Optional[float] = Field(None, ge=0, le=1)
    accountability_score: Optional[float] = Field(None, ge=0, le=1)
    overall_trust_score: float = Field(..., ge=0, le=1)
    trust_level: str
    dimension_details: Optional[Dict[str, Any]]
    weights: Optional[Dict[str, float]]
    assessment_type: Optional[str]
    regulatory_framework: Optional[str]
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    recommendations: Optional[List[str]]
    certification_status: Optional[str]
    previous_score: Optional[float]
    score_trend: Optional[str]
    changes_since_last: Optional[Dict[str, Any]]
    summary_text: Optional[str]
    model_version: Optional[str]
    environment: Optional[str]
    created_at: datetime
    assessed_by: Optional[str]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "metric_id": "trust-123",
                "model_id": "fraud_detector_v1",
                "explainability_score": 0.82,
                "fairness_score": 0.75,
                "robustness_score": 0.70,
                "privacy_score": 0.80,
                "overall_trust_score": 0.77,
                "trust_level": "high",
                "strengths": ["explainability", "privacy"],
                "weaknesses": ["robustness"],
                "certification_status": "certified",
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class TrustStatsResponse(BaseModel):
    """Response containing trust statistics."""
    total_assessments: int
    avg_overall_trust: float
    avg_dimensions: Dict[str, float]
    by_trust_level: Dict[str, int]
    by_certification: Dict[str, int]
    unique_models: int

    class Config:
        json_schema_extra = {
            "example": {
                "total_assessments": 87,
                "avg_overall_trust": 0.745,
                "avg_dimensions": {
                    "explainability": 0.78,
                    "fairness": 0.72,
                    "robustness": 0.68,
                    "privacy": 0.81
                },
                "by_trust_level": {"high": 45, "medium": 35, "low": 7},
                "by_certification": {"certified": 40, "pending": 35, "not_certified": 12},
                "unique_models": 23
            }
        }


class TrustHistoryResponse(BaseModel):
    """Response containing trust score history."""
    model_id: str
    metrics: List[TrustMetricResponse]
    period_days: int

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "fraud_detector_v1",
                "metrics": [],
                "period_days": 90
            }
        }
