"""Schemas for SQL translation."""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SQLTranslationRequest(BaseModel):
    source_sql: str
    source_platform: str
    target_platform: str
    validate_equivalence: bool = True

class SQLTranslationResponse(BaseModel):
    translation_id: str
    source_platform: str
    target_platform: str
    target_sql: Optional[str] = None
    status: str
    confidence_score: Optional[float] = None
    translation_notes: Optional[List[str]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
