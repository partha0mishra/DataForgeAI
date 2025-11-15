"""FastAPI application for BI Dashboarding."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration

# Import dashboard modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.dashboard_manager import (
    Dashboard,
    DashboardManager,
    DashboardStatus,
    VisualizationType,
)
from visualization.chart_builder import ChartBuilder
from data.query_engine import QueryEngine

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DataForge BI Dashboarding API",
    description="Business Intelligence dashboards with interactive visualizations",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
dashboard_manager = DashboardManager()
chart_builder = ChartBuilder()
query_engine = QueryEngine()


# Models
class DashboardCreate(BaseModel):
    """Dashboard creation request."""

    name: str
    description: str
    owner: str
    tags: Optional[List[str]] = None


class DataSourceAdd(BaseModel):
    """Add data source request."""

    source_id: str
    name: str
    type: str  # database, file, api
    connection_string: Optional[str] = None
    query: Optional[str] = None
    file_path: Optional[str] = None
    api_endpoint: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class VisualizationAdd(BaseModel):
    """Add visualization request."""

    viz_id: str
    name: str
    type: VisualizationType
    data_source_id: str
    config: Dict[str, Any]
    position: Optional[Dict[str, int]] = None


class DataQuery(BaseModel):
    """Data query request."""

    source_type: str
    query: Optional[str] = None
    connection_string: Optional[str] = None
    file_path: Optional[str] = None
    api_endpoint: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    transformations: Optional[List[Dict[str, Any]]] = None


# Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DataForge BI Dashboarding API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    increment_counter("health_checks")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Dashboard Endpoints
@app.post("/dashboards")
@track_duration("create_dashboard_duration")
async def create_dashboard(dashboard: DashboardCreate):
    """Create new dashboard."""
    logger.info("Creating dashboard", name=dashboard.name, owner=dashboard.owner)

    try:
        created = dashboard_manager.create_dashboard(
            name=dashboard.name,
            description=dashboard.description,
            owner=dashboard.owner,
            tags=dashboard.tags,
        )

        increment_counter("dashboards_created")

        return {
            "dashboard_id": created.dashboard_id,
            "name": created.name,
            "status": created.status.value,
            "created_at": created.created_at.isoformat(),
        }

    except Exception as e:
        logger.error("Dashboard creation failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboards")
async def list_dashboards(
    owner: Optional[str] = None,
    tags: Optional[str] = None,
    status: Optional[DashboardStatus] = None,
):
    """List dashboards."""
    try:
        tag_list = tags.split(",") if tags else None

        dashboards = dashboard_manager.list_dashboards(
            owner=owner,
            tags=tag_list,
            status=status,
        )

        return {
            "dashboards": [
                {
                    "dashboard_id": d.dashboard_id,
                    "name": d.name,
                    "description": d.description,
                    "owner": d.owner,
                    "status": d.status.value,
                    "visualizations_count": len(d.visualizations),
                    "created_at": d.created_at.isoformat(),
                }
                for d in dashboards
            ],
            "count": len(dashboards),
        }

    except Exception as e:
        logger.error("List dashboards failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: str):
    """Get dashboard details."""
    try:
        dashboard = dashboard_manager.get_dashboard(dashboard_id)

        return {
            "dashboard_id": dashboard.dashboard_id,
            "name": dashboard.name,
            "description": dashboard.description,
            "owner": dashboard.owner,
            "status": dashboard.status.value,
            "data_sources": [
                {
                    "source_id": ds.source_id,
                    "name": ds.name,
                    "type": ds.type,
                }
                for ds in dashboard.data_sources
            ],
            "visualizations": [
                {
                    "viz_id": viz.viz_id,
                    "name": viz.name,
                    "type": viz.type.value,
                    "data_source_id": viz.data_source_id,
                    "position": viz.position,
                }
                for viz in dashboard.visualizations
            ],
            "tags": dashboard.tags,
            "created_at": dashboard.created_at.isoformat(),
            "updated_at": dashboard.updated_at.isoformat(),
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Get dashboard failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dashboards/{dashboard_id}/data-sources")
async def add_data_source(dashboard_id: str, data_source: DataSourceAdd):
    """Add data source to dashboard."""
    logger.info(
        "Adding data source",
        dashboard_id=dashboard_id,
        source_id=data_source.source_id,
    )

    try:
        dashboard_manager.add_data_source(
            dashboard_id=dashboard_id,
            source_id=data_source.source_id,
            name=data_source.name,
            type=data_source.type,
            connection_string=data_source.connection_string,
            query=data_source.query,
            file_path=data_source.file_path,
            api_endpoint=data_source.api_endpoint,
            parameters=data_source.parameters,
        )

        increment_counter("data_sources_added")

        return {
            "dashboard_id": dashboard_id,
            "source_id": data_source.source_id,
            "status": "added",
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Add data source failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dashboards/{dashboard_id}/visualizations")
async def add_visualization(dashboard_id: str, viz: VisualizationAdd):
    """Add visualization to dashboard."""
    logger.info(
        "Adding visualization",
        dashboard_id=dashboard_id,
        viz_id=viz.viz_id,
        type=viz.type.value,
    )

    try:
        dashboard_manager.add_visualization(
            dashboard_id=dashboard_id,
            viz_id=viz.viz_id,
            name=viz.name,
            type=viz.type,
            data_source_id=viz.data_source_id,
            config=viz.config,
            position=viz.position,
        )

        increment_counter("visualizations_added")

        return {
            "dashboard_id": dashboard_id,
            "viz_id": viz.viz_id,
            "type": viz.type.value,
            "status": "added",
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Add visualization failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/dashboards/{dashboard_id}/visualizations/{viz_id}")
async def remove_visualization(dashboard_id: str, viz_id: str):
    """Remove visualization from dashboard."""
    try:
        dashboard_manager.remove_visualization(dashboard_id, viz_id)

        return {
            "dashboard_id": dashboard_id,
            "viz_id": viz_id,
            "status": "removed",
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/dashboards/{dashboard_id}/publish")
async def publish_dashboard(dashboard_id: str):
    """Publish dashboard."""
    try:
        dashboard_manager.publish_dashboard(dashboard_id)

        increment_counter("dashboards_published")

        return {
            "dashboard_id": dashboard_id,
            "status": "published",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/dashboards/{dashboard_id}/clone")
async def clone_dashboard(dashboard_id: str, new_name: str, owner: str):
    """Clone dashboard."""
    try:
        cloned = dashboard_manager.clone_dashboard(dashboard_id, new_name, owner)

        return {
            "source_id": dashboard_id,
            "new_dashboard_id": cloned.dashboard_id,
            "name": cloned.name,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/dashboards/{dashboard_id}/export")
async def export_dashboard(dashboard_id: str):
    """Export dashboard as JSON."""
    try:
        export = dashboard_manager.export_dashboard(dashboard_id)
        return export

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(dashboard_id: str):
    """Delete dashboard."""
    try:
        dashboard_manager.delete_dashboard(dashboard_id)

        return {
            "dashboard_id": dashboard_id,
            "status": "deleted",
        }

    except Exception as e:
        logger.error("Delete dashboard failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Data & Visualization Endpoints
@app.post("/data/query")
@track_duration("query_data_duration")
async def query_data(query: DataQuery):
    """Query data from source."""
    logger.info("Querying data", source_type=query.source_type)

    try:
        df = query_engine.execute_query(
            source_type=query.source_type,
            query=query.query,
            connection_string=query.connection_string,
            file_path=query.file_path,
            api_endpoint=query.api_endpoint,
            parameters=query.parameters,
        )

        # Apply transformations
        if query.transformations:
            df = query_engine.transform_data(df, query.transformations)

        # Convert to JSON
        data = df.to_dict(orient="records")

        return {
            "data": data,
            "rows": len(data),
            "columns": list(df.columns),
        }

    except Exception as e:
        logger.error("Query failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/data/preview")
async def preview_data(query: DataQuery, n: int = 10):
    """Preview data from source."""
    try:
        df = query_engine.preview_data(
            source_type=query.source_type,
            n=n,
            query=query.query,
            connection_string=query.connection_string,
            file_path=query.file_path,
            api_endpoint=query.api_endpoint,
            parameters=query.parameters,
        )

        data = df.to_dict(orient="records")

        return {
            "data": data,
            "rows": len(data),
            "columns": list(df.columns),
            "schema": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

    except Exception as e:
        logger.error("Preview failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboards/{dashboard_id}/render", response_class=HTMLResponse)
async def render_dashboard(dashboard_id: str):
    """Render dashboard as HTML."""
    try:
        dashboard = dashboard_manager.get_dashboard(dashboard_id)

        # Build HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{dashboard.name}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .dashboard-info {{ margin-bottom: 20px; }}
                .visualization {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>{dashboard.name}</h1>
            <div class="dashboard-info">
                <p>{dashboard.description}</p>
                <p>Owner: {dashboard.owner} | Status: {dashboard.status.value}</p>
            </div>
            <p>This is a static render. Use the API to get interactive visualizations.</p>
        </body>
        </html>
        """

        return html

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Statistics
@app.get("/statistics")
async def get_statistics():
    """Get dashboarding statistics."""
    all_dashboards = dashboard_manager.list_dashboards()

    published = sum(1 for d in all_dashboards if d.status == DashboardStatus.PUBLISHED)
    draft = sum(1 for d in all_dashboards if d.status == DashboardStatus.DRAFT)

    total_visualizations = sum(len(d.visualizations) for d in all_dashboards)

    return {
        "total_dashboards": len(all_dashboards),
        "published_dashboards": published,
        "draft_dashboards": draft,
        "total_visualizations": total_visualizations,
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005)
