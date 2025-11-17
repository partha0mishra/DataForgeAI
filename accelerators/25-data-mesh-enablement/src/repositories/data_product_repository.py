"""Repository for DataProduct."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.models.data_product import DataProduct

class DataProductRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: Dict[str, Any]) -> DataProduct:
        product = DataProduct(**data)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def get_by_id(self, product_id: str) -> Optional[DataProduct]:
        return self.db.query(DataProduct).filter(DataProduct.product_id == product_id).first()
    
    def get_by_domain(self, domain_id: str) -> List[DataProduct]:
        return self.db.query(DataProduct).filter(DataProduct.domain_id == domain_id).all()
    
    def list_all(self, skip: int = 0, limit: int = 100) -> List[DataProduct]:
        return self.db.query(DataProduct).offset(skip).limit(limit).all()
    
    def update(self, product_id: str, updates: Dict[str, Any]) -> Optional[DataProduct]:
        product = self.get_by_id(product_id)
        if product:
            for key, value in updates.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            self.db.commit()
            self.db.refresh(product)
        return product
