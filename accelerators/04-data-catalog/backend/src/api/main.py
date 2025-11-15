"""FastAPI application for Data Catalog."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration

# Import catalog modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from metadata.catalog import (
    ColumnMetadata,
    DataCatalog,
    DatasetMetadata,
    DatasetStatus,
    DatasetType,
)
from lineage.lineage_tracker import LineageTracker, LineageType
from schema.schema_registry import (
    CompatibilityMode,
    SchemaRegistry,
    SchemaType,
)
from search.semantic_search import SemanticSearchEngine

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DataForge Data Catalog API",
    description="Data catalog with semantic search and lineage tracking",
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
catalog = DataCatalog()
schema_registry = SchemaRegistry()
lineage_tracker = LineageTracker()
search_engine = SemanticSearchEngine()


# Models
class DatasetRegistration(BaseModel):
    """Dataset registration request."""

    name: str
    description: str
    dataset_type: DatasetType
    source: str
    owner: str
    database: Optional[str] = None
    schema: Optional[str] = None
    table: Optional[str] = None
    columns: Optional[List[dict]] = None
    tags: Optional[List[str]] = None


class SchemaRegistration(BaseModel):
    """Schema registration request."""

    name: str
    namespace: str
    schema: dict
    schema_type: SchemaType
    description: str = ""
    compatibility_mode: CompatibilityMode = CompatibilityMode.BACKWARD
    owner: str = "system"
    tags: Optional[List[str]] = None


class LineageTracking(BaseModel):
    """Lineage tracking request."""

    source_datasets: List[str]
    target_dataset: str
    transformation: str
    metadata: Optional[dict] = None


class SearchQuery(BaseModel):
    """Search query request."""

    query: str
    top_k: int = 10
    filters: Optional[dict] = None
    hybrid_alpha: float = Field(default=0.5, ge=0.0, le=1.0)


# Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DataForge Data Catalog API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    increment_counter("health_checks")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Dataset Endpoints
@app.post("/datasets")
@track_duration("register_dataset_duration")
async def register_dataset(registration: DatasetRegistration):
    """Register a new dataset in the catalog."""
    logger.info("Registering dataset", name=registration.name, owner=registration.owner)

    try:
        # Register in catalog
        dataset_id = catalog.register_dataset(
            name=registration.name,
            description=registration.description,
            dataset_type=registration.dataset_type,
            source=registration.source,
            owner=registration.owner,
            database=registration.database,
            schema=registration.schema,
            table=registration.table,
            tags=registration.tags,
        )

        # Index for search
        search_engine.index_dataset(
            dataset_id=dataset_id,
            name=registration.name,
            description=registration.description,
            metadata={"tags": registration.tags or [], "owner": registration.owner},
            columns=[c.get("name") for c in (registration.columns or [])],
        )

        # Add lineage node
        lineage_tracker.add_node(
            node_id=dataset_id,
            node_type="dataset",
            name=registration.name,
            metadata={"source": registration.source},
        )

        increment_counter("datasets_registered")

        logger.info("Dataset registered", dataset_id=dataset_id)

        return {
            "dataset_id": dataset_id,
            "status": "registered",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Dataset registration failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datasets/{dataset_id}")
@track_duration("get_dataset_duration")
async def get_dataset(dataset_id: str):
    """Get dataset metadata."""
    try:
        metadata = catalog.get_dataset(dataset_id)

        return {
            "dataset_id": metadata.dataset_id,
            "name": metadata.name,
            "description": metadata.description,
            "dataset_type": metadata.dataset_type.value,
            "source": metadata.source,
            "owner": metadata.owner,
            "status": metadata.status.value,
            "tags": metadata.tags,
            "created_at": metadata.created_at.isoformat(),
            "updated_at": metadata.updated_at.isoformat(),
            "access_count": metadata.access_count,
            "popularity_score": metadata.popularity_score,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Get dataset failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datasets")
async def list_datasets(
    dataset_type: Optional[DatasetType] = None,
    owner: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
):
    """List datasets with optional filters."""
    datasets = catalog.list_datasets(
        dataset_type=dataset_type,
        owner=owner,
        tags=tags,
    )

    return {
        "datasets": [
            {
                "dataset_id": d.dataset_id,
                "name": d.name,
                "description": d.description,
                "dataset_type": d.dataset_type.value,
                "owner": d.owner,
                "tags": d.tags,
            }
            for d in datasets
        ],
        "count": len(datasets),
    }


@app.post("/datasets/{dataset_id}/tags")
async def add_tags(dataset_id: str, tags: List[str]):
    """Add tags to dataset."""
    try:
        catalog.add_tags(dataset_id, tags)

        return {
            "dataset_id": dataset_id,
            "tags_added": tags,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Search Endpoints
@app.post("/search")
@track_duration("search_duration")
async def search_datasets(query: SearchQuery):
    """Search datasets using semantic search."""
    logger.info("Search request", query=query.query[:100])

    try:
        results = search_engine.search(
            query=query.query,
            top_k=query.top_k,
            filters=query.filters,
            hybrid_alpha=query.hybrid_alpha,
        )

        increment_counter("searches")

        return {
            "query": query.query,
            "results": [
                {
                    "dataset_id": r.dataset_id,
                    "name": r.name,
                    "description": r.description,
                    "score": r.score,
                    "matched_fields": r.matched_fields,
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "count": len(results),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Search failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Schema Endpoints
@app.post("/schemas")
@track_duration("register_schema_duration")
async def register_schema(registration: SchemaRegistration):
    """Register a schema."""
    logger.info("Registering schema", name=registration.name)

    try:
        schema_id = schema_registry.register_schema(
            name=registration.name,
            namespace=registration.namespace,
            schema=registration.schema,
            schema_type=registration.schema_type,
            description=registration.description,
            compatibility_mode=registration.compatibility_mode,
            owner=registration.owner,
            tags=registration.tags,
        )

        increment_counter("schemas_registered")

        return {
            "schema_id": schema_id,
            "status": "registered",
            "version": 1,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Schema registration failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schemas/{schema_id}")
async def get_schema(schema_id: str, version: Optional[int] = None):
    """Get schema by ID."""
    try:
        schema_version = schema_registry.get_schema(schema_id, version)

        return {
            "schema_id": schema_version.schema_id,
            "version": schema_version.version_id,
            "schema": schema_version.schema,
            "schema_type": schema_version.schema_type.value,
            "created_at": schema_version.created_at.isoformat(),
            "created_by": schema_version.created_by,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Lineage Endpoints
@app.post("/lineage/track")
@track_duration("track_lineage_duration")
async def track_lineage(tracking: LineageTracking):
    """Track transformation lineage."""
    logger.info(
        "Tracking lineage",
        sources=len(tracking.source_datasets),
        target=tracking.target_dataset,
    )

    try:
        lineage_tracker.track_transformation(
            source_datasets=tracking.source_datasets,
            target_dataset=tracking.target_dataset,
            transformation=tracking.transformation,
            metadata=tracking.metadata,
        )

        # Update catalog lineage
        catalog.update_lineage(
            dataset_id=tracking.target_dataset,
            upstream=tracking.source_datasets,
        )

        increment_counter("lineage_tracked")

        return {
            "target_dataset": tracking.target_dataset,
            "source_count": len(tracking.source_datasets),
            "status": "tracked",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Lineage tracking failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/lineage/{dataset_id}/upstream")
async def get_upstream_lineage(dataset_id: str, max_depth: int = 5):
    """Get upstream lineage."""
    try:
        lineage = lineage_tracker.get_upstream_lineage(dataset_id, max_depth)

        return {
            "dataset_id": dataset_id,
            "direction": "upstream",
            "nodes": [
                {
                    "node_id": n.node_id,
                    "node_type": n.node_type,
                    "name": n.name,
                    "metadata": n.metadata,
                }
                for n in lineage.nodes
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "relationship": e.relationship_type.value,
                    "metadata": e.metadata,
                }
                for e in lineage.edges
            ],
            "depth": lineage.depth,
        }

    except Exception as e:
        logger.error("Get upstream lineage failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/lineage/{dataset_id}/downstream")
async def get_downstream_lineage(dataset_id: str, max_depth: int = 5):
    """Get downstream lineage."""
    try:
        lineage = lineage_tracker.get_downstream_lineage(dataset_id, max_depth)

        return {
            "dataset_id": dataset_id,
            "direction": "downstream",
            "nodes": [
                {
                    "node_id": n.node_id,
                    "node_type": n.node_type,
                    "name": n.name,
                    "metadata": n.metadata,
                }
                for n in lineage.nodes
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "relationship": e.relationship_type.value,
                    "metadata": e.metadata,
                }
                for e in lineage.edges
            ],
            "depth": lineage.depth,
        }

    except Exception as e:
        logger.error("Get downstream lineage failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/lineage/{dataset_id}/impact")
async def analyze_impact(dataset_id: str):
    """Analyze impact of changes to dataset."""
    try:
        impact = lineage_tracker.analyze_impact(dataset_id)

        return impact

    except Exception as e:
        logger.error("Impact analysis failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Statistics
@app.get("/statistics")
async def get_statistics():
    """Get catalog statistics."""
    catalog_stats = catalog.get_statistics()
    search_stats = search_engine.get_statistics()

    return {
        "catalog": catalog_stats,
        "search": search_stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/metrics")
async def get_metrics():
    """Get catalog metrics."""
    return {
        "catalog": catalog.get_statistics(),
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
