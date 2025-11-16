"""FastAPI application for pipeline management."""

from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration

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
    title="DataForge Pipeline API",
    description="API for managing data pipelines",
    version="0.1.0"
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


# Models
class PipelineCreate(BaseModel):
    """Pipeline creation request."""

    name: str
    description: Optional[str] = None
    schedule: Optional[str] = None
    config: dict = {}


class PipelineResponse(BaseModel):
    """Pipeline response."""

    pipeline_id: str
    name: str
    description: Optional[str]
    schedule: Optional[str]
    status: str
    created_at: datetime


class PipelineRunResponse(BaseModel):
    """Pipeline run response."""

    run_id: str
    pipeline_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    records_processed: Optional[int]


# In-memory storage (replace with database in production)
pipelines_db = {}
runs_db = {}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DataForge Pipeline API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    increment_counter("health_checks")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/pipelines", response_model=PipelineResponse)
@track_duration("create_pipeline_duration")
async def create_pipeline(pipeline: PipelineCreate):
    """Create a new pipeline."""
    logger.info("Creating pipeline", name=pipeline.name)

    pipeline_id = f"pipe-{len(pipelines_db) + 1}"

    pipeline_data = {
        "pipeline_id": pipeline_id,
        "name": pipeline.name,
        "description": pipeline.description,
        "schedule": pipeline.schedule,
        "status": "active",
        "created_at": datetime.utcnow()
    }

    pipelines_db[pipeline_id] = pipeline_data

    increment_counter("pipelines_created")

    logger.info("Pipeline created", pipeline_id=pipeline_id)

    return PipelineResponse(**pipeline_data)


@app.get("/pipelines", response_model=List[PipelineResponse])
async def list_pipelines():
    """List all pipelines."""
    logger.info("Listing pipelines")

    return [PipelineResponse(**p) for p in pipelines_db.values()]


@app.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: str):
    """Get pipeline by ID."""
    if pipeline_id not in pipelines_db:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return PipelineResponse(**pipelines_db[pipeline_id])


@app.post("/pipelines/{pipeline_id}/runs", response_model=PipelineRunResponse)
@track_duration("trigger_pipeline_duration")
async def trigger_pipeline(pipeline_id: str):
    """Trigger a pipeline run."""
    if pipeline_id not in pipelines_db:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    logger.info("Triggering pipeline", pipeline_id=pipeline_id)

    run_id = f"run-{len(runs_db) + 1}"

    run_data = {
        "run_id": run_id,
        "pipeline_id": pipeline_id,
        "status": "running",
        "start_time": datetime.utcnow(),
        "end_time": None,
        "records_processed": None
    }

    runs_db[run_id] = run_data

    increment_counter("pipeline_runs_triggered", labels={"pipeline_id": pipeline_id})

    logger.info("Pipeline run triggered", run_id=run_id, pipeline_id=pipeline_id)

    return PipelineRunResponse(**run_data)


@app.get("/runs", response_model=List[PipelineRunResponse])
async def list_runs(pipeline_id: Optional[str] = None):
    """List pipeline runs, optionally filtered by pipeline_id."""
    runs = runs_db.values()

    if pipeline_id:
        runs = [r for r in runs if r["pipeline_id"] == pipeline_id]

    return [PipelineRunResponse(**r) for r in runs]


@app.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_run(run_id: str):
    """Get pipeline run by ID."""
    if run_id not in runs_db:
        raise HTTPException(status_code=404, detail="Run not found")

    return PipelineRunResponse(**runs_db[run_id])


@app.get("/metrics")
async def get_metrics():
    """Get pipeline metrics."""
    return {
        "total_pipelines": len(pipelines_db),
        "total_runs": len(runs_db),
        "active_runs": sum(1 for r in runs_db.values() if r["status"] == "running"),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
