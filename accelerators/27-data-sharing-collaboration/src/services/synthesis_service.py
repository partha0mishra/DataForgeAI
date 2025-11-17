"""Data synthesis service."""
from sqlalchemy.orm import Session
from src.models.synthetic_dataset import SyntheticDataset
import random

class SynthesisService:
    def __init__(self, db: Session):
        self.db = db
    
    def generate_dataset(self, name: str, schema: dict, row_count: int):
        dataset = SyntheticDataset(
            name=name,
            generation_method='statistical',
            schema=schema,
            row_count=row_count,
            quality_score=random.uniform(0.7, 0.95)
        )
        self.db.add(dataset)
        self.db.commit()
        return dataset
