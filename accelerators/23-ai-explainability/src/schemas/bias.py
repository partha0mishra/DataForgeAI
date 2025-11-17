"""Schemas for bias detection endpoints."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class BiasAnalysisRequest(BaseModel):
    """Request for bias analysis."""
    model_id: str = Field(..., description="Model identifier")
    model_name: Optional[str] = Field(None, description="Model name")
    X: List[List[float]] = Field(..., description="Feature data")
    y_true: List[int] = Field(..., description="True labels")
    y_pred: Optional[List[int]] = Field(None, description="Predicted labels (optional)")
    protected_attributes: List[str] = Field(
        ...,
        description="Names of protected attributes (e.g., ['race', 'gender'])"
    )
    sensitive_features: List[Any] = Field(
        ...,
        description="Values of sensitive features for each instance"
    )
    reference_group: Optional[str] = Field(
        None,
        description="Reference group for comparison"
    )
    metrics: List[str] = Field(
        default=['demographic_parity', 'equalized_odds'],
        description="Fairness metrics to compute"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "loan_approval_v1",
                "model_name": "Loan Approval Model",
                "X": [[35, 50000, 700], [28, 60000, 720]],
                "y_true": [1, 1],
                "y_pred": [1, 0],
                "protected_attributes": ["age", "gender"],
                "sensitive_features": ["A", "B"],
                "metrics": ["demographic_parity", "equalized_odds"]
            }
        }


class BiasReportResponse(BaseModel):
    """Response containing bias analysis report."""
    report_id: str
    model_id: str
    model_name: Optional[str]
    protected_attributes: List[str]
    reference_group: Optional[str]
    metrics_analyzed: List[str]
    bias_metrics: Dict[str, Any]
    overall_fairness_score: float = Field(..., ge=0, le=1)
    compliant: bool
    issues_detected: Optional[List[str]]
    recommendations: Optional[List[str]]
    severity: Optional[str]
    group_statistics: Optional[Dict[str, Any]]
    disparate_impact_ratio: Optional[float]
    dataset_size: Optional[int]
    group_distributions: Optional[Dict[str, int]]
    summary_text: Optional[str]
    analysis_duration_ms: Optional[float]
    created_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "report_id": "bias-report-123",
                "model_id": "loan_approval_v1",
                "protected_attributes": ["race", "gender"],
                "overall_fairness_score": 0.73,
                "compliant": True,
                "issues_detected": [],
                "severity": "low",
                "disparate_impact_ratio": 0.85,
                "summary_text": "Model demonstrates acceptable fairness...",
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class BiasStatsResponse(BaseModel):
    """Response containing bias statistics."""
    total_reports: int
    compliant_count: int
    non_compliant_count: int
    compliance_rate: float
    avg_fairness_score: float
    by_severity: Dict[str, int]
    unique_models: int

    class Config:
        json_schema_extra = {
            "example": {
                "total_reports": 45,
                "compliant_count": 38,
                "non_compliant_count": 7,
                "compliance_rate": 84.44,
                "avg_fairness_score": 0.781,
                "by_severity": {"low": 38, "medium": 5, "high": 2},
                "unique_models": 12
            }
        }


class TrendingIssuesResponse(BaseModel):
    """Response containing trending bias issues."""
    issues: List[Dict[str, Any]]
    time_range_hours: int

    class Config:
        json_schema_extra = {
            "example": {
                "issues": [
                    {"issue": "Demographic parity difference > 0.10", "count": 12},
                    {"issue": "Disparate impact violation", "count": 8}
                ],
                "time_range_hours": 168
            }
        }
