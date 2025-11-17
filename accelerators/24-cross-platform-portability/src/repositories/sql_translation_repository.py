"""Repository for SQLTranslation."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from src.models.sql_translation import SQLTranslation

class SQLTranslationRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: Dict[str, Any]) -> SQLTranslation:
        translation = SQLTranslation(**data)
        if not translation.query_hash and translation.source_sql:
            translation.query_hash = translation.generate_query_hash()
        self.db.add(translation)
        self.db.commit()
        self.db.refresh(translation)
        return translation
    
    def get_by_id(self, translation_id: str) -> Optional[SQLTranslation]:
        return self.db.query(SQLTranslation).filter(SQLTranslation.translation_id == translation_id).first()
    
    def get_by_hash(self, query_hash: str) -> Optional[SQLTranslation]:
        return self.db.query(SQLTranslation).filter(SQLTranslation.query_hash == query_hash).first()
    
    def get_by_platforms(self, source: str, target: str, limit: int = 50) -> List[SQLTranslation]:
        return self.db.query(SQLTranslation).filter(
            SQLTranslation.source_platform == source,
            SQLTranslation.target_platform == target
        ).order_by(desc(SQLTranslation.created_at)).limit(limit).all()
    
    def update(self, translation_id: str, updates: Dict[str, Any]) -> Optional[SQLTranslation]:
        translation = self.get_by_id(translation_id)
        if translation:
            for key, value in updates.items():
                if hasattr(translation, key):
                    setattr(translation, key, value)
            self.db.commit()
            self.db.refresh(translation)
        return translation
