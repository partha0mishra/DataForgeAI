"""Schemas for hallucination detection endpoints."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class HallucinationCheckRequest(BaseModel):
    """Request for hallucination check."""
    prompt: str = Field(..., description="The input prompt")
    output: str = Field(..., description="The generated output to check")
    model_name: str = Field(..., description="Name of the GenAI model")
    model_version: Optional[str] = Field(None, description="Model version")
    domain: Optional[str] = Field(None, description="Domain/topic of the query")
    use_case: Optional[str] = Field(
        None,
        description="Use case (e.g., customer_support, content_generation)"
    )
    detection_methods: List[str] = Field(
        default=['self_consistency', 'confidence', 'perplexity'],
        description="Detection methods to use"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "What is the capital of France?",
                "output": "The capital of France is Paris, which has a population of about 2.2 million people.",
                "model_name": "gpt-4",
                "model_version": "0613",
                "domain": "geography",
                "use_case": "customer_support",
                "detection_methods": ["self_consistency", "confidence"]
            }
        }


class HallucinationCheckResponse(BaseModel):
    """Response containing hallucination check results."""
    check_id: str
    model_name: str
    model_version: Optional[str]
    prompt: str
    output: str
    hallucination_risk: str
    confidence_score: float = Field(..., ge=0, le=1)
    hallucination_score: float = Field(..., ge=0, le=1)
    reasoning: Optional[str]
    prompt_attribution: Optional[Dict[str, float]]
    fact_checks: Optional[List[Dict[str, Any]]]
    sources: Optional[List[str]]
    grounding_quality: Optional[float]
    detection_methods: Optional[List[str]]
    detection_details: Optional[Dict[str, Any]]
    hallucinated: bool
    issues_detected: Optional[List[str]]
    severity: Optional[str]
    recommendations: Optional[List[str]]
    alternative_responses: Optional[List[str]]
    domain: Optional[str]
    use_case: Optional[str]
    check_duration_ms: Optional[float]
    explanation_text: Optional[str]
    created_at: datetime
    checked_by: Optional[str]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "check_id": "halluc-check-123",
                "model_name": "gpt-4",
                "prompt": "What is the capital of France?",
                "output": "The capital of France is Paris...",
                "hallucination_risk": "low",
                "confidence_score": 0.95,
                "hallucination_score": 0.15,
                "hallucinated": False,
                "issues_detected": [],
                "severity": "low",
                "explanation_text": "✓ This output appears reliable...",
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class HallucinationStatsResponse(BaseModel):
    """Response containing hallucination statistics."""
    total_checks: int
    hallucinated_count: int
    hallucination_rate: float
    avg_confidence_score: float
    avg_hallucination_score: float
    avg_grounding_quality: Optional[float]
    by_risk_level: Dict[str, int]
    by_severity: Dict[str, int]
    unique_models: int

    class Config:
        json_schema_extra = {
            "example": {
                "total_checks": 1250,
                "hallucinated_count": 87,
                "hallucination_rate": 6.96,
                "avg_confidence_score": 0.834,
                "avg_hallucination_score": 0.142,
                "avg_grounding_quality": 0.71,
                "by_risk_level": {"none": 450, "low": 580, "medium": 150, "high": 70},
                "by_severity": {"low": 1080, "medium": 120, "high": 50},
                "unique_models": 8
            }
        }


class ModelReliabilityResponse(BaseModel):
    """Response containing model reliability metrics."""
    model_name: str
    period_days: int
    total_checks: int
    hallucinated_count: int
    hallucination_rate: float
    avg_confidence: float
    avg_hallucination_score: float
    reliability_score: float = Field(..., ge=0, le=1)

    class Config:
        json_schema_extra = {
            "example": {
                "model_name": "gpt-4",
                "period_days": 30,
                "total_checks": 450,
                "hallucinated_count": 23,
                "hallucination_rate": 5.11,
                "avg_confidence": 0.87,
                "avg_hallucination_score": 0.12,
                "reliability_score": 0.825
            }
        }


class TrendingIssuesResponse(BaseModel):
    """Response containing trending hallucination issues."""
    issues: List[Dict[str, Any]]
    time_range_hours: int

    class Config:
        json_schema_extra = {
            "example": {
                "issues": [
                    {"issue": "Poor grounding in verifiable facts", "count": 45},
                    {"issue": "Low self-consistency in responses", "count": 32}
                ],
                "time_range_hours": 168
            }
        }
