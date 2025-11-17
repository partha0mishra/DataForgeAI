"""Graph analytics service."""
from sqlalchemy.orm import Session
from src.models.knowledge_node import KnowledgeNode, KnowledgeEdge

class GraphService:
    def __init__(self, db: Session):
        self.db = db

    def create_node(self, node_type: str, label: str, properties: dict):
        node = KnowledgeNode(node_type=node_type, label=label, properties=properties)
        self.db.add(node)
        self.db.commit()
        return node

    def create_edge(self, source_id: str, target_id: str, relationship_type: str, properties: dict = None):
        edge = KnowledgeEdge(
            source_node_id=source_id,
            target_node_id=target_id,
            relationship_type=relationship_type,
            properties=properties or {}
        )
        self.db.add(edge)
        self.db.commit()
        return edge

    def query_graph(self, node_id: str, max_depth: int = 2):
        """Traverse graph from a starting node."""
        node = self.db.query(KnowledgeNode).filter(KnowledgeNode.node_id == node_id).first()
        if not node:
            return None

        edges = self.db.query(KnowledgeEdge).filter(
            (KnowledgeEdge.source_node_id == node_id) |
            (KnowledgeEdge.target_node_id == node_id)
        ).all()

        return {
            'node': node,
            'edges': edges,
            'depth': 1
        }
