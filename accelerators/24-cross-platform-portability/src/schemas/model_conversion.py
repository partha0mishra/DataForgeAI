"""Schemas for model conversion."""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class ModelConversionRequest(BaseModel):
    model_id: str
    source_uri: str
    source_format: str
    target_format: str
    target_platform: str
    optimization_level: str = "basic"
    preserve_metadata: bool = True

class ModelConversionResponse(BaseModel):
    conversion_id: str
    model_id: str
    source_format: str
    target_format: str
    target_platform: str
    status: str
    target_uri: Optional[str] = None
    conversion_warnings: Optional[List[str]] = None
    conversion_duration_ms: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
