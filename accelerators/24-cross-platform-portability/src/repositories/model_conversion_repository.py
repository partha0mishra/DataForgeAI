"""Repository for ModelConversion."""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from src.models.model_conversion import ModelConversion

class ModelConversionRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: Dict[str, Any]) -> ModelConversion:
        conversion = ModelConversion(**data)
        self.db.add(conversion)
        self.db.commit()
        self.db.refresh(conversion)
        return conversion
    
    def get_by_id(self, conversion_id: str) -> Optional[ModelConversion]:
        return self.db.query(ModelConversion).filter(ModelConversion.conversion_id == conversion_id).first()
    
    def get_by_model_id(self, model_id: str, limit: int = 50) -> List[ModelConversion]:
        return self.db.query(ModelConversion).filter(ModelConversion.model_id == model_id).order_by(desc(ModelConversion.created_at)).limit(limit).all()
    
    def get_by_status(self, status: str) -> List[ModelConversion]:
        return self.db.query(ModelConversion).filter(ModelConversion.status == status).all()
    
    def update(self, conversion_id: str, updates: Dict[str, Any]) -> Optional[ModelConversion]:
        conversion = self.get_by_id(conversion_id)
        if conversion:
            for key, value in updates.items():
                if hasattr(conversion, key):
                    setattr(conversion, key, value)
            self.db.commit()
            self.db.refresh(conversion)
        return conversion
    
    def get_stats(self) -> Dict[str, Any]:
        total = self.db.query(ModelConversion).count()
        by_status = self.db.query(ModelConversion.status, func.count()).group_by(ModelConversion.status).all()
        return {"total": total, "by_status": dict(by_status)}
