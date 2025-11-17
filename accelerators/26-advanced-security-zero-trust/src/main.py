"""Advanced Security & Zero Trust - Production API."""
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from src.database import get_db, init_db
from src.services.security_service import SecurityService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Advanced Security & Zero Trust API", version="1.0.0")

class PolicyCreate(BaseModel):
    name: str
    policy_type: str
    rules: dict

class AccessCheck(BaseModel):
    principal_id: str
    resource_id: str
    permission: str

@app.on_event("startup")
async def startup():
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/policies")
async def create_policy(policy: PolicyCreate, db: Session = Depends(get_db)):
    service = SecurityService(db)
    result = service.create_policy(policy.name, policy.policy_type, policy.rules)
    return {"policy_id": result.policy_id, "name": result.name}

@app.post("/api/v1/access/check")
async def check_access(request: AccessCheck, db: Session = Depends(get_db)):
    service = SecurityService(db)
    allowed = service.check_access(request.principal_id, request.resource_id, request.permission)
    return {"allowed": allowed}

@app.post("/api/v1/threats")
async def log_threat(threat_type: str, severity: str, db: Session = Depends(get_db)):
    service = SecurityService(db)
    threat = service.log_threat(threat_type, severity)
    return {"detection_id": threat.detection_id, "severity": severity}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8026)
