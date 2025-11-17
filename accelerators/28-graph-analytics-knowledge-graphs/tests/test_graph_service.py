"""Tests for Graph Service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.knowledge_node import Base, KnowledgeNode, KnowledgeEdge
from src.services.graph_service import GraphService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_node(db_session):
    """Test creating a knowledge node."""
    service = GraphService(db_session)
    node = service.create_node(
        node_type="entity",
        label="Apple Inc.",
        properties={"industry": "Technology"}
    )

    assert node.node_id is not None
    assert node.node_type == "entity"
    assert node.label == "Apple Inc."
    assert node.properties["industry"] == "Technology"


def test_create_edge(db_session):
    """Test creating a knowledge edge."""
    service = GraphService(db_session)

    # Create two nodes
    node1 = service.create_node("entity", "Apple Inc.", {})
    node2 = service.create_node("entity", "Tim Cook", {})

    # Create edge
    edge = service.create_edge(
        source_id=node1.node_id,
        target_id=node2.node_id,
        relationship_type="CEO_OF",
        properties={"since": "2011"}
    )

    assert edge.edge_id is not None
    assert edge.source_node_id == node1.node_id
    assert edge.target_node_id == node2.node_id
    assert edge.relationship_type == "CEO_OF"


def test_query_graph(db_session):
    """Test querying graph neighbors."""
    service = GraphService(db_session)

    # Create nodes and edges
    node1 = service.create_node("entity", "Apple Inc.", {})
    node2 = service.create_node("entity", "Tim Cook", {})
    edge = service.create_edge(node1.node_id, node2.node_id, "CEO_OF", {})

    # Query graph
    result = service.query_graph(node1.node_id, max_depth=1)

    assert result is not None
    assert result['node'].node_id == node1.node_id
    assert len(result['edges']) == 1
