"""Disaster Recovery & Multi-Region API."""
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.services.dr_service import DRService

app = FastAPI(title="Disaster Recovery & Multi-Region API")

class BackupCreate(BaseModel):
    resource_id: str
    backup_type: str = "full"
    region: str

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/v1/backups")
async def create_backup(req: BackupCreate, db: Session = Depends(get_db)):
    service = DRService(db)
    backup = service.create_backup(req.resource_id, req.backup_type, req.region)
    return {"backup_id": backup.backup_id, "status": backup.status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8032)
