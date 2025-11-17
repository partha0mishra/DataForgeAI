"""ThreatDetection model."""
from sqlalchemy import Column, String, DateTime, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class ThreatDetection(Base):
    __tablename__ = "threat_detections"
    
    detection_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    threat_type = Column(String(50), nullable=False, index=True)  # intrusion, malware, anomaly
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    source_ip = Column(String(50))
    target_resource = Column(String(200))
    indicators = Column(JSON)
    risk_score = Column(Float)
    status = Column(String(20), default='detected')  # detected, investigating, mitigated, false_positive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
