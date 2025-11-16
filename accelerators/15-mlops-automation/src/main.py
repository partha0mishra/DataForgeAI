"""MLOps Automation Accelerator - Main API Service.

This service provides automated model deployment, monitoring, drift detection,
and retraining capabilities for machine learning models.
"""

import os
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime

# Shared libraries
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../shared-libraries/dataforge-common"))

from dataforge_common.logging import get_logger
from dataforge_common.tracing import get_tracing
from dataforge_common.security import get_current_user, require_roles
from dataforge_common.settings import get_settings

from .model_deployment import ModelDeploymentManager
from .drift_detection import DriftDetectionManager
from .retraining import RetrainingManager
from .ab_testing import ABTestingManager
from .model_registry import ModelRegistryClient

logger = get_logger(__name__)
settings = get_settings()


# Pydantic Models
class ModelDeploymentRequest(BaseModel):
    """Model deployment request."""
    model_id: str = Field(..., description="Unique model identifier")
    model_uri: str = Field(..., description="MLflow model URI (e.g., models:/my_model/1)")
    environment: str = Field(..., description="Deployment environment (dev/staging/production)")
    deployment_strategy: str = Field(default="blue_green", description="Deployment strategy")
    traffic_percentage: int = Field(default=100, ge=0, le=100, description="Traffic percentage for canary")
    resource_requirements: Optional[dict] = Field(default=None, description="CPU/memory requirements")


class ModelDeploymentResponse(BaseModel):
    """Model deployment response."""
    deployment_id: str
    model_id: str
    environment: str
    status: str
    endpoint_url: str
    created_at: datetime


class DriftAnalysisRequest(BaseModel):
    """Drift analysis request."""
    model_id: str
    reference_data_uri: Optional[str] = None
    current_data_uri: Optional[str] = None
    features: Optional[list[str]] = None


class DriftAnalysisResponse(BaseModel):
    """Drift analysis response."""
    model_id: str
    has_drift: bool
    drift_score: float
    features_with_drift: list[str]
    analysis_timestamp: datetime
    recommendations: list[str]


class RetrainingRequest(BaseModel):
    """Retraining request."""
    model_id: str
    trigger_reason: str = Field(default="manual", description="Reason for retraining")
    training_data_uri: Optional[str] = None
    hyperparameters: Optional[dict] = None


class RetrainingResponse(BaseModel):
    """Retraining response."""
    job_id: str
    model_id: str
    status: str
    started_at: datetime


class ABTestRequest(BaseModel):
    """A/B test creation request."""
    name: str
    model_a: str
    model_b: str
    traffic_split: dict[str, int] = Field(default={"model_a": 50, "model_b": 50})
    success_metric: str = Field(default="accuracy")
    duration_days: int = Field(default=7, ge=1, le=30)


class ABTestResponse(BaseModel):
    """A/B test response."""
    experiment_id: str
    name: str
    status: str
    created_at: datetime


# Application Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting MLOps Automation Accelerator")

    # Initialize tracing
    tracing = get_tracing()
    tracing.instrument_fastapi(app)

    # Initialize managers
    app.state.model_deployment = ModelDeploymentManager()
    app.state.drift_detection = DriftDetectionManager()
    app.state.retraining = RetrainingManager()
    app.state.ab_testing = ABTestingManager()
    app.state.model_registry = ModelRegistryClient()

    logger.info("MLOps Automation service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down MLOps Automation service")


# FastAPI Application
app = FastAPI(
    title="MLOps Automation Accelerator",
    description="Automated model deployment, monitoring, and retraining",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mlops-automation",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# Model Deployment Endpoints
@app.post("/api/v1/models/deploy", response_model=ModelDeploymentResponse)
async def deploy_model(
    request: ModelDeploymentRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_roles(["developer", "admin"]))
):
    """Deploy a model to specified environment.

    Supports multiple deployment strategies:
    - blue_green: Zero-downtime deployment with instant switch
    - canary: Gradual rollout with traffic splitting
    - rolling: Progressive update across instances
    """
    logger.info(f"Deploying model {request.model_id} to {request.environment}")

    try:
        deployment_manager = app.state.model_deployment

        # Validate model exists in registry
        model_info = app.state.model_registry.get_model(request.model_uri)
        if not model_info:
            raise HTTPException(status_code=404, detail=f"Model not found: {request.model_uri}")

        # Deploy model
        deployment = await deployment_manager.deploy(
            model_id=request.model_id,
            model_uri=request.model_uri,
            environment=request.environment,
            strategy=request.deployment_strategy,
            traffic_percentage=request.traffic_percentage,
            resource_requirements=request.resource_requirements
        )

        # Start monitoring in background
        background_tasks.add_task(
            deployment_manager.start_monitoring,
            deployment_id=deployment["deployment_id"]
        )

        return ModelDeploymentResponse(**deployment)

    except Exception as e:
        logger.error(f"Model deployment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/models/{model_id}/status")
async def get_model_status(
    model_id: str,
    current_user=Depends(get_current_user)
):
    """Get deployment status for a model."""
    deployment_manager = app.state.model_deployment
    status = await deployment_manager.get_status(model_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")

    return status


@app.post("/api/v1/models/{model_id}/rollback")
async def rollback_model(
    model_id: str,
    version: Optional[int] = None,
    current_user=Depends(require_roles(["admin"]))
):
    """Rollback model to previous version."""
    logger.warning(f"Rolling back model {model_id} to version {version}")

    deployment_manager = app.state.model_deployment
    result = await deployment_manager.rollback(model_id, version)

    return {
        "model_id": model_id,
        "status": "rolled_back",
        "current_version": result["version"],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.delete("/api/v1/models/{model_id}")
async def undeploy_model(
    model_id: str,
    environment: str,
    current_user=Depends(require_roles(["admin"]))
):
    """Undeploy model from environment."""
    logger.info(f"Undeploying model {model_id} from {environment}")

    deployment_manager = app.state.model_deployment
    await deployment_manager.undeploy(model_id, environment)

    return {
        "model_id": model_id,
        "environment": environment,
        "status": "undeployed",
        "timestamp": datetime.utcnow().isoformat()
    }


# Drift Detection Endpoints
@app.get("/api/v1/models/{model_id}/drift", response_model=DriftAnalysisResponse)
async def get_drift_analysis(
    model_id: str,
    current_user=Depends(get_current_user)
):
    """Get latest drift analysis for a model."""
    drift_manager = app.state.drift_detection
    analysis = await drift_manager.get_latest_analysis(model_id)

    if not analysis:
        raise HTTPException(status_code=404, detail=f"No drift analysis found for {model_id}")

    return DriftAnalysisResponse(**analysis)


@app.post("/api/v1/models/{model_id}/drift/analyze")
async def analyze_drift(
    model_id: str,
    request: DriftAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user)
):
    """Trigger drift analysis for a model."""
    drift_manager = app.state.drift_detection

    # Run analysis in background
    background_tasks.add_task(
        drift_manager.analyze,
        model_id=model_id,
        reference_data_uri=request.reference_data_uri,
        current_data_uri=request.current_data_uri,
        features=request.features
    )

    return {
        "model_id": model_id,
        "status": "analysis_started",
        "timestamp": datetime.utcnow().isoformat()
    }


# Retraining Endpoints
@app.post("/api/v1/retraining/trigger", response_model=RetrainingResponse)
async def trigger_retraining(
    request: RetrainingRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_roles(["developer", "admin"]))
):
    """Trigger model retraining."""
    logger.info(f"Triggering retraining for {request.model_id} (reason: {request.trigger_reason})")

    retraining_manager = app.state.retraining

    job = await retraining_manager.trigger(
        model_id=request.model_id,
        trigger_reason=request.trigger_reason,
        training_data_uri=request.training_data_uri,
        hyperparameters=request.hyperparameters
    )

    # Run retraining in background
    background_tasks.add_task(
        retraining_manager.execute,
        job_id=job["job_id"]
    )

    return RetrainingResponse(**job)


@app.get("/api/v1/retraining/{job_id}/status")
async def get_retraining_status(
    job_id: str,
    current_user=Depends(get_current_user)
):
    """Get retraining job status."""
    retraining_manager = app.state.retraining
    status = await retraining_manager.get_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return status


@app.get("/api/v1/retraining/history")
async def get_retraining_history(
    model_id: Optional[str] = None,
    limit: int = 10,
    current_user=Depends(get_current_user)
):
    """Get retraining history."""
    retraining_manager = app.state.retraining
    history = await retraining_manager.get_history(model_id, limit)

    return {"history": history}


# A/B Testing Endpoints
@app.post("/api/v1/experiments/create", response_model=ABTestResponse)
async def create_experiment(
    request: ABTestRequest,
    current_user=Depends(require_roles(["developer", "admin"]))
):
    """Create A/B test experiment."""
    logger.info(f"Creating A/B test: {request.name}")

    ab_testing_manager = app.state.ab_testing

    experiment = await ab_testing_manager.create_experiment(
        name=request.name,
        model_a=request.model_a,
        model_b=request.model_b,
        traffic_split=request.traffic_split,
        success_metric=request.success_metric,
        duration_days=request.duration_days
    )

    return ABTestResponse(**experiment)


@app.get("/api/v1/experiments/{experiment_id}/results")
async def get_experiment_results(
    experiment_id: str,
    current_user=Depends(get_current_user)
):
    """Get A/B test results."""
    ab_testing_manager = app.state.ab_testing
    results = await ab_testing_manager.get_results(experiment_id)

    if not results:
        raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")

    return results


@app.post("/api/v1/experiments/{experiment_id}/promote")
async def promote_winner(
    experiment_id: str,
    current_user=Depends(require_roles(["admin"]))
):
    """Promote winning model from A/B test."""
    logger.info(f"Promoting winner from experiment {experiment_id}")

    ab_testing_manager = app.state.ab_testing
    result = await ab_testing_manager.promote_winner(experiment_id)

    return result


# Metrics Endpoint
@app.get("/api/v1/models/{model_id}/metrics")
async def get_model_metrics(
    model_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    current_user=Depends(get_current_user)
):
    """Get model performance metrics."""
    deployment_manager = app.state.model_deployment
    metrics = await deployment_manager.get_metrics(
        model_id,
        start_time=start_time,
        end_time=end_time
    )

    return metrics


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8015,
        reload=True
    )
