"""FastAPI REST API for Data Observability."""

from fastapi import FastAPI, File, UploadFile, Request, Depends
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__, Request, Depends).parent.parent))

from monitoring.quality_monitor import QualityMonitor

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


app = FastAPI(title="DataForge Data Observability", version="0.1.0", description="DataForge AI Accelerator")
# Include authentication router if available
if AUTH_ENABLED:
    auth_router = create_auth_router()
    app.include_router(auth_router)

monitor = QualityMonitor()


class FreshnessCheck(BaseModel):
    """Freshness check request."""
    table: str
    last_update: str
    max_age_hours: float = 24.0


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/monitor/freshness")
async def check_freshness(check: FreshnessCheck):
    """Check data freshness."""
    last_update = datetime.fromisoformat(check.last_update)

    metric = monitor.check_freshness(
        table=check.table,
        last_update=last_update,
        max_age_hours=check.max_age_hours,
    )

    return {
        "table": metric.table,
        "metric": metric.metric_name,
        "value": metric.value,
        "threshold": metric.threshold,
        "passed": metric.passed,
    }


@app.post("/monitor/completeness")
async def check_completeness(
    file: UploadFile = File(...),
    table: str = "table",
    min_completeness: float = 0.95,
):
    """Check data completeness."""
    df = pd.read_csv(file.file)

    metric = monitor.check_completeness(
        table=table,
        df=df,
        min_completeness=min_completeness,
    )

    return {
        "table": metric.table,
        "metric": metric.metric_name,
        "value": metric.value,
        "threshold": metric.threshold,
        "passed": metric.passed,
    }


@app.get("/metrics")
async def get_metrics(table: Optional[str] = None, limit: int = 100):
    """Get quality metrics."""
    metrics = monitor.get_metrics(table=table, limit=limit)

    return {
        "count": len(metrics),
        "metrics": [
            {
                "timestamp": m.timestamp.isoformat(),
                "table": m.table,
                "metric": m.metric_name,
                "value": m.value,
                "passed": m.passed,
            }
            for m in metrics
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8014)
