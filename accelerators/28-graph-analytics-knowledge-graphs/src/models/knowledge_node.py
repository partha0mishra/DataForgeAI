"""Knowledge Graph Node model."""
from sqlalchemy import Column, String, DateTime, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    node_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_type = Column(String(50), nullable=False)  # entity, concept, attribute
    label = Column(String(200), nullable=False)
    properties = Column(JSON)
    embedding = Column(JSON)  # Vector embedding
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    edge_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_node_id = Column(String(36), nullable=False, index=True)
    target_node_id = Column(String(36), nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False)
    properties = Column(JSON)
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
