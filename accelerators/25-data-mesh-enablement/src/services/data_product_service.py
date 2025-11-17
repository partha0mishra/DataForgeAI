"""Service for data product management."""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from src.repositories.data_product_repository import DataProductRepository

class DataProductService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DataProductRepository(db)
    
    def create_product(self, name: str, domain_id: str, owner: str, **kwargs) -> Any:
        data = {
            'name': name,
            'domain_id': domain_id,
            'owner': owner,
            'product_type': kwargs.get('product_type', 'dataset'),
            'access_type': kwargs.get('access_type', 'internal'),
            'data_location': kwargs.get('data_location', ''),
            'status': 'draft'
        }
        data.update(kwargs)
        return self.repo.create(data)
    
    def get_product(self, product_id: str):
        return self.repo.get_by_id(product_id)
    
    def list_products(self, domain_id: Optional[str] = None):
        if domain_id:
            return self.repo.get_by_domain(domain_id)
        return self.repo.list_all()
    
    def publish_product(self, product_id: str):
        return self.repo.update(product_id, {'status': 'active'})
