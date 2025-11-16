"""Cost Optimization & FinOps Accelerator."""

from fastapi import FastAPI, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../shared-libraries/dataforge-common"))
from dataforge_common.security import get_current_user

app = FastAPI(title="Cost Optimization & FinOps")


class CostSummary(BaseModel):
    """Cost summary."""
    total_cost: float
    period: str
    by_service: Dict[str, float]
    by_region: Dict[str, float]
    trend: str


class OptimizationRecommendation(BaseModel):
    """Cost optimization recommendation."""
    recommendation_id: str
    title: str
    description: str
    estimated_savings: float
    priority: str
    actions: List[str]


@app.get("/api/v1/costs/summary")
async def get_cost_summary(
    period: str = "month",
    cloud_provider: Optional[str] = None,
    current_user=Depends(get_current_user)
) -> CostSummary:
    """Get cost summary."""
    return CostSummary(
        total_cost=145230.50,
        period=period,
        by_service={"compute": 65000, "storage": 35000, "networking": 25000, "data_warehouse": 20230.50},
        by_region={"us-east-1": 80000, "us-west-2": 40000, "eu-west-1": 25230.50},
        trend="increasing"
    )


@app.get("/api/v1/recommendations", response_model=List[OptimizationRecommendation])
async def get_recommendations(current_user=Depends(get_current_user)):
    """Get cost optimization recommendations."""
    return [
        OptimizationRecommendation(
            recommendation_id="rec_001",
            title="Switch idle EC2 instances to Spot",
            description="5 EC2 instances have <10% utilization",
            estimated_savings=2500.0,
            priority="high",
            actions=["Identify workloads suitable for Spot", "Migrate to Spot instances"]
        ),
        OptimizationRecommendation(
            recommendation_id="rec_002",
            title="Optimize BigQuery partition strategy",
            description="Query costs can be reduced by 40% with proper partitioning",
            estimated_savings=8000.0,
            priority="high",
            actions=["Analyze query patterns", "Implement date partitioning", "Add clustering"]
        )
    ]


@app.post("/api/v1/budgets/create")
async def create_budget(
    name: str,
    amount: float,
    period: str,
    current_user=Depends(get_current_user)
):
    """Create cost budget with alerts."""
    return {
        "budget_id": "budget_001",
        "name": name,
        "amount": amount,
        "period": period,
        "alerts": [{"threshold": 80, "enabled": True}, {"threshold": 100, "enabled": True}]
    }
