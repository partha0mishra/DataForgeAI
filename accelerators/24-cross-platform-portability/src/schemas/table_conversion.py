"""Schemas for table conversion."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TableConversionRequest(BaseModel):
    table_name: str
    source_path: str
    source_format: str
    target_format: str
    preserve_partitioning: bool = True
    preserve_stats: bool = True

class TableConversionResponse(BaseModel):
    conversion_id: str
    table_name: str
    source_format: str
    target_format: str
    status: str
    target_path: Optional[str] = None
    conversion_duration_ms: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
