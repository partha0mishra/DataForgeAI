"""AIOps service."""
from sqlalchemy.orm import Session
from src.models.incident import Incident

class AIOpsService:
    def __init__(self, db: Session):
        self.db = db
    
    def detect_incident(self, title: str, severity: str, service: str):
        incident = Incident(title=title, severity=severity, service=service)
        self.db.add(incident)
        self.db.commit()
        # Simplified auto-remediation
        if severity in ['low', 'medium']:
            incident.auto_remediation = {'action': 'restart_service', 'applied': True}
            incident.status = 'resolved'
            self.db.commit()
        return incident
