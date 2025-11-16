"""Data Mesh Enablement Accelerator."""

from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../shared-libraries/dataforge-common"))
from dataforge_common.security import require_roles

app = FastAPI(title="Data Mesh Enablement")


class DomainStatus(str, Enum):
    """Domain status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROVISIONING = "provisioning"


class ProductStatus(str, Enum):
    """Data product status."""
    DRAFT = "draft"
    PREVIEW = "preview"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


class AccessRequestStatus(str, Enum):
    """Access request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


class CloudProvider(str, Enum):
    """Cloud providers."""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


# ==============================================
# Domain Models
# ==============================================

class DomainCreate(BaseModel):
    """Create domain request."""
    name: str = Field(..., description="Domain name (e.g., sales, marketing)")
    owner_email: str
    description: str
    business_unit: Optional[str] = None
    tags: List[str] = []


class Domain(BaseModel):
    """Domain response."""
    domain_id: str
    name: str
    owner_email: str
    description: str
    business_unit: Optional[str]
    status: DomainStatus
    data_products_count: int
    created_at: datetime
    tags: List[str]


class DataProductSLA(BaseModel):
    """SLA definition for data product."""
    freshness_hours: int = Field(..., description="Max age of data in hours")
    quality_score_min: int = Field(..., ge=0, le=100, description="Minimum quality score")
    uptime_percent: float = Field(default=99.9, ge=0, le=100)
    support_response_hours: int = 24


class DataProductSchema(BaseModel):
    """Data product schema definition."""
    fields: List[Dict]
    partitions: Optional[List[str]] = []
    format: str = "parquet"


class DataProductCreate(BaseModel):
    """Create data product request."""
    name: str
    domain_id: str
    description: str
    schema: DataProductSchema
    sla: DataProductSLA
    tags: List[str] = []
    documentation_url: Optional[str] = None
    sample_queries: Optional[List[str]] = []


class DataProduct(BaseModel):
    """Data product response."""
    product_id: str
    name: str
    domain_id: str
    description: str
    owner_email: str
    status: ProductStatus
    version: str
    schema: DataProductSchema
    sla: DataProductSLA
    quality_score: int
    consumer_count: int
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    storage_location: str


class WorkspaceProvisionRequest(BaseModel):
    """Workspace provisioning request."""
    domain_id: str
    template: str = "standard"  # standard, advanced, ml_enabled
    cloud_provider: CloudProvider
    region: str
    storage_size_gb: int = 1000
    compute_units: int = 4


class GovernancePolicy(BaseModel):
    """Governance policy definition."""
    policy_name: str
    policy_type: str  # access_control, data_quality, retention, pii_masking
    description: str
    rules: Dict
    applies_to_domains: List[str] = []  # Empty = all domains
    enabled: bool = True


class AccessRequest(BaseModel):
    """Data product access request."""
    product_id: str
    requester_email: str
    purpose: str
    duration_days: Optional[int] = None
    access_level: str = "read"  # read, write


class MarketplaceReview(BaseModel):
    """Data product review."""
    product_id: str
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None
    reviewer_email: str


class QualityMetrics(BaseModel):
    """Data quality metrics."""
    completeness: float = Field(..., ge=0, le=100)
    accuracy: float = Field(..., ge=0, le=100)
    timeliness: float = Field(..., ge=0, le=100)
    consistency: float = Field(..., ge=0, le=100)
    overall_score: float = Field(..., ge=0, le=100)


# ==============================================
# Domain Management Endpoints
# ==============================================

@app.post("/api/v1/domains", response_model=Domain)
async def create_domain(
    request: DomainCreate,
    current_user=Depends(require_roles(["admin", "domain_architect"]))
):
    """Register new domain in data mesh."""
    return Domain(
        domain_id=f"domain_{request.name}",
        name=request.name,
        owner_email=request.owner_email,
        description=request.description,
        business_unit=request.business_unit,
        status=DomainStatus.ACTIVE,
        data_products_count=0,
        created_at=datetime.utcnow(),
        tags=request.tags
    )


@app.get("/api/v1/domains", response_model=List[Domain])
async def list_domains(
    status: Optional[DomainStatus] = None,
    current_user=Depends(require_roles(["user"]))
):
    """List all domains in data mesh."""
    # Simulate domain listing
    return [
        Domain(
            domain_id="domain_sales",
            name="sales",
            owner_email="sales-lead@company.com",
            description="Sales transactions and pipeline data",
            business_unit="Revenue",
            status=DomainStatus.ACTIVE,
            data_products_count=12,
            created_at=datetime.utcnow(),
            tags=["revenue", "crm"]
        ),
        Domain(
            domain_id="domain_marketing",
            name="marketing",
            owner_email="marketing-lead@company.com",
            description="Campaign and customer engagement data",
            business_unit="Growth",
            status=DomainStatus.ACTIVE,
            data_products_count=8,
            created_at=datetime.utcnow(),
            tags=["growth", "analytics"]
        )
    ]


@app.get("/api/v1/domains/{domain_id}", response_model=Domain)
async def get_domain(
    domain_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Get domain details."""
    return Domain(
        domain_id=domain_id,
        name=domain_id.replace("domain_", ""),
        owner_email="owner@company.com",
        description="Domain description",
        business_unit="Business Unit",
        status=DomainStatus.ACTIVE,
        data_products_count=10,
        created_at=datetime.utcnow(),
        tags=[]
    )


@app.put("/api/v1/domains/{domain_id}")
async def update_domain(
    domain_id: str,
    owner_email: Optional[str] = None,
    description: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "domain_owner"]))
):
    """Update domain metadata."""
    return {
        "domain_id": domain_id,
        "updated_fields": ["owner_email", "description"] if owner_email and description else [],
        "updated_at": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/domains/{domain_id}/owners")
async def get_domain_owners(
    domain_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Get domain ownership information."""
    return {
        "domain_id": domain_id,
        "primary_owner": "owner@company.com",
        "technical_leads": ["tech1@company.com", "tech2@company.com"],
        "data_stewards": ["steward@company.com"],
        "on_call_rotation": ["oncall1@company.com", "oncall2@company.com"]
    }


# ==============================================
# Data Product Lifecycle Endpoints
# ==============================================

@app.post("/api/v1/data-products", response_model=DataProduct)
async def create_data_product(
    request: DataProductCreate,
    current_user=Depends(require_roles(["domain_owner", "data_engineer"]))
):
    """Create new data product."""
    return DataProduct(
        product_id=f"dp_{request.domain_id}_{request.name}",
        name=request.name,
        domain_id=request.domain_id,
        description=request.description,
        owner_email="owner@company.com",
        status=ProductStatus.DRAFT,
        version="0.1.0",
        schema=request.schema,
        sla=request.sla,
        quality_score=0,
        consumer_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        tags=request.tags,
        storage_location=f"s3://data-mesh/{request.domain_id}/{request.name}/"
    )


@app.get("/api/v1/data-products", response_model=List[DataProduct])
async def list_data_products(
    domain_id: Optional[str] = None,
    status: Optional[ProductStatus] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    min_quality_score: Optional[int] = None,
    current_user=Depends(require_roles(["user"]))
):
    """List/search data products."""
    # Simulate product listing
    products = [
        DataProduct(
            product_id="dp_sales_transactions",
            name="sales_transactions",
            domain_id="domain_sales",
            description="Daily sales transactions with customer information",
            owner_email="sales-eng@company.com",
            status=ProductStatus.PRODUCTION,
            version="2.1.0",
            schema=DataProductSchema(
                fields=[{"name": "transaction_id", "type": "string"}, {"name": "amount", "type": "decimal"}],
                partitions=["date"],
                format="parquet"
            ),
            sla=DataProductSLA(freshness_hours=4, quality_score_min=95),
            quality_score=97,
            consumer_count=15,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=["sales", "revenue", "pii"],
            storage_location="s3://data-mesh/sales/transactions/"
        ),
        DataProduct(
            product_id="dp_marketing_campaigns",
            name="marketing_campaigns",
            domain_id="domain_marketing",
            description="Campaign performance and attribution data",
            owner_email="marketing-eng@company.com",
            status=ProductStatus.PRODUCTION,
            version="1.5.0",
            schema=DataProductSchema(
                fields=[{"name": "campaign_id", "type": "string"}, {"name": "spend", "type": "decimal"}],
                format="parquet"
            ),
            sla=DataProductSLA(freshness_hours=24, quality_score_min=90),
            quality_score=93,
            consumer_count=8,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=["marketing", "campaigns"],
            storage_location="s3://data-mesh/marketing/campaigns/"
        )
    ]

    # Apply filters
    if domain_id:
        products = [p for p in products if p.domain_id == domain_id]
    if status:
        products = [p for p in products if p.status == status]
    if min_quality_score:
        products = [p for p in products if p.quality_score >= min_quality_score]

    return products


@app.get("/api/v1/data-products/{product_id}", response_model=DataProduct)
async def get_data_product(
    product_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Get data product details."""
    return DataProduct(
        product_id=product_id,
        name="sales_transactions",
        domain_id="domain_sales",
        description="Daily sales transactions",
        owner_email="sales-eng@company.com",
        status=ProductStatus.PRODUCTION,
        version="2.1.0",
        schema=DataProductSchema(
            fields=[{"name": "id", "type": "string"}],
            format="parquet"
        ),
        sla=DataProductSLA(freshness_hours=4, quality_score_min=95),
        quality_score=97,
        consumer_count=15,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        tags=["sales"],
        storage_location=f"s3://data-mesh/products/{product_id}/"
    )


@app.put("/api/v1/data-products/{product_id}")
async def update_data_product(
    product_id: str,
    description: Optional[str] = None,
    sla: Optional[DataProductSLA] = None,
    current_user=Depends(require_roles(["domain_owner", "data_engineer"]))
):
    """Update data product metadata."""
    return {
        "product_id": product_id,
        "updated_at": datetime.utcnow().isoformat(),
        "version": "2.1.1",
        "changes": ["description", "sla"] if description and sla else []
    }


@app.post("/api/v1/data-products/{product_id}/publish")
async def publish_data_product(
    product_id: str,
    current_user=Depends(require_roles(["domain_owner"]))
):
    """Publish data product to marketplace."""
    return {
        "product_id": product_id,
        "status": "production",
        "published_at": datetime.utcnow().isoformat(),
        "marketplace_url": f"https://data-mesh.company.com/marketplace/products/{product_id}",
        "version": "1.0.0"
    }


@app.post("/api/v1/data-products/{product_id}/versions")
async def create_product_version(
    product_id: str,
    version: str,
    changelog: str,
    breaking_changes: bool = False,
    current_user=Depends(require_roles(["domain_owner", "data_engineer"]))
):
    """Create new version of data product."""
    return {
        "product_id": product_id,
        "version": version,
        "changelog": changelog,
        "breaking_changes": breaking_changes,
        "created_at": datetime.utcnow().isoformat(),
        "backward_compatible": not breaking_changes
    }


@app.delete("/api/v1/data-products/{product_id}")
async def deprecate_data_product(
    product_id: str,
    deprecation_reason: str,
    sunset_date: str,
    current_user=Depends(require_roles(["domain_owner", "admin"]))
):
    """Deprecate data product."""
    return {
        "product_id": product_id,
        "status": "deprecated",
        "deprecation_reason": deprecation_reason,
        "sunset_date": sunset_date,
        "active_consumers_notified": True,
        "consumer_count": 15
    }


# ==============================================
# Self-Serve Infrastructure Endpoints
# ==============================================

@app.post("/api/v1/provision/workspace")
async def provision_workspace(
    request: WorkspaceProvisionRequest,
    current_user=Depends(require_roles(["admin", "domain_owner"]))
):
    """Provision domain workspace with infrastructure."""
    return {
        "workspace_id": f"ws_{request.domain_id}",
        "domain_id": request.domain_id,
        "status": "provisioning",
        "cloud_provider": request.cloud_provider.value,
        "region": request.region,
        "resources": {
            "storage": f"s3://data-mesh-{request.domain_id}/" if request.cloud_provider == CloudProvider.AWS else f"gs://data-mesh-{request.domain_id}/",
            "compute": f"{request.compute_units} compute units",
            "orchestration": "Managed Airflow",
            "monitoring": "Grafana dashboard provisioned"
        },
        "estimated_completion_minutes": 15,
        "terraform_apply_url": f"https://terraform.company.com/runs/ws_{request.domain_id}"
    }


@app.get("/api/v1/provision/templates")
async def list_infrastructure_templates(
    current_user=Depends(require_roles(["user"]))
):
    """List available infrastructure templates."""
    return {
        "templates": [
            {
                "name": "standard",
                "description": "Standard data product infrastructure",
                "includes": ["S3/ADLS storage", "Spark cluster", "Airflow", "Monitoring"],
                "estimated_cost_monthly": 5000
            },
            {
                "name": "advanced",
                "description": "Advanced with real-time streaming",
                "includes": ["Standard +", "Kafka", "Flink", "Redis cache"],
                "estimated_cost_monthly": 12000
            },
            {
                "name": "ml_enabled",
                "description": "ML-enabled data products",
                "includes": ["Advanced +", "GPU compute", "MLflow", "Feature store"],
                "estimated_cost_monthly": 20000
            }
        ]
    }


@app.post("/api/v1/provision/scale")
async def scale_workspace(
    workspace_id: str,
    compute_units: int,
    storage_size_gb: int,
    current_user=Depends(require_roles(["domain_owner", "admin"]))
):
    """Scale domain workspace resources."""
    return {
        "workspace_id": workspace_id,
        "scaling_operation": "in_progress",
        "current_compute_units": 4,
        "target_compute_units": compute_units,
        "current_storage_gb": 1000,
        "target_storage_gb": storage_size_gb,
        "estimated_completion_minutes": 5
    }


@app.get("/api/v1/provision/status/{workspace_id}")
async def get_provisioning_status(
    workspace_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Get workspace provisioning status."""
    return {
        "workspace_id": workspace_id,
        "status": "active",
        "provisioned_at": "2025-01-16T10:30:00Z",
        "resources": {
            "storage": "s3://data-mesh-sales/",
            "compute": "4 units (16 vCPUs, 64GB RAM)",
            "orchestration": "airflow-sales.company.com",
            "monitoring": "grafana.company.com/d/sales"
        },
        "health": "healthy",
        "uptime_percent": 99.95
    }


# ==============================================
# Governance & Policies Endpoints
# ==============================================

@app.post("/api/v1/policies")
async def create_policy(
    policy: GovernancePolicy,
    current_user=Depends(require_roles(["admin", "compliance_officer"]))
):
    """Create governance policy."""
    return {
        "policy_id": f"policy_{policy.policy_name}",
        "policy_name": policy.policy_name,
        "policy_type": policy.policy_type,
        "enabled": policy.enabled,
        "created_at": datetime.utcnow().isoformat(),
        "applies_to_domains": policy.applies_to_domains if policy.applies_to_domains else "all"
    }


@app.get("/api/v1/policies")
async def list_policies(
    policy_type: Optional[str] = None,
    current_user=Depends(require_roles(["user"]))
):
    """List governance policies."""
    policies = [
        {
            "policy_id": "policy_pii_masking",
            "policy_name": "PII Automatic Masking",
            "policy_type": "pii_masking",
            "description": "Automatically mask PII fields in all data products",
            "enabled": True,
            "applies_to_domains": []
        },
        {
            "policy_id": "policy_retention_90d",
            "policy_name": "90-Day Data Retention",
            "policy_type": "retention",
            "description": "Delete data older than 90 days",
            "enabled": True,
            "applies_to_domains": ["marketing", "sales"]
        }
    ]

    if policy_type:
        policies = [p for p in policies if p["policy_type"] == policy_type]

    return {"policies": policies}


@app.post("/api/v1/policies/{policy_id}/enforce")
async def enforce_policy(
    policy_id: str,
    product_ids: List[str],
    current_user=Depends(require_roles(["admin"]))
):
    """Apply policy to data products."""
    return {
        "policy_id": policy_id,
        "products_affected": len(product_ids),
        "enforcement_status": "applied",
        "applied_at": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/compliance/violations")
async def get_policy_violations(
    severity: Optional[str] = Query(None, description="critical, high, medium, low"),
    current_user=Depends(require_roles(["admin", "compliance_officer"]))
):
    """Get policy violations."""
    return {
        "violations": [
            {
                "violation_id": "viol_001",
                "policy_id": "policy_pii_masking",
                "product_id": "dp_sales_customers",
                "severity": "high",
                "description": "SSN field not masked",
                "detected_at": "2025-01-16T09:15:00Z",
                "status": "open"
            }
        ],
        "total_violations": 1,
        "critical_count": 0,
        "high_count": 1
    }


@app.get("/api/v1/compliance/report")
async def generate_compliance_report(
    domain_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "compliance_officer"]))
):
    """Generate compliance report."""
    return {
        "report_id": "compliance_report_001",
        "domain_id": domain_id or "all",
        "period": f"{start_date} to {end_date}",
        "total_policies": 25,
        "policies_enforced": 25,
        "compliance_rate": 98.5,
        "violations": 12,
        "violations_resolved": 10,
        "generated_at": datetime.utcnow().isoformat(),
        "download_url": "https://reports.company.com/compliance_001.pdf"
    }


# ==============================================
# Marketplace Endpoints
# ==============================================

@app.get("/api/v1/marketplace/search")
async def search_marketplace(
    query: Optional[str] = None,
    domain_id: Optional[str] = None,
    tags: Optional[str] = None,
    min_quality_score: int = 0,
    current_user=Depends(require_roles(["user"]))
):
    """Search data products in marketplace."""
    # Reuse list_data_products logic
    products = await list_data_products(
        domain_id=domain_id,
        tags=tags,
        min_quality_score=min_quality_score,
        current_user=current_user
    )

    return {
        "query": query,
        "results_count": len(products),
        "products": products
    }


@app.post("/api/v1/marketplace/access-request")
async def request_product_access(
    request: AccessRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Request access to data product."""
    # Simulate auto-approval logic
    auto_approve = request.access_level == "read" and request.purpose

    return {
        "request_id": "access_req_001",
        "product_id": request.product_id,
        "requester_email": request.requester_email,
        "status": AccessRequestStatus.AUTO_APPROVED if auto_approve else AccessRequestStatus.PENDING,
        "access_level": request.access_level,
        "duration_days": request.duration_days,
        "approved_at": datetime.utcnow().isoformat() if auto_approve else None,
        "message": "Auto-approved based on governance policies" if auto_approve else "Pending domain owner review"
    }


@app.get("/api/v1/marketplace/subscriptions")
async def get_my_subscriptions(
    current_user=Depends(require_roles(["user"]))
):
    """Get current user's data product subscriptions."""
    return {
        "subscriptions": [
            {
                "product_id": "dp_sales_transactions",
                "product_name": "sales_transactions",
                "access_level": "read",
                "subscribed_at": "2025-01-10T10:00:00Z",
                "expires_at": "2025-04-10T10:00:00Z",
                "status": "active"
            },
            {
                "product_id": "dp_marketing_campaigns",
                "product_name": "marketing_campaigns",
                "access_level": "read",
                "subscribed_at": "2025-01-05T14:30:00Z",
                "expires_at": None,
                "status": "active"
            }
        ],
        "total_subscriptions": 2
    }


@app.post("/api/v1/marketplace/review")
async def review_product(
    review: MarketplaceReview,
    current_user=Depends(require_roles(["user"]))
):
    """Rate and review data product."""
    return {
        "review_id": "review_001",
        "product_id": review.product_id,
        "rating": review.rating,
        "reviewer_email": review.reviewer_email,
        "created_at": datetime.utcnow().isoformat(),
        "verified_consumer": True
    }


@app.get("/api/v1/marketplace/analytics/{product_id}")
async def get_product_analytics(
    product_id: str,
    current_user=Depends(require_roles(["domain_owner"]))
):
    """Get data product usage analytics."""
    return {
        "product_id": product_id,
        "metrics": {
            "total_consumers": 15,
            "active_consumers_30d": 12,
            "total_queries_30d": 45000,
            "avg_queries_per_day": 1500,
            "data_volume_read_tb": 12.5,
            "avg_query_latency_ms": 850
        },
        "top_consumers": [
            {"email": "analyst1@company.com", "queries_30d": 5000},
            {"email": "analyst2@company.com", "queries_30d": 3500}
        ],
        "popular_queries": [
            "SELECT * FROM sales_transactions WHERE date = CURRENT_DATE",
            "SELECT customer_id, SUM(amount) FROM sales_transactions GROUP BY customer_id"
        ]
    }


# ==============================================
# Lineage & Impact Analysis Endpoints
# ==============================================

@app.get("/api/v1/lineage/{product_id}")
async def get_product_lineage(
    product_id: str,
    depth: int = Query(3, description="Lineage depth"),
    current_user=Depends(require_roles(["user"]))
):
    """Get data product lineage."""
    return {
        "product_id": product_id,
        "lineage": {
            "upstream": [
                {"source": "postgres://sales_db/transactions", "type": "database"},
                {"source": "s3://raw-data/sales/", "type": "s3"}
            ],
            "downstream": [
                {"consumer": "dp_finance_revenue", "type": "data_product"},
                {"consumer": "tableau://sales-dashboard", "type": "bi_tool"},
                {"consumer": "ml_model://churn_prediction_v2", "type": "ml_model"}
            ]
        },
        "depth": depth,
        "total_upstream": 2,
        "total_downstream": 3
    }


@app.post("/api/v1/lineage/impact-analysis")
async def analyze_change_impact(
    product_id: str,
    change_type: str = Query(..., description="schema_change, deprecation, sla_change"),
    change_details: Dict = {},
    current_user=Depends(require_roles(["domain_owner"]))
):
    """Analyze impact of changes to data product."""
    return {
        "product_id": product_id,
        "change_type": change_type,
        "impact_summary": {
            "affected_products": 3,
            "affected_dashboards": 5,
            "affected_ml_models": 1,
            "total_consumers_impacted": 15
        },
        "breaking_changes": change_type == "schema_change",
        "affected_entities": [
            {"entity_id": "dp_finance_revenue", "entity_type": "data_product", "impact": "high"},
            {"entity_id": "sales_dashboard_v2", "entity_type": "dashboard", "impact": "medium"}
        ],
        "recommendations": [
            "Notify all downstream consumers 2 weeks in advance",
            "Provide migration guide for schema changes",
            "Maintain backward compatibility for 1 version cycle"
        ]
    }


@app.get("/api/v1/lineage/dependencies/{product_id}")
async def get_product_dependencies(
    product_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Get data product dependencies."""
    return {
        "product_id": product_id,
        "direct_dependencies": [
            {"product_id": "dp_sales_customers", "relationship": "join"},
            {"product_id": "dp_sales_products", "relationship": "lookup"}
        ],
        "transitive_dependencies": [
            {"product_id": "dp_crm_contacts", "depth": 2}
        ],
        "dependency_health": {
            "all_dependencies_healthy": True,
            "unhealthy_dependencies": []
        }
    }


@app.post("/api/v1/lineage/trace")
async def trace_data_flow(
    entity_id: str,
    entity_type: str = Query(..., description="record_id, customer_id, etc."),
    current_user=Depends(require_roles(["user"]))
):
    """Trace specific data entity across products."""
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "trace": [
            {
                "step": 1,
                "product": "source_system",
                "timestamp": "2025-01-16T08:00:00Z",
                "operation": "ingested"
            },
            {
                "step": 2,
                "product": "dp_sales_transactions",
                "timestamp": "2025-01-16T09:00:00Z",
                "operation": "transformed"
            },
            {
                "step": 3,
                "product": "dp_finance_revenue",
                "timestamp": "2025-01-16T10:00:00Z",
                "operation": "aggregated"
            }
        ]
    }


# ==============================================
# Quality & SLA Endpoints
# ==============================================

@app.get("/api/v1/quality/metrics/{product_id}", response_model=QualityMetrics)
async def get_quality_metrics(
    product_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Get data product quality metrics."""
    return QualityMetrics(
        completeness=98.5,
        accuracy=96.2,
        timeliness=99.1,
        consistency=97.8,
        overall_score=97.9
    )


@app.post("/api/v1/quality/test")
async def run_quality_tests(
    product_id: str,
    test_suite: str = "full",  # full, smoke, custom
    current_user=Depends(require_roles(["domain_owner", "data_engineer"]))
):
    """Run quality tests on data product."""
    return {
        "test_run_id": "test_run_001",
        "product_id": product_id,
        "test_suite": test_suite,
        "status": "running",
        "tests_total": 25,
        "tests_passed": 0,
        "tests_failed": 0,
        "started_at": datetime.utcnow().isoformat(),
        "estimated_duration_minutes": 5
    }


@app.get("/api/v1/sla/status/{product_id}")
async def get_sla_status(
    product_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Check SLA compliance for data product."""
    return {
        "product_id": product_id,
        "sla_compliance": {
            "freshness": {"status": "compliant", "current_hours": 2, "sla_hours": 4},
            "quality_score": {"status": "compliant", "current_score": 97, "sla_min": 95},
            "uptime": {"status": "compliant", "current_percent": 99.95, "sla_percent": 99.9}
        },
        "overall_compliance": True,
        "last_violation": None
    }


@app.post("/api/v1/sla/incident")
async def report_sla_incident(
    product_id: str,
    incident_type: str,
    description: str,
    current_user=Depends(require_roles(["user"]))
):
    """Report SLA violation incident."""
    return {
        "incident_id": "incident_001",
        "product_id": product_id,
        "incident_type": incident_type,
        "severity": "high",
        "reported_by": current_user,
        "reported_at": datetime.utcnow().isoformat(),
        "ticket_created": "JIRA-12345",
        "owner_notified": True
    }
