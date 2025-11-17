"""Graph analytics service."""
from sqlalchemy.orm import Session
from src.models.knowledge_node import KnowledgeNode

class GraphService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_node(self, node_type: str, properties: dict):
        node = KnowledgeNode(node_type=node_type, properties=properties)
        self.db.add(node)
        self.db.commit()
        return node
