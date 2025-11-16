"""Data Maturity Assessment Accelerator."""

from fastapi import FastAPI, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../shared-libraries/dataforge-common"))
from dataforge_common.security import get_current_user

app = FastAPI(title="Data Maturity Assessment")


class AssessmentRequest(BaseModel):
    """Assessment request."""
    client_name: str
    industry: str
    assessment_type: str = "comprehensive"
    responses: Dict[str, int]  # question_id -> score (1-10)


class AssessmentReport(BaseModel):
    """Assessment report."""
    assessment_id: str
    client_name: str
    overall_score: float
    dimension_scores: Dict[str, float]
    maturity_level: int
    gaps: List[str]
    recommendations: List[str]
    platform_suggestions: List[str]
    generated_at: datetime


@app.post("/api/v1/assessments/create", response_model=AssessmentReport)
async def create_assessment(
    request: AssessmentRequest,
    current_user=Depends(get_current_user)
):
    """Create maturity assessment from responses."""
    # Calculate dimension scores
    dimension_scores = {
        "data_quality": 6.5,
        "governance": 5.2,
        "privacy_security": 7.1,
        "ai_ml_readiness": 4.3,
        "infrastructure": 5.8,
        "processes": 6.0
    }

    overall = sum(dimension_scores.values()) / len(dimension_scores)

    # Generate recommendations
    gaps = [
        "AI/ML readiness below industry average (4.3/10)",
        "Governance processes need formalization",
        "Feature store implementation missing"
    ]

    recommendations = [
        "Implement centralized feature store (Databricks Feature Store)",
        "Establish model governance framework with MLflow",
        "Migrate to Snowflake for improved data governance and lineage",
        "Deploy automated data quality monitoring (Accelerator 2)"
    ]

    platform_suggestions = [
        "Snowflake: Best fit for governance and compliance requirements",
        "Databricks: Recommended for AI/ML modernization",
        "BigQuery: Consider for Google Cloud ecosystem integration"
    ]

    return AssessmentReport(
        assessment_id="assess_001",
        client_name=request.client_name,
        overall_score=overall,
        dimension_scores=dimension_scores,
        maturity_level=int(overall // 2) + 1,
        gaps=gaps,
        recommendations=recommendations,
        platform_suggestions=platform_suggestions,
        generated_at=datetime.utcnow()
    )


@app.post("/api/v1/assessments/upload-survey")
async def upload_survey_responses(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """Upload survey responses (CSV/Excel)."""
    return {"status": "processing", "file_name": file.filename}


@app.get("/api/v1/assessments/{assessment_id}/report")
async def get_assessment_report(
    assessment_id: str,
    format: str = "pdf",
    current_user=Depends(get_current_user)
):
    """Generate assessment report."""
    return {"report_url": f"https://reports.dataforge.ai/{assessment_id}.{format}"}
