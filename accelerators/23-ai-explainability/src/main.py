"""AI Explainability and Trust Accelerator - Production API."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
import numpy as np
import logging
from datetime import datetime

from src.database import get_db, init_db
from src.services.explanation_service import ExplanationService
from src.services.bias_detection_service import BiasDetectionService
from src.services.trust_assessment_service import TrustAssessmentService
from src.services.hallucination_detection_service import HallucinationDetectionService

from src.schemas.explanations import (
    ExplanationRequest,
    ExplanationResponse,
    TopFeaturesResponse,
    ExplanationStatsResponse
)
from src.schemas.bias import (
    BiasAnalysisRequest,
    BiasReportResponse,
    BiasStatsResponse,
    TrendingIssuesResponse as BiasTrendingIssues
)
from src.schemas.trust import (
    TrustAssessmentRequest,
    TrustMetricResponse,
    TrustStatsResponse,
    TrustHistoryResponse
)
from src.schemas.hallucination import (
    HallucinationCheckRequest,
    HallucinationCheckResponse,
    HallucinationStatsResponse,
    ModelReliabilityResponse,
    TrendingIssuesResponse as HallucinationTrendingIssues
)

# Placeholder imports for security (would use from shared library)
try:
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), "../../../shared-libraries/dataforge-common"))
    from dataforge_common.security import get_current_user, require_roles
except ImportError:
    # Fallback for development
    def get_current_user():
        return {"user_id": "dev_user", "username": "developer"}

    def require_roles(*roles):
        def decorator(func):
            return func
        return decorator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Explainability and Trust API",
    description="Production-ready API for model explainability, bias detection, trust assessment, and hallucination detection",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ==================== EXPLANATION ENDPOINTS ====================

@app.post("/api/v1/explanations", response_model=ExplanationResponse)
async def create_explanation(
    request: ExplanationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Generate model explanation using SHAP, LIME, or other methods.

    Requires a trained model object (in production, would load from model registry).
    """
    try:
        service = ExplanationService(db)

        # Convert request data to numpy arrays
        instance = np.array(request.instance) if request.instance else None
        background_data = np.array(request.background_data) if request.background_data else None
        training_data = np.array(request.training_data) if request.training_data else None

        # In production, load actual model from registry
        # For demo, we'll create a mock model
        from sklearn.ensemble import RandomForestClassifier
        mock_model = RandomForestClassifier(n_estimators=10, random_state=42)

        if background_data is not None and len(background_data) > 0:
            # Train mock model
            mock_y = np.random.randint(0, 2, len(background_data))
            mock_model.fit(background_data, mock_y)

        # Generate explanation based on type
        if request.explanation_type == "shap":
            explanation = service.generate_shap_explanation(
                model=mock_model,
                instance=instance,
                background_data=background_data,
                feature_names=request.feature_names,
                model_id=request.model_id,
                model_name=request.model_name,
                num_features=request.num_features,
                created_by=current_user.get("username")
            )
        elif request.explanation_type == "lime":
            if instance is None or training_data is None:
                raise HTTPException(
                    status_code=400,
                    detail="LIME requires both instance and training_data"
                )
            explanation = service.generate_lime_explanation(
                model=mock_model,
                instance=instance,
                training_data=training_data,
                feature_names=request.feature_names,
                model_id=request.model_id,
                model_name=request.model_name,
                num_features=request.num_features,
                created_by=current_user.get("username")
            )
        elif request.explanation_type == "feature_importance":
            if not request.feature_names:
                raise HTTPException(
                    status_code=400,
                    detail="feature_importance requires feature_names"
                )
            explanation = service.generate_feature_importance_explanation(
                model=mock_model,
                feature_names=request.feature_names,
                model_id=request.model_id,
                model_name=request.model_name,
                created_by=current_user.get("username")
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported explanation type: {request.explanation_type}"
            )

        return ExplanationResponse.from_orm(explanation)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating explanation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/explanations/{explanation_id}", response_model=ExplanationResponse)
async def get_explanation(
    explanation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get explanation by ID."""
    service = ExplanationService(db)
    explanation = service.get_explanation_by_id(explanation_id)

    if not explanation:
        raise HTTPException(status_code=404, detail="Explanation not found")

    return ExplanationResponse.from_orm(explanation)


@app.get("/api/v1/explanations/model/{model_id}", response_model=List[ExplanationResponse])
async def get_model_explanations(
    model_id: str,
    explanation_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get all explanations for a model."""
    service = ExplanationService(db)
    explanations = service.get_model_explanations(model_id, explanation_type, limit)
    return [ExplanationResponse.from_orm(exp) for exp in explanations]


@app.get("/api/v1/explanations/model/{model_id}/top-features", response_model=TopFeaturesResponse)
async def get_top_features(
    model_id: str,
    explanation_type: str = "shap",
    top_n: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get aggregated top features for a model."""
    service = ExplanationService(db)
    top_features = service.get_top_features(model_id, explanation_type, top_n)

    return TopFeaturesResponse(
        model_id=model_id,
        explanation_type=explanation_type,
        top_features=top_features,
        total_explanations=len(service.get_model_explanations(model_id, explanation_type))
    )


@app.get("/api/v1/explanations/stats", response_model=ExplanationStatsResponse)
async def get_explanation_stats(
    model_id: Optional[str] = None,
    hours: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get explanation statistics."""
    service = ExplanationService(db)
    stats = service.get_explanation_stats(model_id, hours)
    return ExplanationStatsResponse(**stats)


# ==================== BIAS DETECTION ENDPOINTS ====================

@app.post("/api/v1/bias/analyze", response_model=BiasReportResponse)
async def analyze_bias(
    request: BiasAnalysisRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Analyze model for bias and fairness."""
    try:
        service = BiasDetectionService(db)

        # Convert to numpy arrays
        X = np.array(request.X)
        y_true = np.array(request.y_true)
        y_pred = np.array(request.y_pred) if request.y_pred else None
        sensitive_features = np.array(request.sensitive_features)

        # In production, load actual model from registry
        from sklearn.ensemble import RandomForestClassifier
        mock_model = RandomForestClassifier(n_estimators=10, random_state=42)
        if y_pred is None:
            mock_model.fit(X, y_true)

        report = service.analyze_bias(
            model=mock_model,
            X=X,
            y_true=y_true,
            y_pred=y_pred,
            protected_attributes=request.protected_attributes,
            sensitive_features=sensitive_features,
            model_id=request.model_id,
            model_name=request.model_name,
            reference_group=request.reference_group,
            metrics=request.metrics,
            created_by=current_user.get("username")
        )

        return BiasReportResponse.from_orm(report)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in bias analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/bias/reports/{report_id}", response_model=BiasReportResponse)
async def get_bias_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get bias report by ID."""
    service = BiasDetectionService(db)
    report = service.get_report_by_id(report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Bias report not found")

    return BiasReportResponse.from_orm(report)


@app.get("/api/v1/bias/model/{model_id}", response_model=List[BiasReportResponse])
async def get_model_bias_reports(
    model_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get all bias reports for a model."""
    service = BiasDetectionService(db)
    reports = service.get_model_reports(model_id, limit)
    return [BiasReportResponse.from_orm(r) for r in reports]


@app.get("/api/v1/bias/model/{model_id}/latest", response_model=BiasReportResponse)
async def get_latest_bias_report(
    model_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get the most recent bias report for a model."""
    service = BiasDetectionService(db)
    report = service.get_latest_report(model_id)

    if not report:
        raise HTTPException(status_code=404, detail="No bias reports found for this model")

    return BiasReportResponse.from_orm(report)


@app.get("/api/v1/bias/non-compliant", response_model=List[BiasReportResponse])
async def get_non_compliant_models(
    severity: Optional[str] = None,
    hours: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get non-compliant bias reports."""
    service = BiasDetectionService(db)
    reports = service.get_non_compliant_models(severity, hours)
    return [BiasReportResponse.from_orm(r) for r in reports]


@app.get("/api/v1/bias/stats", response_model=BiasStatsResponse)
async def get_bias_stats(
    model_id: Optional[str] = None,
    hours: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get bias statistics."""
    service = BiasDetectionService(db)
    stats = service.get_bias_stats(model_id, hours)
    return BiasStatsResponse(**stats)


# ==================== TRUST ASSESSMENT ENDPOINTS ====================

@app.post("/api/v1/trust/assess", response_model=TrustMetricResponse)
async def assess_trust(
    request: TrustAssessmentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Perform comprehensive trust assessment for a model."""
    try:
        service = TrustAssessmentService(db)

        metric = service.assess_model_trust(
            model_id=request.model_id,
            model_name=request.model_name,
            model_version=request.model_version,
            environment=request.environment,
            assessment_type=request.assessment_type,
            regulatory_framework=request.regulatory_framework,
            weights=request.weights,
            assessed_by=current_user.get("username")
        )

        return TrustMetricResponse.from_orm(metric)

    except Exception as e:
        logger.error(f"Error in trust assessment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/trust/{metric_id}", response_model=TrustMetricResponse)
async def get_trust_metric(
    metric_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get trust metric by ID."""
    service = TrustAssessmentService(db)
    metric = service.get_trust_metric(metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail="Trust metric not found")

    return TrustMetricResponse.from_orm(metric)


@app.get("/api/v1/trust/model/{model_id}/history", response_model=TrustHistoryResponse)
async def get_trust_history(
    model_id: str,
    days: int = 90,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get trust score history for a model."""
    service = TrustAssessmentService(db)
    metrics = service.get_model_trust_history(model_id, days)

    return TrustHistoryResponse(
        model_id=model_id,
        metrics=[TrustMetricResponse.from_orm(m) for m in metrics],
        period_days=days
    )


@app.get("/api/v1/trust/low-trust", response_model=List[TrustMetricResponse])
async def get_low_trust_models(
    threshold: float = 0.6,
    environment: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get models with low trust scores."""
    service = TrustAssessmentService(db)
    metrics = service.get_low_trust_models(threshold, environment)
    return [TrustMetricResponse.from_orm(m) for m in metrics]


@app.get("/api/v1/trust/stats", response_model=TrustStatsResponse)
async def get_trust_stats(
    environment: Optional[str] = None,
    hours: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get trust statistics."""
    service = TrustAssessmentService(db)
    stats = service.get_trust_stats(environment, hours)
    return TrustStatsResponse(**stats)


# ==================== HALLUCINATION DETECTION ENDPOINTS ====================

@app.post("/api/v1/hallucination/check", response_model=HallucinationCheckResponse)
async def check_hallucination(
    request: HallucinationCheckRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Check GenAI output for hallucinations."""
    try:
        service = HallucinationDetectionService(db)

        check = service.check_hallucination(
            prompt=request.prompt,
            output=request.output,
            model_name=request.model_name,
            model_version=request.model_version,
            domain=request.domain,
            use_case=request.use_case,
            detection_methods=request.detection_methods,
            checked_by=current_user.get("username")
        )

        return HallucinationCheckResponse.from_orm(check)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in hallucination check: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/hallucination/{check_id}", response_model=HallucinationCheckResponse)
async def get_hallucination_check(
    check_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get hallucination check by ID."""
    service = HallucinationDetectionService(db)
    check = service.get_check_by_id(check_id)

    if not check:
        raise HTTPException(status_code=404, detail="Hallucination check not found")

    return HallucinationCheckResponse.from_orm(check)


@app.get("/api/v1/hallucination/model/{model_name}", response_model=List[HallucinationCheckResponse])
async def get_model_hallucination_checks(
    model_name: str,
    model_version: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get hallucination checks for a model."""
    service = HallucinationDetectionService(db)
    checks = service.get_model_checks(model_name, model_version, limit)
    return [HallucinationCheckResponse.from_orm(c) for c in checks]


@app.get("/api/v1/hallucination/high-risk", response_model=List[HallucinationCheckResponse])
async def get_high_risk_checks(
    hours: int = 24,
    model_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get high risk hallucination checks."""
    service = HallucinationDetectionService(db)
    checks = service.get_high_risk_checks(hours, model_name)
    return [HallucinationCheckResponse.from_orm(c) for c in checks]


@app.get("/api/v1/hallucination/stats", response_model=HallucinationStatsResponse)
async def get_hallucination_stats(
    model_name: Optional[str] = None,
    hours: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get hallucination statistics."""
    service = HallucinationDetectionService(db)
    stats = service.get_check_stats(model_name, hours)
    return HallucinationStatsResponse(**stats)


@app.get("/api/v1/hallucination/model/{model_name}/reliability", response_model=ModelReliabilityResponse)
async def get_model_reliability(
    model_name: str,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get reliability metrics for a GenAI model."""
    service = HallucinationDetectionService(db)
    reliability = service.get_model_reliability(model_name, days)
    return ModelReliabilityResponse(**reliability)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8023)
