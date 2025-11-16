"""FastAPI REST API for Data Governance."""

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pii.detector import PIIDetector
from classification.classifier import DataClassifier
from compliance.checker import ComplianceChecker
from audit.trail import AuditTrail

app = FastAPI(title="DataForge Data Governance", version="0.1.0")

pii_detector = PIIDetector()
data_classifier = DataClassifier()
compliance_checker = ComplianceChecker()
audit_trail = AuditTrail()


class ComplianceCheckRequest(BaseModel):
    """Compliance check request."""
    has_consent: bool = False
    retention_days: Optional[int] = None
    data_age_days: Optional[int] = None


@app.get("/health")
async def health_check():
    """Health check."""
    return {"status": "healthy"}


@app.post("/pii/scan")
async def scan_pii(file: UploadFile = File(...)):
    """Scan file for PII."""
    try:
        df = pd.read_csv(file.file)
        report = pii_detector.scan_dataframe(df)

        return {
            "total_rows": report.total_rows,
            "total_columns": report.total_columns,
            "pii_columns": report.pii_columns,
            "summary": report.summary,
            "matches_sample": [
                {
                    "type": m.pii_type.value,
                    "column": m.column,
                    "row": m.row_index,
                }
                for m in report.matches[:10]
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/pii/mask")
async def mask_pii(
    file: UploadFile = File(...),
    strategy: str = "redact",
):
    """Mask PII in file."""
    try:
        df = pd.read_csv(file.file)
        masked_df = pii_detector.mask_dataframe(df, strategy=strategy)

        return {
            "message": "PII masked successfully",
            "rows": len(masked_df),
            "columns": len(masked_df.columns),
            "strategy": strategy,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/classify")
async def classify_data(file: UploadFile = File(...)):
    """Classify data by sensitivity."""
    try:
        df = pd.read_csv(file.file)
        classifications = data_classifier.classify_dataframe(df)

        return {
            "classifications": {
                col: classification.value
                for col, classification in classifications.items()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/compliance/check")
async def check_compliance(
    file: UploadFile = File(...),
    has_consent: bool = False,
    retention_days: Optional[int] = None,
    data_age_days: Optional[int] = None,
):
    """Check GDPR compliance."""
    try:
        df = pd.read_csv(file.file)

        report = compliance_checker.check_gdpr(
            df=df,
            has_consent=has_consent,
            retention_days=retention_days,
            data_age_days=data_age_days,
        )

        return {
            "compliant": report.compliant,
            "checks_performed": report.checks_performed,
            "passed_checks": report.passed_checks,
            "violations": [
                {
                    "rule": v.rule,
                    "severity": v.severity,
                    "description": v.description,
                    "affected_data": v.affected_data,
                    "remediation": v.remediation,
                }
                for v in report.violations
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/audit/log")
async def log_audit(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    ip_address: Optional[str] = None,
):
    """Log audit event."""
    event = audit_trail.log_access(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
    )

    return {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
    }


@app.get("/audit/events")
async def get_audit_events(
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
):
    """Get audit events."""
    events = audit_trail.get_events(
        user_id=user_id,
        resource_id=resource_id,
    )

    return {
        "total_events": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "user_id": e.user_id,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
            }
            for e in events[-100:]  # Last 100 events
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
