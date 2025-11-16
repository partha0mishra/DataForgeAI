"""FastAPI application for Model Factory."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration

# Import model factory modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry.model_registry import ModelRegistry, ModelStage
from serving.model_server import ModelServer

# Import authentication
try:
    from dataforge_common import (
        get_current_user,
        get_optional_user,
        require_roles,
        create_auth_router,
        User,
    )
    AUTH_ENABLED = True
except ImportError:
    print("Warning: dataforge-common not installed. Authentication disabled.")
    AUTH_ENABLED = False


logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DataForge Model Factory API",
    description="ML model training, registry, and serving",
    version="0.1.0",
)
# Include authentication router if available
if AUTH_ENABLED:
    auth_router = create_auth_router()
    app.include_router(auth_router)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
model_registry = ModelRegistry()
model_server = ModelServer(registry=model_registry)


# Models
class ModelRegistration(BaseModel):
    """Model registration request."""

    model_uri: str  # runs:/run_id/model
    name: str
    description: str = ""
    tags: Optional[Dict[str, str]] = None


class StageTransition(BaseModel):
    """Stage transition request."""

    stage: ModelStage
    archive_existing: bool = True


class PredictRequest(BaseModel):
    """Prediction request."""

    model_name: str
    model_version: Optional[str] = None
    model_stage: Optional[str] = "Production"
    features: Optional[Dict[str, Any]] = None
    instances: Optional[List[Dict[str, Any]]] = None


class ModelLoad(BaseModel):
    """Model load request."""

    name: str
    version: Optional[str] = None
    stage: Optional[str] = None


# Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DataForge Model Factory API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    increment_counter("health_checks")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Registry Endpoints
@app.post("/registry/models")
@track_duration("register_model_duration")
async def register_model(registration: ModelRegistration):
    """Register a model in the registry."""
    logger.info("Registering model", name=registration.name)

    try:
        version = model_registry.register_model(
            model_uri=registration.model_uri,
            name=registration.name,
            description=registration.description,
            tags=registration.tags,
        )

        increment_counter("models_registered")

        return {
            "name": registration.name,
            "version": version,
            "status": "registered",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Model registration failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/registry/models")
async def list_models():
    """List all registered models."""
    try:
        models = model_registry.list_models()

        return {
            "models": [
                {
                    "name": m.name,
                    "latest_version": m.latest_version,
                    "description": m.description,
                    "tags": m.tags,
                    "versions": [
                        {
                            "version": v.version,
                            "stage": v.stage.value,
                            "created_at": v.created_at.isoformat(),
                        }
                        for v in m.versions
                    ],
                }
                for m in models
            ],
            "count": len(models),
        }

    except Exception as e:
        logger.error("List models failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/registry/models/{name}")
async def get_model_info(name: str):
    """Get model information."""
    try:
        models = model_registry.list_models()
        matching = [m for m in models if m.name == name]

        if not matching:
            raise HTTPException(status_code=404, detail=f"Model not found: {name}")

        model = matching[0]

        return {
            "name": model.name,
            "latest_version": model.latest_version,
            "description": model.description,
            "tags": model.tags,
            "versions": [
                {
                    "version": v.version,
                    "stage": v.stage.value,
                    "run_id": v.run_id,
                    "created_at": v.created_at.isoformat(),
                    "metrics": v.metrics,
                    "description": v.description,
                }
                for v in model.versions
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get model failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/registry/models/{name}/versions/{version}")
async def get_model_version(name: str, version: str):
    """Get specific model version."""
    try:
        model_version = model_registry.get_model_version(name, version)

        return {
            "name": model_version.name,
            "version": model_version.version,
            "stage": model_version.stage.value,
            "run_id": model_version.run_id,
            "created_at": model_version.created_at.isoformat(),
            "updated_at": model_version.updated_at.isoformat(),
            "description": model_version.description,
            "tags": model_version.tags,
            "metrics": model_version.metrics,
        }

    except Exception as e:
        logger.error("Get model version failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/registry/models/{name}/versions/{version}/stage")
@track_duration("transition_stage_duration")
async def transition_stage(name: str, version: str, transition: StageTransition):
    """Transition model version to new stage."""
    logger.info(
        "Transitioning model stage",
        name=name,
        version=version,
        stage=transition.stage.value,
    )

    try:
        model_registry.transition_stage(
            name=name,
            version=version,
            stage=transition.stage,
            archive_existing=transition.archive_existing,
        )

        increment_counter(
            "stage_transitions",
            labels={"stage": transition.stage.value},
        )

        return {
            "name": name,
            "version": version,
            "stage": transition.stage.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Stage transition failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/registry/models/{name}/versions/{version}/promote")
async def promote_to_production(name: str, version: str):
    """Promote model to production."""
    logger.info("Promoting to production", name=name, version=version)

    try:
        model_registry.promote_to_production(name, version)

        increment_counter("production_promotions")

        return {
            "name": name,
            "version": version,
            "stage": "Production",
            "status": "promoted",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Promotion failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/registry/models/{name}/production")
async def get_production_model(name: str):
    """Get production version of model."""
    try:
        production_model = model_registry.get_production_model(name)

        if not production_model:
            raise HTTPException(
                status_code=404,
                detail=f"No production model found for {name}",
            )

        return {
            "name": production_model.name,
            "version": production_model.version,
            "stage": production_model.stage.value,
            "metrics": production_model.metrics,
            "created_at": production_model.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get production model failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/registry/models/{name}/versions/{version}/lineage")
async def get_model_lineage(name: str, version: str):
    """Get model lineage."""
    try:
        lineage = model_registry.get_model_lineage(name, version)

        return lineage

    except Exception as e:
        logger.error("Get lineage failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Serving Endpoints
@app.post("/serving/load")
async def load_model(load_request: ModelLoad):
    """Load model into serving cache."""
    logger.info("Loading model", name=load_request.name)

    try:
        model_server.load_model(
            name=load_request.name,
            version=load_request.version,
            stage=load_request.stage,
        )

        return {
            "name": load_request.name,
            "status": "loaded",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Model load failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/serving/predict")
@track_duration("prediction_latency_ms")
async def predict(request: PredictRequest):
    """Make predictions."""
    logger.info("Prediction request", model=request.model_name)

    try:
        response = model_server.predict(
            model_name=request.model_name,
            features=request.features,
            instances=request.instances,
            model_version=request.model_version,
            model_stage=request.model_stage,
        )

        return {
            "predictions": response.predictions,
            "model_name": response.model_name,
            "model_version": response.model_version,
            "count": response.prediction_count,
            "timestamp": response.timestamp,
            "latency_ms": response.latency_ms,
        }

    except Exception as e:
        logger.error("Prediction failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/serving/predict_proba")
async def predict_proba(request: PredictRequest):
    """Make probability predictions."""
    logger.info("Probability prediction request", model=request.model_name)

    try:
        response = model_server.predict_proba(
            model_name=request.model_name,
            features=request.features,
            instances=request.instances,
            model_version=request.model_version,
            model_stage=request.model_stage,
        )

        return {
            "probabilities": response.predictions,
            "model_name": response.model_name,
            "model_version": response.model_version,
            "count": response.prediction_count,
            "timestamp": response.timestamp,
        }

    except Exception as e:
        logger.error("Probability prediction failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/serving/models")
async def get_loaded_models():
    """Get loaded models."""
    models = model_server.get_loaded_models()

    return {
        "models": models,
        "count": len(models),
    }


@app.delete("/serving/models/{name}/versions/{version}")
async def unload_model(name: str, version: str):
    """Unload model from cache."""
    try:
        model_server.unload_model(name, version)

        return {
            "name": name,
            "version": version,
            "status": "unloaded",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Model unload failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Statistics
@app.get("/statistics")
async def get_statistics():
    """Get model factory statistics."""
    registry_models = model_registry.list_models()
    server_stats = model_server.get_server_stats()

    return {
        "registry": {
            "total_models": len(registry_models),
            "models_by_stage": {
                "production": sum(
                    1
                    for m in registry_models
                    for v in m.versions
                    if v.stage == ModelStage.PRODUCTION
                ),
                "staging": sum(
                    1
                    for m in registry_models
                    for v in m.versions
                    if v.stage == ModelStage.STAGING
                ),
            },
        },
        "serving": server_stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/metrics")
async def get_metrics():
    """Get model factory metrics."""
    server_stats = model_server.get_server_stats()

    return {
        "serving": server_stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
