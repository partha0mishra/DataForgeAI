"""MLOps Automation Accelerator - Production API Service.

This service provides production-ready MLOps capabilities:
- Model registration and management with MLflow integration
- Multi-strategy deployments (blue-green, canary, rolling, shadow)
- Statistical drift detection (data, prediction, concept drift)
- Experiment tracking and management
- Model comparison and promotion
"""

import logging
from typing import List, Optional
from contextlib import asynccontextmanager
from datetime import datetime

import numpy as np
from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.database import engine, get_db
from src.models.base import Base
from src.services.mlops_service import MLOpsService
from src.services.drift_service import DriftService
from src.services.experiment_service import ExperimentService
from src.schemas import (
    # Model schemas
    ModelCreate,
    ModelCreateFromMLflow,
    ModelResponse,
    ModelUpdate,
    ModelMetricsUpdate,
    ModelListResponse,
    ModelComparisonResponse,
    ModelPromoteRequest,
    # Deployment schemas
    DeploymentCreate,
    DeploymentResponse,
    DeploymentUpdate,
    DeploymentStatsResponse,
    DeploymentListResponse,
    CanaryTrafficUpdate,
    DeploymentRollbackResponse,
    # Experiment schemas
    ExperimentCreate,
    ExperimentResponse,
    ExperimentUpdate,
    ExperimentDetailsResponse,
    ExperimentLeaderboardResponse,
    ExperimentsSummaryResponse,
    ExperimentSyncRequest,
    RunCreate,
    RunMetricsLog,
    RunParamsLog,
    RunEndRequest,
    RunComparisonResponse,
    # Drift schemas
    DataDriftRequest,
    PredictionDriftRequest,
    ConceptDriftRequest,
    DriftResponse,
    DriftSummaryResponse,
    DeploymentDriftResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Application Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting MLOps Automation Accelerator (Production Mode)")
    logger.info("Initializing database connection...")

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    logger.info("Database initialized successfully")
    logger.info("MLOps Automation service ready to accept requests")

    yield

    # Shutdown
    logger.info("Shutting down MLOps Automation service")
    engine.dispose()
    logger.info("Cleanup complete")


# FastAPI Application
app = FastAPI(
    title="MLOps Automation Accelerator",
    description="""
    Production-ready MLOps platform for automated model lifecycle management.

    ## Features

    * **Model Management**: Register, version, and track ML models with MLflow integration
    * **Multi-Strategy Deployments**: Blue-green, canary, rolling, and shadow deployments
    * **Drift Detection**: Statistical drift detection for data, predictions, and concept
    * **Experiment Tracking**: Full experiment lifecycle with MLflow synchronization
    * **Model Comparison**: Compare models by performance metrics
    * **Auto-Retraining**: Automatic retraining triggers based on drift severity

    ## Deployment Strategies

    * **Blue-Green**: Zero-downtime deployments with instant traffic switch
    * **Canary**: Progressive rollouts with configurable traffic splitting (0-100%)
    * **Rolling**: Gradual updates across replicas
    * **Shadow**: Production traffic mirroring for validation
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health & Status ====================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "service": "mlops-automation",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "MLOps Automation Accelerator",
        "version": "1.0.0",
        "description": "Production-ready MLOps platform",
        "docs": "/docs",
        "health": "/health"
    }


# ==================== Model Management ====================

@app.post(
    "/api/v1/models",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Models"]
)
async def register_model(
    model_data: ModelCreate,
    db: Session = Depends(get_db)
):
    """Register a new ML model with metrics and metadata.

    This endpoint allows manual model registration with performance metrics.
    For MLflow integration, use POST /api/v1/models/from-mlflow instead.
    """
    try:
        service = MLOpsService(db)
        model = service.register_model(
            name=model_data.name,
            version=model_data.version,
            framework=model_data.framework,
            algorithm=model_data.algorithm,
            parameters=model_data.parameters,
            metrics=model_data.metrics,
            tags=model_data.tags,
            description=model_data.description,
            created_by=model_data.created_by
        )
        return ModelResponse.from_model(model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register model: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post(
    "/api/v1/models/from-mlflow",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Models"]
)
async def register_model_from_mlflow(
    model_data: ModelCreateFromMLflow,
    db: Session = Depends(get_db)
):
    """Register a model from an existing MLflow run.

    Automatically extracts metrics, parameters, and metadata from MLflow.
    """
    try:
        service = MLOpsService(db)
        model = service.register_model_from_mlflow(
            mlflow_run_id=model_data.mlflow_run_id,
            model_name=model_data.model_name,
            version=model_data.version,
            tags=model_data.tags
        )
        return ModelResponse.from_model(model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register model from MLflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/api/v1/models/{model_id}",
    response_model=ModelResponse,
    tags=["Models"]
)
async def get_model(
    model_id: str,
    db: Session = Depends(get_db)
):
    """Get model details by ID."""
    from src.repositories.model_repository import ModelRepository

    repo = ModelRepository(db)
    model = repo.get_by_id(model_id)

    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    return ModelResponse.from_model(model)


@app.get(
    "/api/v1/models",
    response_model=ModelListResponse,
    tags=["Models"]
)
async def list_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    framework: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all models with optional filtering."""
    from src.repositories.model_repository import ModelRepository

    repo = ModelRepository(db)
    models = repo.list_all(skip=skip, limit=limit, framework=framework, status=status)
    total = len(repo.list_all())  # TODO: Optimize with count query

    return ModelListResponse(
        models=[ModelResponse.from_model(m) for m in models],
        total=total,
        skip=skip,
        limit=limit
    )


@app.get(
    "/api/v1/models/production",
    response_model=List[ModelResponse],
    tags=["Models"]
)
async def get_production_models(db: Session = Depends(get_db)):
    """Get all models currently in production."""
    from src.repositories.model_repository import ModelRepository

    repo = ModelRepository(db)
    models = repo.get_production_models()

    return [ModelResponse.from_model(m) for m in models]


@app.patch(
    "/api/v1/models/{model_id}",
    response_model=ModelResponse,
    tags=["Models"]
)
async def update_model(
    model_id: str,
    updates: ModelUpdate,
    db: Session = Depends(get_db)
):
    """Update model metadata."""
    from src.repositories.model_repository import ModelRepository

    repo = ModelRepository(db)
    update_data = updates.model_dump(exclude_unset=True)
    model = repo.update(model_id, update_data)

    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    return ModelResponse.from_model(model)


@app.post(
    "/api/v1/models/{model_id}/promote",
    response_model=ModelResponse,
    tags=["Models"]
)
async def promote_model_to_production(
    model_id: str,
    request: ModelPromoteRequest = ModelPromoteRequest(),
    db: Session = Depends(get_db)
):
    """Promote a model to production status.

    Optionally demotes current production models of the same name.
    """
    try:
        service = MLOpsService(db)
        model = service.promote_to_production(
            model_id=model_id,
            demote_current=request.demote_current
        )
        return ModelResponse.from_model(model)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to promote model: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post(
    "/api/v1/models/{model_id}/metrics",
    response_model=ModelResponse,
    tags=["Models"]
)
async def update_model_metrics(
    model_id: str,
    metrics_data: ModelMetricsUpdate,
    db: Session = Depends(get_db)
):
    """Update model performance metrics."""
    from src.repositories.model_repository import ModelRepository

    repo = ModelRepository(db)
    model = repo.update_metrics(model_id, metrics_data.metrics)

    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    return ModelResponse.from_model(model)


@app.post(
    "/api/v1/models/compare",
    response_model=ModelComparisonResponse,
    tags=["Models"]
)
async def compare_models(
    model_ids: List[str],
    db: Session = Depends(get_db)
):
    """Compare multiple models by their performance metrics."""
    try:
        service = MLOpsService(db)
        comparison = service.compare_models(model_ids)
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    "/api/v1/models/{model_id}/details",
    tags=["Models"]
)
async def get_model_with_deployments(
    model_id: str,
    db: Session = Depends(get_db)
):
    """Get model with all deployment information."""
    try:
        service = MLOpsService(db)
        details = service.get_model_with_deployments(model_id)
        return details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Deployments ====================

@app.post(
    "/api/v1/deployments",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Deployments"]
)
async def create_deployment(
    deployment_data: DeploymentCreate,
    db: Session = Depends(get_db)
):
    """Create a new model deployment.

    Supports multiple deployment strategies:
    - **blue_green**: Zero-downtime with instant switch
    - **canary**: Progressive rollout with traffic control
    - **rolling**: Gradual pod updates
    - **shadow**: Production traffic mirroring
    """
    try:
        service = MLOpsService(db)
        deployment = service.create_deployment(
            model_id=deployment_data.model_id,
            deployment_name=deployment_data.deployment_name,
            environment=deployment_data.environment,
            strategy=deployment_data.strategy,
            replicas=deployment_data.replicas,
            resource_config=deployment_data.resource_config,
            traffic_percentage=deployment_data.traffic_percentage,
            deployed_by=deployment_data.deployed_by
        )
        return DeploymentResponse.from_deployment(deployment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create deployment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/api/v1/deployments/{deployment_id}",
    response_model=DeploymentResponse,
    tags=["Deployments"]
)
async def get_deployment(
    deployment_id: str,
    db: Session = Depends(get_db)
):
    """Get deployment details by ID."""
    from src.repositories.deployment_repository import DeploymentRepository

    repo = DeploymentRepository(db)
    deployment = repo.get_by_id(deployment_id)

    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")

    return DeploymentResponse.from_deployment(deployment)


@app.get(
    "/api/v1/deployments",
    response_model=DeploymentListResponse,
    tags=["Deployments"]
)
async def list_deployments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    environment: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all deployments with optional filtering."""
    from src.repositories.deployment_repository import DeploymentRepository

    repo = DeploymentRepository(db)
    deployments = repo.list_all(skip=skip, limit=limit, environment=environment, status=status)
    total = len(repo.list_all())

    return DeploymentListResponse(
        deployments=[DeploymentResponse.from_deployment(d) for d in deployments],
        total=total,
        skip=skip,
        limit=limit
    )


@app.post(
    "/api/v1/deployments/{deployment_id}/traffic",
    response_model=DeploymentResponse,
    tags=["Deployments"]
)
async def update_canary_traffic(
    deployment_id: str,
    traffic_data: CanaryTrafficUpdate,
    db: Session = Depends(get_db)
):
    """Update traffic percentage for canary deployment.

    Allows progressive traffic shifting from 0% to 100%.
    """
    try:
        service = MLOpsService(db)
        deployment = service.update_canary_traffic(
            deployment_id=deployment_id,
            traffic_percentage=traffic_data.traffic_percentage
        )
        return DeploymentResponse.from_deployment(deployment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/api/v1/deployments/{deployment_id}/rollback",
    response_model=DeploymentRollbackResponse,
    tags=["Deployments"]
)
async def rollback_deployment(
    deployment_id: str,
    db: Session = Depends(get_db)
):
    """Rollback a deployment to previous version."""
    try:
        service = MLOpsService(db)
        deployment = service.rollback_deployment(deployment_id)
        return DeploymentRollbackResponse(
            deployment_id=deployment.deployment_id,
            status=deployment.status,
            message="Deployment rolled back successfully",
            rolled_back_at=datetime.utcnow()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    "/api/v1/deployments/{deployment_id}/stats",
    response_model=DeploymentStatsResponse,
    tags=["Deployments"]
)
async def get_deployment_stats(
    deployment_id: str,
    db: Session = Depends(get_db)
):
    """Get deployment statistics including requests, errors, and latency."""
    from src.repositories.deployment_repository import DeploymentRepository

    repo = DeploymentRepository(db)
    stats = repo.get_deployment_stats(deployment_id)

    if not stats:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")

    return DeploymentStatsResponse(**stats)


# ==================== Experiments ====================

@app.post(
    "/api/v1/experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Experiments"]
)
async def create_experiment(
    experiment_data: ExperimentCreate,
    db: Session = Depends(get_db)
):
    """Create a new ML experiment with optional MLflow synchronization."""
    try:
        service = ExperimentService(db)
        experiment = service.create_experiment(
            name=experiment_data.name,
            description=experiment_data.description,
            tags=experiment_data.tags,
            artifact_location=experiment_data.artifact_location,
            created_by=experiment_data.created_by,
            sync_with_mlflow=experiment_data.sync_with_mlflow
        )
        return ExperimentResponse.from_experiment(experiment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create experiment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post(
    "/api/v1/experiments/sync",
    response_model=ExperimentResponse,
    tags=["Experiments"]
)
async def sync_experiment_from_mlflow(
    sync_data: ExperimentSyncRequest,
    db: Session = Depends(get_db)
):
    """Import an existing experiment from MLflow."""
    try:
        service = ExperimentService(db)
        experiment = service.sync_experiment_from_mlflow(
            mlflow_experiment_id=sync_data.mlflow_experiment_id
        )
        return ExperimentResponse.from_experiment(experiment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/api/v1/experiments/{experiment_id}",
    response_model=ExperimentDetailsResponse,
    tags=["Experiments"]
)
async def get_experiment_details(
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed experiment information including all models."""
    try:
        service = ExperimentService(db)
        details = service.get_experiment_details(experiment_id)
        return details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get(
    "/api/v1/experiments",
    response_model=ExperimentsSummaryResponse,
    tags=["Experiments"]
)
async def list_experiments(db: Session = Depends(get_db)):
    """Get summary of all experiments."""
    service = ExperimentService(db)
    summary = service.get_all_experiments_summary()
    return summary


@app.get(
    "/api/v1/experiments/{experiment_id}/leaderboard",
    response_model=ExperimentLeaderboardResponse,
    tags=["Experiments"]
)
async def get_experiment_leaderboard(
    experiment_id: str,
    metric: str = Query("accuracy", description="Metric to rank by"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get top performing models from an experiment."""
    try:
        service = ExperimentService(db)
        leaderboard = service.get_experiment_leaderboard(
            experiment_id=experiment_id,
            metric=metric,
            limit=limit
        )
        return ExperimentLeaderboardResponse(
            experiment_id=experiment_id,
            experiment_name=service.experiment_repo.get_by_id(experiment_id).name,
            metric=metric,
            entries=leaderboard
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post(
    "/api/v1/experiments/runs/start",
    tags=["Experiments"]
)
async def start_run(
    run_data: RunCreate,
    db: Session = Depends(get_db)
):
    """Start a new MLflow run for an experiment."""
    try:
        service = ExperimentService(db)
        run_id = service.start_run(
            experiment_id=run_data.experiment_id,
            run_name=run_data.run_name,
            tags=run_data.tags
        )
        return {"run_id": run_id, "status": "started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/api/v1/experiments/runs/log-metrics",
    tags=["Experiments"]
)
async def log_metrics(
    metrics_data: RunMetricsLog,
    db: Session = Depends(get_db)
):
    """Log metrics to an MLflow run."""
    try:
        service = ExperimentService(db)
        service.log_metrics(
            run_id=metrics_data.run_id,
            metrics=metrics_data.metrics,
            step=metrics_data.step
        )
        return {"status": "logged", "metric_count": len(metrics_data.metrics)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/api/v1/experiments/runs/log-params",
    tags=["Experiments"]
)
async def log_parameters(
    params_data: RunParamsLog,
    db: Session = Depends(get_db)
):
    """Log parameters to an MLflow run."""
    try:
        service = ExperimentService(db)
        service.log_parameters(
            run_id=params_data.run_id,
            params=params_data.params
        )
        return {"status": "logged", "param_count": len(params_data.params)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Drift Detection ====================

@app.post(
    "/api/v1/drift/data-drift",
    response_model=DriftResponse,
    tags=["Drift Detection"]
)
async def detect_data_drift(
    drift_data: DataDriftRequest,
    db: Session = Depends(get_db)
):
    """Detect data drift using statistical tests (Kolmogorov-Smirnov).

    Compares reference data (training) with current production data.
    Returns affected features, p-values, and recommendations.
    """
    try:
        service = DriftService(db)

        # Convert to numpy arrays
        reference_data = np.array(drift_data.reference_data)
        current_data = np.array(drift_data.current_data)

        drift = service.detect_data_drift(
            model_id=drift_data.model_id,
            reference_data=reference_data,
            current_data=current_data,
            feature_names=drift_data.feature_names,
            threshold=drift_data.threshold,
            deployment_id=drift_data.deployment_id
        )
        return DriftResponse.from_drift_detection(drift)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to detect data drift: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post(
    "/api/v1/drift/prediction-drift",
    response_model=DriftResponse,
    tags=["Drift Detection"]
)
async def detect_prediction_drift(
    drift_data: PredictionDriftRequest,
    db: Session = Depends(get_db)
):
    """Detect prediction drift by comparing prediction distributions."""
    try:
        service = DriftService(db)

        reference_predictions = np.array(drift_data.reference_predictions)
        current_predictions = np.array(drift_data.current_predictions)

        drift = service.detect_prediction_drift(
            model_id=drift_data.model_id,
            reference_predictions=reference_predictions,
            current_predictions=current_predictions,
            threshold=drift_data.threshold,
            deployment_id=drift_data.deployment_id
        )
        return DriftResponse.from_drift_detection(drift)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/api/v1/drift/concept-drift",
    response_model=DriftResponse,
    tags=["Drift Detection"]
)
async def detect_concept_drift(
    drift_data: ConceptDriftRequest,
    db: Session = Depends(get_db)
):
    """Detect concept drift by monitoring model performance degradation."""
    try:
        service = DriftService(db)

        true_labels = np.array(drift_data.true_labels)
        predictions = np.array(drift_data.predictions)

        drift = service.detect_concept_drift(
            model_id=drift_data.model_id,
            true_labels=true_labels,
            predictions=predictions,
            historical_accuracy=drift_data.historical_accuracy,
            threshold=drift_data.threshold,
            deployment_id=drift_data.deployment_id
        )
        return DriftResponse.from_drift_detection(drift)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/api/v1/drift/summary/{model_id}",
    response_model=DriftSummaryResponse,
    tags=["Drift Detection"]
)
async def get_drift_summary(
    model_id: str,
    hours: int = Query(24, ge=1, le=720, description="Time window in hours"),
    db: Session = Depends(get_db)
):
    """Get drift detection summary for a model over a time window."""
    try:
        service = DriftService(db)
        summary = service.get_drift_summary(model_id=model_id, hours=hours)
        return summary
    except Exception as e:
        logger.error(f"Failed to get drift summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/api/v1/drift/deployment/{deployment_id}",
    response_model=DeploymentDriftResponse,
    tags=["Drift Detection"]
)
async def monitor_deployment_drift(
    deployment_id: str,
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db)
):
    """Monitor drift for a specific deployment."""
    try:
        service = DriftService(db)
        monitoring = service.monitor_deployment_drift(
            deployment_id=deployment_id,
            data_window_hours=hours
        )
        return monitoring
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Startup ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8015,
        reload=True,
        log_level="info"
    )
