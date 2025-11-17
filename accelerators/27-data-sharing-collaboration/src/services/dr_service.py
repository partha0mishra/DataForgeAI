"""Disaster recovery service."""
from sqlalchemy.orm import Session
from src.models.backup import Backup
import random

class DRService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_backup(self, resource_id: str, backup_type: str, region: str):
        backup = Backup(
            resource_id=resource_id,
            backup_type=backup_type,
            region=region,
            size_gb=random.uniform(1.0, 100.0),
            status='completed',
            verified=True
        )
        self.db.add(backup)
        self.db.commit()
        return backup
