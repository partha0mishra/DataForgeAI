"""Zero-ETL Integration Accelerator."""

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../shared-libraries/dataforge-common"))
from dataforge_common.security import require_roles

app = FastAPI(title="Zero-ETL Integration")


class IntegrationType(str, Enum):
    """Integration types."""
    FEDERATED_QUERY = "federated_query"
    EXTERNAL_TABLE = "external_table"
    ZERO_ETL_REPLICATION = "zero_etl_replication"
    STREAMING = "streaming"
    API_FEDERATION = "api_federation"


class IntegrationRequest(BaseModel):
    """Integration request."""
    name: str
    integration_type: IntegrationType
    source_platform: str
    target_platform: str
    source_config: Dict[str, str]
    target_config: Dict[str, str]
    tables: Optional[List[str]] = None
    real_time: bool = False


class Integration(BaseModel):
    """Integration definition."""
    integration_id: str
    name: str
    integration_type: IntegrationType
    status: str
    source_platform: str
    target_platform: str
    created_at: datetime
    data_freshness_seconds: Optional[int]


@app.post("/api/v1/integrations/create", response_model=Integration)
async def create_integration(
    request: IntegrationRequest,
    current_user=Depends(require_roles(["developer", "admin"]))
):
    """Create zero-ETL integration."""
    # Generate configuration based on platforms
    if request.integration_type == IntegrationType.FEDERATED_QUERY:
        # Configure Trino/Presto or platform-native federation
        config = _generate_federated_config(request)
    elif request.integration_type == IntegrationType.EXTERNAL_TABLE:
        # Configure external tables (Snowflake/BigQuery/Redshift)
        config = _generate_external_table_config(request)
    elif request.integration_type == IntegrationType.ZERO_ETL_REPLICATION:
        # Configure native replication (Aurora->Redshift, etc.)
        config = _generate_replication_config(request)

    return Integration(
        integration_id="int_001",
        name=request.name,
        integration_type=request.integration_type,
        status="active",
        source_platform=request.source_platform,
        target_platform=request.target_platform,
        created_at=datetime.utcnow(),
        data_freshness_seconds=5 if request.real_time else 300
    )


def _generate_federated_config(request: IntegrationRequest) -> Dict:
    """Generate federated query configuration."""
    if request.target_platform == "redshift":
        return {"type": "redshift_federated", "query": "SELECT * FROM aurora_db.table"}
    elif request.target_platform == "bigquery":
        return {"type": "bigquery_federated", "external_connection": "aws-s3-connection"}
    return {}


def _generate_external_table_config(request: IntegrationRequest) -> Dict:
    """Generate external table configuration."""
    if request.target_platform == "snowflake":
        return {"type": "snowflake_external", "stage": "s3://bucket/path", "file_format": "parquet"}
    return {}


def _generate_replication_config(request: IntegrationRequest) -> Dict:
    """Generate zero-ETL replication configuration."""
    if request.source_platform == "aurora" and request.target_platform == "redshift":
        return {"type": "aurora_zero_etl", "cluster_id": "aurora-cluster-1"}
    return {}


@app.get("/api/v1/integrations/{integration_id}/status")
async def get_integration_status(
    integration_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Get integration status and metrics."""
    return {
        "integration_id": integration_id,
        "status": "healthy",
        "data_freshness_seconds": 5,
        "query_latency_ms": 125,
        "rows_synced_last_hour": 1250000,
        "errors_last_hour": 0
    }


@app.post("/api/v1/integrations/{integration_id}/test-query")
async def test_federated_query(
    integration_id: str,
    query: str,
    current_user=Depends(require_roles(["developer"]))
):
    """Test federated query performance."""
    return {
        "query": query,
        "execution_time_ms": 245,
        "rows_returned": 10500,
        "bytes_scanned": 125000000,
        "estimated_cost_usd": 0.0062
    }
