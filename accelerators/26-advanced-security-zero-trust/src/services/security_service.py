"""Security service."""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from src.models.security_policy import SecurityPolicy
from src.models.access_control import AccessControl
from src.models.threat_detection import ThreatDetection
from src.models.audit_log import AuditLog
import uuid

class SecurityService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_policy(self, name: str, policy_type: str, rules: Dict) -> SecurityPolicy:
        policy = SecurityPolicy(name=name, policy_type=policy_type, rules=rules)
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy
    
    def check_access(self, principal_id: str, resource_id: str, permission: str) -> bool:
        controls = self.db.query(AccessControl).filter(
            AccessControl.principal_id == principal_id,
            AccessControl.resource_id == resource_id
        ).all()
        for control in controls:
            if permission in control.permissions:
                return True
        return False
    
    def log_threat(self, threat_type: str, severity: str, **kwargs) -> ThreatDetection:
        threat = ThreatDetection(threat_type=threat_type, severity=severity, **kwargs)
        self.db.add(threat)
        self.db.commit()
        self.db.refresh(threat)
        return threat
    
    def audit_action(self, action: str, principal: str, resource: str, result: str):
        log = AuditLog(action=action, principal=principal, resource=resource, result=result)
        self.db.add(log)
        self.db.commit()
        return log
