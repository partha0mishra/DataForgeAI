"""Pydantic schemas for deployment operations."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class DeploymentCreate(BaseModel):
    """Schema for creating a new deployment."""

    model_id: str = Field(..., min_length=1, description="Model identifier")
    deployment_name: str = Field(..., min_length=1, max_length=200, description="Deployment name")
    environment: str = Field(..., pattern="^(dev|staging|production)$", description="Target environment")
    strategy: str = Field(
        "rolling",
        pattern="^(blue_green|canary|rolling|shadow)$",
        description="Deployment strategy"
    )
    replicas: int = Field(1, ge=1, le=100, description="Number of replicas")
    resource_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Resource configuration (CPU, memory, GPU)"
    )
    traffic_percentage: int = Field(
        100,
        ge=0,
        le=100,
        description="Traffic percentage for canary deployments"
    )
    deployed_by: Optional[str] = Field(None, max_length=100, description="Deployer identifier")

    @field_validator("traffic_percentage")
    @classmethod
    def validate_canary_traffic(cls, v, info):
        """Validate traffic percentage for canary deployments."""
        if info.data.get("strategy") == "canary" and v == 0:
            raise ValueError("Canary deployments must have traffic_percentage > 0")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "model-123",
                "deployment_name": "fraud-detector-prod",
                "environment": "production",
                "strategy": "canary",
                "replicas": 3,
                "resource_config": {
                    "cpu": "2000m",
                    "memory": "4Gi",
                    "gpu": 0
                },
                "traffic_percentage": 10,
                "deployed_by": "ops-team"
            }
        }


class DeploymentResponse(BaseModel):
    """Schema for deployment response."""

    deployment_id: str
    model_id: str
    deployment_name: str
    environment: str
    strategy: str
    status: str
    health_status: str
    replicas: int
    resource_config: Dict[str, Any] = Field(default_factory=dict)
    traffic_percentage: int
    request_count: Optional[int] = None
    error_count: Optional[int] = None
    avg_latency_ms: Optional[int] = None
    deployed_by: Optional[str] = None
    deployed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_health_check: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_deployment(cls, deployment):
        """Create response from database model."""
        return cls(
            deployment_id=deployment.deployment_id,
            model_id=deployment.model_id,
            deployment_name=deployment.deployment_name,
            environment=deployment.environment,
            strategy=deployment.strategy,
            status=deployment.status,
            health_status=deployment.health_status,
            replicas=deployment.replicas,
            resource_config=deployment.resource_config or {},
            traffic_percentage=deployment.traffic_percentage,
            request_count=deployment.request_count,
            error_count=deployment.error_count,
            avg_latency_ms=deployment.avg_latency_ms,
            deployed_by=deployment.deployed_by,
            deployed_at=deployment.deployed_at,
            created_at=deployment.created_at,
            updated_at=deployment.updated_at,
            last_health_check=deployment.last_health_check
        )


class DeploymentUpdate(BaseModel):
    """Schema for updating deployment."""

    replicas: Optional[int] = Field(None, ge=1, le=100)
    resource_config: Optional[Dict[str, Any]] = None


class CanaryTrafficUpdate(BaseModel):
    """Schema for updating canary traffic percentage."""

    traffic_percentage: int = Field(..., ge=0, le=100, description="New traffic percentage")

    class Config:
        json_schema_extra = {
            "example": {
                "traffic_percentage": 50
            }
        }


class DeploymentStatsResponse(BaseModel):
    """Schema for deployment statistics response."""

    deployment_id: str
    deployment_name: str
    status: str
    health_status: str
    request_count: int
    error_count: int
    error_rate_percentage: float
    avg_latency_ms: Optional[int]
    traffic_percentage: int
    replicas: int
    uptime_hours: Optional[float]


class DeploymentListResponse(BaseModel):
    """Schema for paginated deployment list response."""

    deployments: List[DeploymentResponse]
    total: int
    skip: int
    limit: int


class DeploymentRollbackResponse(BaseModel):
    """Schema for deployment rollback response."""

    deployment_id: str
    status: str
    message: str
    rolled_back_at: datetime
