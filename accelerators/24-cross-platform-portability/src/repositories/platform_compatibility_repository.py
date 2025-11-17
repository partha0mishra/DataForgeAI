"""Repository for PlatformCompatibility."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.models.platform_compatibility import PlatformCompatibility

class PlatformCompatibilityRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: Dict[str, Any]) -> PlatformCompatibility:
        analysis = PlatformCompatibility(**data)
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis
    
    def get_by_id(self, analysis_id: str) -> Optional[PlatformCompatibility]:
        return self.db.query(PlatformCompatibility).filter(PlatformCompatibility.analysis_id == analysis_id).first()
    
    def get_by_resource(self, resource_id: str) -> List[PlatformCompatibility]:
        return self.db.query(PlatformCompatibility).filter(PlatformCompatibility.resource_id == resource_id).order_by(desc(PlatformCompatibility.created_at)).all()
