"""Repository for TableConversion."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.models.table_conversion import TableConversion

class TableConversionRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: Dict[str, Any]) -> TableConversion:
        conversion = TableConversion(**data)
        self.db.add(conversion)
        self.db.commit()
        self.db.refresh(conversion)
        return conversion
    
    def get_by_id(self, conversion_id: str) -> Optional[TableConversion]:
        return self.db.query(TableConversion).filter(TableConversion.conversion_id == conversion_id).first()
    
    def get_by_table(self, table_name: str) -> List[TableConversion]:
        return self.db.query(TableConversion).filter(TableConversion.table_name == table_name).order_by(desc(TableConversion.created_at)).all()
    
    def update(self, conversion_id: str, updates: Dict[str, Any]) -> Optional[TableConversion]:
        conversion = self.get_by_id(conversion_id)
        if conversion:
            for key, value in updates.items():
                if hasattr(conversion, key):
                    setattr(conversion, key, value)
            self.db.commit()
            self.db.refresh(conversion)
        return conversion
