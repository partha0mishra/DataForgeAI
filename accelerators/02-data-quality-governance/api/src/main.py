"""FastAPI application for Data Quality & Governance."""

from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration
from dataforge_contracts import QualityReport

# Import governance modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.quality_checker import DataQualityChecker
from governance.pii_detection.detector import PIIDetector
from governance.audit_logger.logger import AuditLogger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DataForge Quality & Governance API",
    description="API for data quality validation and governance",
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
quality_checker = DataQualityChecker()
pii_detector = PIIDetector()
audit_logger = AuditLogger()


# Models
class QualityCheckRequest(BaseModel):
    """Quality check request."""

    dataset_name: str
    expectation_suite: str = "default"
    user: Optional[str] = "system"


class PIIDetectionRequest(BaseModel):
    """PII detection request."""

    dataset_name: str
    mask_pii: bool = False
    user: Optional[str] = "system"


class AuditQuery(BaseModel):
    """Audit log query."""

    event_type: Optional[str] = None
    user: Optional[str] = None
    dataset: Optional[str] = None
    limit: int = 100


# In-memory storage (replace with database in production)
quality_reports_db = {}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DataForge Quality & Governance API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    increment_counter("health_checks")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/quality/check", response_model=QualityReport)
@track_duration("quality_check_duration")
async def run_quality_check(
    file: UploadFile = File(...),
    user: str = "system",
    expectation_suite: str = "default",
):
    """
    Run quality checks on uploaded data.

    Upload a CSV file and get a quality report.
    """
    logger.info("Quality check requested", filename=file.filename, user=user)

    try:
        # Read uploaded file
        df = pd.read_csv(file.file)

        # Run quality checks
        report = quality_checker.validate_dataframe(
            df=df,
            expectation_suite_name=expectation_suite,
            batch_identifier=file.filename,
        )

        # Store report
        quality_reports_db[report.report_id] = report

        # Log audit event
        audit_logger.log_quality_check(
            dataset=file.filename,
            status=report.overall_status.value,
            metrics=report.metrics.model_dump(),
            suite=expectation_suite,
            metadata={"user": user},
        )

        increment_counter(
            "quality_checks_run",
            labels={"status": report.overall_status.value},
        )

        logger.info(
            "Quality check complete",
            report_id=report.report_id,
            status=report.overall_status.value,
        )

        return report

    except Exception as e:
        logger.error("Quality check failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quality/reports", response_model=List[QualityReport])
async def list_quality_reports():
    """List all quality reports."""
    return list(quality_reports_db.values())


@app.get("/quality/reports/{report_id}", response_model=QualityReport)
async def get_quality_report(report_id: str):
    """Get quality report by ID."""
    if report_id not in quality_reports_db:
        raise HTTPException(status_code=404, detail="Report not found")

    return quality_reports_db[report_id]


@app.post("/pii/detect")
@track_duration("pii_detection_duration")
async def detect_pii(
    file: UploadFile = File(...),
    user: str = "system",
    mask_pii: bool = False,
):
    """
    Detect PII in uploaded data.

    Upload a CSV file and get PII detection results.
    Optionally mask PII before returning.
    """
    logger.info("PII detection requested", filename=file.filename, user=user)

    try:
        # Read uploaded file
        df = pd.read_csv(file.file)

        # Detect PII
        pii_found = pii_detector.detect_in_dataframe(df)

        # Generate report
        report = pii_detector.generate_report(df)

        # Mask PII if requested
        if mask_pii and pii_found:
            df = pii_detector.mask_pii(df)
            action_taken = "masked"
        else:
            action_taken = "detected_only"

        # Log audit event
        audit_logger.log_pii_detection(
            dataset=file.filename,
            pii_found=pii_found,
            action_taken=action_taken,
            metadata={"user": user},
        )

        increment_counter(
            "pii_detections_run",
            labels={"pii_found": str(bool(pii_found))},
        )

        logger.info(
            "PII detection complete",
            columns_with_pii=len(pii_found),
            action=action_taken,
        )

        return {
            "pii_detected": pii_found,
            "report": report,
            "masked": mask_pii,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("PII detection failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/query")
async def query_audit_logs(query: AuditQuery):
    """
    Query audit logs.

    Filter by event type, user, or dataset.
    """
    logger.info("Audit query requested", filters=query.model_dump())

    try:
        results = audit_logger.query_logs(
            event_type=query.event_type,
            user=query.user,
            dataset=query.dataset,
        )

        # Limit results
        results = results[: query.limit]

        logger.info("Audit query complete", results=len(results))

        return {
            "count": len(results),
            "logs": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Audit query failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Get quality and governance metrics."""
    total_reports = len(quality_reports_db)
    passed_reports = sum(
        1
        for r in quality_reports_db.values()
        if r.overall_status.value == "passed"
    )

    return {
        "quality_checks": {
            "total": total_reports,
            "passed": passed_reports,
            "failed": total_reports - passed_reports,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
