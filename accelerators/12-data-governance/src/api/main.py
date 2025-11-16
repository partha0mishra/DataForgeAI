"""FastAPI REST API for Data Governance."""

from fastapi import FastAPI, File, HTTPException, UploadFile, Depends, Request
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

app = FastAPI(
    title="DataForge Data Governance",
    version="0.1.0",
    description="Enterprise data governance with PII detection, classification, and compliance",
)

# Include authentication router if available
if AUTH_ENABLED:
    auth_router = create_auth_router()
    app.include_router(auth_router)

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
async def scan_pii(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: Optional[User] = Depends(get_current_user) if AUTH_ENABLED else None,
):
    """Scan file for PII.

    Requires authentication. Logs access to audit trail.
    """
    try:
        df = pd.read_csv(file.file)
        report = pii_detector.scan_dataframe(df)

        # Log audit event
        if current_user:
            audit_trail.log_access(
                user_id=current_user.user_id,
                action="pii_scan",
                resource_type="file",
                resource_id=file.filename or "unknown",
                ip_address=request.client.host if request else None,
            )

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
    request: Request = None,
    current_user: Optional[User] = Depends(get_current_user) if AUTH_ENABLED else None,
):
    """Mask PII in file.

    Requires authentication. Logs access to audit trail.
    """
    try:
        df = pd.read_csv(file.file)
        masked_df = pii_detector.mask_dataframe(df, strategy=strategy)

        # Log audit event
        if current_user:
            audit_trail.log_access(
                user_id=current_user.user_id,
                action="pii_mask",
                resource_type="file",
                resource_id=file.filename or "unknown",
                ip_address=request.client.host if request else None,
            )

        return {
            "message": "PII masked successfully",
            "rows": len(masked_df),
            "columns": len(masked_df.columns),
            "strategy": strategy,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/classify")
async def classify_data(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: Optional[User] = Depends(get_current_user) if AUTH_ENABLED else None,
):
    """Classify data by sensitivity.

    Requires authentication. Logs access to audit trail.
    """
    try:
        df = pd.read_csv(file.file)
        classifications = data_classifier.classify_dataframe(df)

        # Log audit event
        if current_user:
            audit_trail.log_access(
                user_id=current_user.user_id,
                action="data_classify",
                resource_type="file",
                resource_id=file.filename or "unknown",
                ip_address=request.client.host if request else None,
            )

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
    request: Request = None,
    current_user: Optional[User] = Depends(get_current_user) if AUTH_ENABLED else None,
):
    """Check GDPR compliance.

    Requires authentication. Logs access to audit trail.
    """
    try:
        df = pd.read_csv(file.file)

        report = compliance_checker.check_gdpr(
            df=df,
            has_consent=has_consent,
            retention_days=retention_days,
            data_age_days=data_age_days,
        )

        # Log audit event
        if current_user:
            audit_trail.log_access(
                user_id=current_user.user_id,
                action="compliance_check",
                resource_type="file",
                resource_id=file.filename or "unknown",
                ip_address=request.client.host if request else None,
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
    action: str,
    resource_type: str,
    resource_id: str,
    request: Request = None,
    current_user: Optional[User] = Depends(get_current_user) if AUTH_ENABLED else None,
):
    """Log audit event.

    Requires authentication. User ID is taken from authenticated user.
    """
    if not current_user and AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_id = current_user.user_id if current_user else "anonymous"

    event = audit_trail.log_access(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=request.client.host if request else None,
    )

    return {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
    }


@app.get("/audit/events")
async def get_audit_events(
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    current_user: Optional[User] = Depends(require_roles(["admin"])) if AUTH_ENABLED else None,
):
    """Get audit events.

    Requires admin role.
    """
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
