"""Schemas for data products."""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class DataProductCreate(BaseModel):
    name: str
    domain_id: str
    owner: str
    product_type: str = "dataset"
    access_type: str = "internal"
    data_location: str
    description: Optional[str] = None

class DataProductResponse(BaseModel):
    product_id: str
    name: str
    domain_id: str
    owner: str
    product_type: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
