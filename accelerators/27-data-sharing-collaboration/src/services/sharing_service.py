"""Data sharing service."""
from sqlalchemy.orm import Session
from src.models.sharing_agreement import SharingAgreement

class SharingService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_agreement(self, provider: str, consumer: str, assets: list):
        agreement = SharingAgreement(
            provider_org=provider, 
            consumer_org=consumer, 
            data_assets=assets
        )
        self.db.add(agreement)
        self.db.commit()
        return agreement
