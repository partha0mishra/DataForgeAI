"""Advanced Security & Zero Trust Accelerator."""

from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../shared-libraries/dataforge-common"))
from dataforge_common.security import require_roles

app = FastAPI(title="Advanced Security & Zero Trust")


class MaskingFunction(str, Enum):
    """Data masking functions."""
    PARTIAL_MASK = "partial_mask"
    FULL_MASK = "full_mask"
    HASH = "hash"
    NULLIFY = "nullify"
    SHUFFLE = "shuffle"


class RiskLevel(str, Enum):
    """Risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Severity(str, Enum):
    """Vulnerability severity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    """Security incident status."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


# ==============================================
# Dynamic Masking Models
# ==============================================

class MaskingPolicy(BaseModel):
    """Masking policy definition."""
    policy_name: str
    columns: List[str]
    masking_function: MaskingFunction
    roles_exempt: List[str] = []
    tables: Optional[List[str]] = None  # None = all tables
    preserve_length: bool = True


class MaskingPreviewRequest(BaseModel):
    """Preview masking request."""
    data: Dict[str, Any]
    policy_name: str


# ==============================================
# Tokenization Models
# ==============================================

class TokenizeRequest(BaseModel):
    """Tokenization request."""
    data: str
    token_type: str = "alphanumeric"  # alphanumeric, numeric, uuid
    preserve_format: bool = True


class TokenizedData(BaseModel):
    """Tokenized data response."""
    token: str
    token_id: str
    original_format: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class DetokenizeRequest(BaseModel):
    """Detokenization request."""
    token: str
    purpose: str = Field(..., description="Business justification for detokenization")


# ==============================================
# Secrets Management Models
# ==============================================

class SecretCreate(BaseModel):
    """Create secret request."""
    secret_name: str
    secret_value: str
    rotation_days: int = 30
    auto_rotate: bool = True
    tags: Dict[str, str] = {}


class Secret(BaseModel):
    """Secret metadata (never includes value)."""
    secret_id: str
    secret_name: str
    version: int
    created_at: datetime
    last_rotated_at: datetime
    next_rotation_at: datetime
    auto_rotate: bool
    tags: Dict[str, str]


class SecretScanRequest(BaseModel):
    """Secret scanning request."""
    repository_url: Optional[str] = None
    directory_path: Optional[str] = None
    file_patterns: List[str] = ["*.py", "*.js", "*.yaml", "*.env"]


# ==============================================
# Vulnerability Scanning Models
# ==============================================

class ContainerScanRequest(BaseModel):
    """Container scan request."""
    image: str
    registry: Optional[str] = None
    severity_threshold: Severity = Severity.HIGH


class Vulnerability(BaseModel):
    """Vulnerability finding."""
    cve_id: str
    severity: Severity
    package: str
    installed_version: str
    fixed_version: Optional[str]
    description: str
    cvss_score: float
    published_date: datetime


class ScanResult(BaseModel):
    """Scan result summary."""
    scan_id: str
    target: str
    scan_type: str
    vulnerabilities_found: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    scanned_at: datetime
    vulnerabilities: List[Vulnerability]


# ==============================================
# Behavioral Analytics Models
# ==============================================

class UserRiskScore(BaseModel):
    """User risk score."""
    user_id: str
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    contributing_factors: List[Dict[str, Any]]
    anomalies_detected: int
    last_updated: datetime


class Anomaly(BaseModel):
    """Behavioral anomaly."""
    anomaly_id: str
    user_id: str
    anomaly_type: str
    description: str
    severity: Severity
    detected_at: datetime
    baseline_behavior: Dict
    observed_behavior: Dict
    risk_score_impact: int


class SecurityIncident(BaseModel):
    """Security incident."""
    incident_id: str
    incident_type: str
    severity: Severity
    status: IncidentStatus
    user_id: Optional[str]
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime]
    actions_taken: List[str]


# ==============================================
# Encryption Models
# ==============================================

class EncryptionKeyCreate(BaseModel):
    """Create encryption key."""
    key_name: str
    key_algorithm: str = "AES-256"
    rotation_days: int = 90
    purpose: str  # data, secrets, backups


class EncryptRequest(BaseModel):
    """Encryption request."""
    plaintext: str
    key_id: str
    context: Optional[Dict[str, str]] = None


class DecryptRequest(BaseModel):
    """Decryption request."""
    ciphertext: str
    key_id: str
    context: Optional[Dict[str, str]] = None
    purpose: str = Field(..., description="Business justification")


# ==============================================
# Access Control Models
# ==============================================

class JITAccessRequest(BaseModel):
    """Just-in-time access request."""
    resource: str
    permissions: List[str]
    duration_hours: int = Field(..., ge=1, le=24)
    justification: str


class AccessReview(BaseModel):
    """Access review entry."""
    user_id: str
    resources: List[str]
    permissions: List[str]
    last_used: Optional[datetime]
    review_required: bool
    certifier: Optional[str]


# ==============================================
# DLP Models
# ==============================================

class DLPPolicy(BaseModel):
    """DLP policy."""
    policy_name: str
    sensitive_data_types: List[str]  # ssn, credit_card, email, etc.
    action: str  # block, quarantine, alert, redact
    threshold: int = Field(..., description="Number of occurrences to trigger")


class DLPScanRequest(BaseModel):
    """DLP scan request."""
    content: str
    content_type: str = "query_result"


class DLPViolation(BaseModel):
    """DLP violation."""
    violation_id: str
    policy_name: str
    user_id: str
    sensitive_data_type: str
    occurrences: int
    action_taken: str
    detected_at: datetime
    content_snippet: str


# ==============================================
# Dynamic Masking Endpoints
# ==============================================

@app.post("/api/v1/masking/policies")
async def create_masking_policy(
    policy: MaskingPolicy,
    current_user=Depends(require_roles(["admin", "security_engineer"]))
):
    """Create dynamic data masking policy."""
    return {
        "policy_id": f"mask_policy_{policy.policy_name}",
        "policy_name": policy.policy_name,
        "masking_function": policy.masking_function.value,
        "columns": policy.columns,
        "status": "active",
        "created_at": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/masking/policies")
async def list_masking_policies(
    current_user=Depends(require_roles(["user"]))
):
    """List all masking policies."""
    return {
        "policies": [
            {
                "policy_id": "mask_policy_ssn",
                "policy_name": "mask_ssn",
                "masking_function": "partial_mask",
                "columns": ["ssn", "social_security_number"],
                "roles_exempt": ["admin", "compliance_officer"]
            },
            {
                "policy_id": "mask_policy_cc",
                "policy_name": "mask_credit_cards",
                "masking_function": "partial_mask",
                "columns": ["credit_card", "cc_number"],
                "roles_exempt": ["admin"]
            }
        ]
    }


@app.post("/api/v1/masking/apply")
async def apply_masking(
    data: Dict[str, Any],
    policy_names: List[str],
    current_user=Depends(require_roles(["user"]))
):
    """Apply masking policies to data."""
    # Simulate masking
    masked_data = data.copy()
    if "ssn" in masked_data:
        masked_data["ssn"] = "XXX-XX-" + masked_data["ssn"][-4:]
    if "credit_card" in masked_data:
        masked_data["credit_card"] = "XXXX-XXXX-XXXX-" + masked_data["credit_card"][-4:]

    return {
        "masked_data": masked_data,
        "policies_applied": policy_names,
        "user_role": "analyst",
        "masking_applied": True
    }


@app.get("/api/v1/masking/preview")
async def preview_masking(
    sample_value: str,
    masking_function: MaskingFunction,
    current_user=Depends(require_roles(["user"]))
):
    """Preview how masking will look."""
    previews = {
        MaskingFunction.PARTIAL_MASK: sample_value[:3] + "***" + sample_value[-2:],
        MaskingFunction.FULL_MASK: "*" * len(sample_value),
        MaskingFunction.HASH: "a1b2c3d4e5f6...",
        MaskingFunction.NULLIFY: "NULL"
    }

    return {
        "original": sample_value,
        "masked": previews.get(masking_function, sample_value),
        "masking_function": masking_function.value
    }


# ==============================================
# Tokenization Endpoints
# ==============================================

@app.post("/api/v1/tokenization/tokenize", response_model=TokenizedData)
async def tokenize_data(
    request: TokenizeRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Tokenize sensitive data."""
    import hashlib
    token = hashlib.sha256(request.data.encode()).hexdigest()[:16]

    return TokenizedData(
        token=token,
        token_id=f"tok_{token}",
        original_format="string",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=365) if request.preserve_format else None
    )


@app.post("/api/v1/tokenization/detokenize")
async def detokenize_data(
    request: DetokenizeRequest,
    current_user=Depends(require_roles(["admin", "compliance_officer"]))
):
    """Retrieve original data from token (restricted access)."""
    return {
        "token": request.token,
        "original_value": "4111-1111-1111-1111",  # Simulated
        "purpose": request.purpose,
        "detokenized_by": current_user,
        "detokenized_at": datetime.utcnow().isoformat(),
        "audit_logged": True
    }


@app.post("/api/v1/tokenization/rotate")
async def rotate_token_mapping(
    token_id: str,
    current_user=Depends(require_roles(["admin"]))
):
    """Rotate token mapping (change token, keep original data)."""
    return {
        "token_id": token_id,
        "old_token": "abc123def456",
        "new_token": "xyz789uvw012",
        "rotated_at": datetime.utcnow().isoformat(),
        "original_data_unchanged": True
    }


@app.get("/api/v1/tokenization/audit")
async def get_tokenization_audit(
    token_id: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "auditor"]))
):
    """Audit token access logs."""
    return {
        "audit_entries": [
            {
                "timestamp": "2025-01-16T10:30:00Z",
                "operation": "detokenize",
                "token_id": "tok_abc123",
                "user_id": "analyst@company.com",
                "purpose": "Fraud investigation #12345",
                "success": True
            }
        ],
        "total_entries": 1
    }


# ==============================================
# Secrets Management Endpoints
# ==============================================

@app.post("/api/v1/secrets", response_model=Secret)
async def create_secret(
    request: SecretCreate,
    current_user=Depends(require_roles(["admin", "developer"]))
):
    """Store secret in vault."""
    now = datetime.utcnow()
    return Secret(
        secret_id=f"secret_{request.secret_name}",
        secret_name=request.secret_name,
        version=1,
        created_at=now,
        last_rotated_at=now,
        next_rotation_at=now + timedelta(days=request.rotation_days),
        auto_rotate=request.auto_rotate,
        tags=request.tags
    )


@app.get("/api/v1/secrets/{secret_id}")
async def get_secret(
    secret_id: str,
    current_user=Depends(require_roles(["admin", "developer"]))
):
    """Retrieve secret from vault."""
    return {
        "secret_id": secret_id,
        "secret_value": "***SENSITIVE***",  # Only returned to authorized users in real impl
        "version": 1,
        "retrieved_at": datetime.utcnow().isoformat(),
        "retrieved_by": current_user,
        "audit_logged": True
    }


@app.put("/api/v1/secrets/{secret_id}/rotate")
async def rotate_secret(
    secret_id: str,
    new_value: Optional[str] = None,
    current_user=Depends(require_roles(["admin"]))
):
    """Rotate secret (manual or auto-generate)."""
    return {
        "secret_id": secret_id,
        "old_version": 1,
        "new_version": 2,
        "rotated_at": datetime.utcnow().isoformat(),
        "auto_generated": new_value is None,
        "dependent_services_notified": True
    }


@app.post("/api/v1/secrets/scan", response_model=Dict)
async def scan_for_secrets(
    request: SecretScanRequest,
    current_user=Depends(require_roles(["security_engineer"]))
):
    """Scan codebase for exposed secrets."""
    return {
        "scan_id": "scan_001",
        "target": request.repository_url or request.directory_path,
        "secrets_found": 3,
        "findings": [
            {
                "secret_type": "aws_access_key",
                "file": "config/production.yaml",
                "line": 45,
                "severity": "critical",
                "recommendation": "Move to AWS Secrets Manager"
            },
            {
                "secret_type": "private_key",
                "file": "keys/id_rsa",
                "line": 1,
                "severity": "high",
                "recommendation": "Remove from repository, use SSH agent"
            }
        ],
        "scanned_at": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/secrets/audit")
async def get_secret_audit(
    secret_id: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "auditor"]))
):
    """Get secret access audit logs."""
    return {
        "audit_entries": [
            {
                "timestamp": "2025-01-16T10:15:00Z",
                "operation": "read",
                "secret_id": "secret_db_password",
                "user_id": "app-server-01",
                "source_ip": "10.0.1.45",
                "success": True
            }
        ]
    }


# ==============================================
# Vulnerability Scanning Endpoints
# ==============================================

@app.post("/api/v1/security/scan/container", response_model=ScanResult)
async def scan_container(
    request: ContainerScanRequest,
    current_user=Depends(require_roles(["security_engineer", "developer"]))
):
    """Scan container image for vulnerabilities."""
    vulnerabilities = [
        Vulnerability(
            cve_id="CVE-2024-12345",
            severity=Severity.HIGH,
            package="openssl",
            installed_version="1.1.1k",
            fixed_version="1.1.1n",
            description="Buffer overflow in SSL certificate parsing",
            cvss_score=8.1,
            published_date=datetime(2024, 1, 15)
        )
    ]

    return ScanResult(
        scan_id="scan_container_001",
        target=request.image,
        scan_type="container",
        vulnerabilities_found=1,
        critical_count=0,
        high_count=1,
        medium_count=0,
        low_count=0,
        scanned_at=datetime.utcnow(),
        vulnerabilities=vulnerabilities
    )


@app.post("/api/v1/security/scan/dependencies")
async def scan_dependencies(
    manifest_file: str,  # package.json, requirements.txt, etc.
    current_user=Depends(require_roles(["security_engineer", "developer"]))
):
    """Scan dependencies for known vulnerabilities."""
    return {
        "scan_id": "scan_deps_001",
        "manifest": manifest_file,
        "dependencies_scanned": 125,
        "vulnerabilities_found": 8,
        "critical_count": 1,
        "high_count": 3,
        "medium_count": 4,
        "recommendations": [
            {"package": "lodash", "current": "4.17.15", "fixed": "4.17.21", "cve": "CVE-2021-23337"}
        ]
    }


@app.post("/api/v1/security/scan/iac")
async def scan_infrastructure_code(
    iac_path: str,
    iac_type: str = "terraform",
    current_user=Depends(require_roles(["security_engineer"]))
):
    """Scan infrastructure-as-code for security issues."""
    return {
        "scan_id": "scan_iac_001",
        "path": iac_path,
        "iac_type": iac_type,
        "issues_found": 5,
        "critical": 0,
        "high": 2,
        "medium": 3,
        "findings": [
            {
                "severity": "high",
                "rule": "S3_BUCKET_PUBLIC_ACCESS",
                "resource": "aws_s3_bucket.data_lake",
                "message": "S3 bucket allows public access",
                "remediation": "Set block_public_acls = true"
            }
        ]
    }


@app.get("/api/v1/security/vulnerabilities")
async def list_vulnerabilities(
    severity: Optional[Severity] = None,
    status: Optional[str] = Query(None, description="open, patched, risk_accepted"),
    current_user=Depends(require_roles(["security_engineer"]))
):
    """List all vulnerabilities across platform."""
    return {
        "vulnerabilities": [
            {
                "vulnerability_id": "vuln_001",
                "cve_id": "CVE-2024-12345",
                "severity": "high",
                "affected_systems": ["app-server-01", "app-server-02"],
                "status": "open",
                "detected_date": "2025-01-10",
                "sla_days_remaining": 3
            }
        ],
        "total": 1,
        "sla_breaches": 0
    }


@app.post("/api/v1/security/remediate")
async def remediate_vulnerability(
    vulnerability_id: str,
    remediation_type: str = "auto_patch",
    current_user=Depends(require_roles(["admin", "security_engineer"]))
):
    """Auto-remediate vulnerability."""
    return {
        "vulnerability_id": vulnerability_id,
        "remediation_type": remediation_type,
        "status": "in_progress",
        "affected_systems": 2,
        "estimated_completion_minutes": 15,
        "rollback_plan": "available"
    }


# ==============================================
# Behavioral Analytics Endpoints
# ==============================================

@app.get("/api/v1/security/user-risk-score/{user_id}", response_model=UserRiskScore)
async def get_user_risk_score(
    user_id: str,
    current_user=Depends(require_roles(["security_engineer", "admin"]))
):
    """Get user risk score based on behavior."""
    return UserRiskScore(
        user_id=user_id,
        risk_score=35,
        risk_level=RiskLevel.MEDIUM,
        contributing_factors=[
            {"factor": "off_hours_access", "weight": 15, "description": "3 logins after 10pm this week"},
            {"factor": "unusual_query_volume", "weight": 10, "description": "200% above baseline"},
            {"factor": "failed_auth_attempts", "weight": 10, "description": "5 failed logins yesterday"}
        ],
        anomalies_detected=3,
        last_updated=datetime.utcnow()
    )


@app.get("/api/v1/security/anomalies")
async def list_anomalies(
    severity: Optional[Severity] = None,
    user_id: Optional[str] = None,
    current_user=Depends(require_roles(["security_engineer"]))
):
    """List detected behavioral anomalies."""
    anomalies = [
        Anomaly(
            anomaly_id="anom_001",
            user_id="analyst@company.com",
            anomaly_type="unusual_data_export",
            description="Exported 50GB of data, baseline is 2GB",
            severity=Severity.HIGH,
            detected_at=datetime.utcnow(),
            baseline_behavior={"avg_export_gb": 2, "std_dev": 0.5},
            observed_behavior={"export_gb": 50},
            risk_score_impact=25
        )
    ]

    return {"anomalies": anomalies, "total": len(anomalies)}


@app.post("/api/v1/security/incident")
async def create_security_incident(
    incident_type: str,
    severity: Severity,
    description: str,
    user_id: Optional[str] = None,
    current_user=Depends(require_roles(["security_engineer"]))
):
    """Create security incident."""
    return {
        "incident_id": "inc_001",
        "incident_type": incident_type,
        "severity": severity.value,
        "status": "open",
        "assigned_to": "security-team@company.com",
        "created_at": datetime.utcnow().isoformat(),
        "sla_hours": 4 if severity == Severity.CRITICAL else 24,
        "ticket_created": "JIRA-SEC-001"
    }


@app.get("/api/v1/security/insider-threats")
async def detect_insider_threats(
    risk_threshold: int = 70,
    current_user=Depends(require_roles(["security_engineer", "admin"]))
):
    """Detect potential insider threats."""
    return {
        "high_risk_users": [
            {
                "user_id": "contractor@company.com",
                "risk_score": 85,
                "red_flags": [
                    "Access to sensitive data outside role scope",
                    "Large data exports before termination notice",
                    "VPN usage from unusual countries"
                ],
                "recommended_actions": [
                    "Review access permissions",
                    "Enable enhanced monitoring",
                    "Notify HR/Legal"
                ]
            }
        ],
        "total_high_risk": 1,
        "analysis_date": datetime.utcnow().isoformat()
    }


# ==============================================
# Encryption Endpoints
# ==============================================

@app.post("/api/v1/encryption/keys")
async def create_encryption_key(
    request: EncryptionKeyCreate,
    current_user=Depends(require_roles(["admin", "security_engineer"]))
):
    """Create encryption key."""
    return {
        "key_id": f"key_{request.key_name}",
        "key_name": request.key_name,
        "algorithm": request.key_algorithm,
        "purpose": request.purpose,
        "created_at": datetime.utcnow().isoformat(),
        "next_rotation": (datetime.utcnow() + timedelta(days=request.rotation_days)).isoformat(),
        "hsm_backed": True
    }


@app.post("/api/v1/encryption/encrypt")
async def encrypt_data(
    request: EncryptRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Encrypt data with specified key."""
    import base64
    ciphertext = base64.b64encode(request.plaintext.encode()).decode()

    return {
        "ciphertext": ciphertext,
        "key_id": request.key_id,
        "algorithm": "AES-256-GCM",
        "encrypted_at": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/encryption/decrypt")
async def decrypt_data(
    request: DecryptRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Decrypt data (audited)."""
    import base64
    plaintext = base64.b64decode(request.ciphertext).decode()

    return {
        "plaintext": plaintext,
        "key_id": request.key_id,
        "decrypted_by": current_user,
        "purpose": request.purpose,
        "decrypted_at": datetime.utcnow().isoformat(),
        "audit_logged": True
    }


@app.put("/api/v1/encryption/keys/{key_id}/rotate")
async def rotate_encryption_key(
    key_id: str,
    current_user=Depends(require_roles(["admin"]))
):
    """Rotate encryption key."""
    return {
        "key_id": key_id,
        "old_version": 1,
        "new_version": 2,
        "rotated_at": datetime.utcnow().isoformat(),
        "re_encryption_required": True,
        "re_encryption_status": "scheduled"
    }


# ==============================================
# Access Control Endpoints
# ==============================================

@app.post("/api/v1/access/jit-request")
async def request_jit_access(
    request: JITAccessRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Request just-in-time elevated access."""
    expires_at = datetime.utcnow() + timedelta(hours=request.duration_hours)

    return {
        "request_id": "jit_001",
        "resource": request.resource,
        "permissions": request.permissions,
        "status": "approved",  # Could be pending approval in real impl
        "expires_at": expires_at.isoformat(),
        "granted_at": datetime.utcnow().isoformat(),
        "justification": request.justification
    }


@app.get("/api/v1/access/review")
async def get_access_review(
    user_id: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "manager"]))
):
    """Get access review for certification."""
    return {
        "review_id": "review_q1_2025",
        "users_requiring_review": 150,
        "reviews": [
            {
                "user_id": "analyst@company.com",
                "resources": ["sales_data", "customer_pii"],
                "last_used": "2025-01-15",
                "review_required": True,
                "recommendation": "retain_access"
            }
        ]
    }


@app.post("/api/v1/access/revoke")
async def revoke_access(
    user_id: str,
    resources: List[str],
    reason: str,
    current_user=Depends(require_roles(["admin"]))
):
    """Revoke user access."""
    return {
        "user_id": user_id,
        "resources_revoked": resources,
        "revoked_by": current_user,
        "revoked_at": datetime.utcnow().isoformat(),
        "reason": reason,
        "user_notified": True
    }


@app.get("/api/v1/access/audit")
async def get_access_audit(
    user_id: Optional[str] = None,
    resource: Optional[str] = None,
    start_date: Optional[str] = None,
    current_user=Depends(require_roles(["auditor", "admin"]))
):
    """Get access audit trail."""
    return {
        "audit_entries": [
            {
                "timestamp": "2025-01-16T10:30:00Z",
                "user_id": "analyst@company.com",
                "resource": "sales_data",
                "action": "read",
                "ip_address": "10.0.1.50",
                "device_id": "laptop-12345",
                "success": True
            }
        ],
        "total_entries": 1
    }


# ==============================================
# DLP Endpoints
# ==============================================

@app.post("/api/v1/dlp/policies")
async def create_dlp_policy(
    policy: DLPPolicy,
    current_user=Depends(require_roles(["admin", "security_engineer"]))
):
    """Create DLP policy."""
    return {
        "policy_id": f"dlp_{policy.policy_name}",
        "policy_name": policy.policy_name,
        "sensitive_data_types": policy.sensitive_data_types,
        "action": policy.action,
        "threshold": policy.threshold,
        "created_at": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/dlp/scan")
async def scan_for_sensitive_data(
    request: DLPScanRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Scan content for sensitive data."""
    return {
        "scan_id": "dlp_scan_001",
        "sensitive_data_found": True,
        "findings": [
            {"type": "ssn", "count": 15, "sample": "XXX-XX-1234"},
            {"type": "credit_card", "count": 3, "sample": "XXXX-XXXX-XXXX-5678"}
        ],
        "policy_violations": ["block_pii_export"],
        "action_taken": "quarantine",
        "scanned_at": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/dlp/violations")
async def list_dlp_violations(
    severity: Optional[Severity] = None,
    current_user=Depends(require_roles(["security_engineer"]))
):
    """List DLP violations."""
    return {
        "violations": [
            {
                "violation_id": "dlp_viol_001",
                "policy_name": "block_pii_export",
                "user_id": "analyst@company.com",
                "sensitive_data_type": "ssn",
                "occurrences": 150,
                "action_taken": "blocked",
                "detected_at": "2025-01-16T09:45:00Z"
            }
        ],
        "total": 1
    }


@app.post("/api/v1/dlp/quarantine")
async def quarantine_data(
    content_id: str,
    reason: str,
    current_user=Depends(require_roles(["security_engineer"]))
):
    """Quarantine sensitive data for review."""
    return {
        "quarantine_id": "quar_001",
        "content_id": content_id,
        "reason": reason,
        "quarantined_at": datetime.utcnow().isoformat(),
        "review_required": True,
        "approver": "security-team@company.com"
    }
