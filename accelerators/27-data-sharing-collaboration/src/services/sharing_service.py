"""Data sharing service."""
from sqlalchemy.orm import Session
from src.models.sharing_agreement import SharingAgreement

class SharingService:
    def __init__(self, db: Session):
        self.db = db

    def create_agreement(self, provider_org: str, consumer_org: str, data_assets: list, terms: dict = None):
        agreement = SharingAgreement(
            provider_org=provider_org,
            consumer_org=consumer_org,
            data_assets=data_assets,
            terms=terms or {}
        )
        self.db.add(agreement)
        self.db.commit()
        return agreement

    def get_agreement(self, agreement_id: str):
        """Get sharing agreement by ID."""
        return self.db.query(SharingAgreement).filter(
            SharingAgreement.agreement_id == agreement_id
        ).first()

    def deactivate_agreement(self, agreement_id: str):
        """Deactivate a sharing agreement."""
        agreement = self.get_agreement(agreement_id)
        if agreement:
            agreement.active = False
            self.db.commit()
        return agreement
