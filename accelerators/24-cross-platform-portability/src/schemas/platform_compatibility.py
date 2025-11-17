"""Schemas for platform compatibility."""
from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime

class PlatformCompatibilityRequest(BaseModel):
    resource_id: str
    resource_type: str
    source_platform: str
    target_platforms: List[str]

class PlatformCompatibilityResponse(BaseModel):
    analysis_id: str
    resource_id: str
    resource_type: str
    platform_compatibility: Dict[str, Any]
    recommended_platform: Optional[str] = None
    portability_score: Optional[float] = None
    migration_effort: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
