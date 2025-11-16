"""Graph Analytics & Knowledge Graphs Accelerator."""

from fastapi import FastAPI, Depends, UploadFile, File
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../shared-libraries/dataforge-common"))
from dataforge_common.security import require_roles

app = FastAPI(title="Graph Analytics & Knowledge Graphs")


class GraphDatabaseType(str, Enum):
    """Graph database types."""
    NEO4J = "neo4j"
    NEPTUNE = "neptune"
    TIGERGRAPH = "tigergraph"
    ARANGODB = "arangodb"
    COSMOS_GREMLIN = "cosmos_gremlin"


class QueryLanguage(str, Enum):
    """Graph query languages."""
    CYPHER = "cypher"
    GREMLIN = "gremlin"
    SPARQL = "sparql"


class GraphAlgorithm(str, Enum):
    """Graph algorithms."""
    PAGERANK = "pagerank"
    BETWEENNESS_CENTRALITY = "betweenness_centrality"
    CLOSENESS_CENTRALITY = "closeness_centrality"
    LOUVAIN = "louvain"
    LABEL_PROPAGATION = "label_propagation"
    CONNECTED_COMPONENTS = "connected_components"
    SHORTEST_PATH = "shortest_path"
    NODE_SIMILARITY = "node_similarity"


class EmbeddingAlgorithm(str, Enum):
    """Node embedding algorithms."""
    NODE2VEC = "node2vec"
    DEEPWALK = "deepwalk"
    GRAPHSAGE = "graphsage"
    LINE = "line"


# ==============================================
# Graph Database Models
# ==============================================

class GraphCreate(BaseModel):
    """Create graph database request."""
    name: str
    database_type: GraphDatabaseType
    description: str
    node_types: List[str] = []
    edge_types: List[str] = []
    properties: Dict[str, Any] = {}


class Graph(BaseModel):
    """Graph database."""
    graph_id: str
    name: str
    database_type: GraphDatabaseType
    description: str
    node_count: int
    edge_count: int
    node_types: List[str]
    edge_types: List[str]
    created_at: datetime
    status: str


class GraphStats(BaseModel):
    """Graph statistics."""
    graph_id: str
    node_count: int
    edge_count: int
    avg_degree: float
    density: float
    connected_components: int
    largest_component_size: int
    avg_clustering_coefficient: Optional[float]


# ==============================================
# Data Import Models
# ==============================================

class CSVImportRequest(BaseModel):
    """CSV import request."""
    nodes_file: str
    edges_file: Optional[str] = None
    node_id_column: str
    node_label_column: Optional[str] = None
    edge_source_column: Optional[str] = None
    edge_target_column: Optional[str] = None
    edge_type_column: Optional[str] = None


class RelationalImportRequest(BaseModel):
    """Import from relational database."""
    connection_string: str
    node_tables: List[Dict[str, str]]  # [{table, id_column, label}]
    edge_tables: List[Dict[str, str]]  # [{table, source_col, target_col, type}]


class StreamImportRequest(BaseModel):
    """Stream import configuration."""
    kafka_topic: str
    kafka_bootstrap_servers: str
    message_format: str = "json"
    node_path: Optional[str] = None
    edge_path: Optional[str] = None


# ==============================================
# Query Models
# ==============================================

class GraphQuery(BaseModel):
    """Graph query request."""
    graph_id: str
    query: str
    language: QueryLanguage
    parameters: Dict[str, Any] = {}
    limit: int = 100


class QueryResult(BaseModel):
    """Query result."""
    query_id: str
    rows: List[Dict[str, Any]]
    execution_time_ms: float
    rows_returned: int


class NeighborsRequest(BaseModel):
    """Get neighbors request."""
    node_id: str
    hops: int = 1
    edge_types: Optional[List[str]] = None
    direction: str = "both"  # outgoing, incoming, both


# ==============================================
# Graph Algorithm Models
# ==============================================

class PageRankRequest(BaseModel):
    """PageRank request."""
    graph_id: str
    damping_factor: float = 0.85
    max_iterations: int = 20
    tolerance: float = 0.0001


class CommunityDetectionRequest(BaseModel):
    """Community detection request."""
    graph_id: str
    algorithm: str = "louvain"  # louvain, label_propagation
    min_community_size: int = 2
    resolution: float = 1.0


class ShortestPathRequest(BaseModel):
    """Shortest path request."""
    graph_id: str
    source_node_id: str
    target_node_id: str
    weight_property: Optional[str] = None


class NodeSimilarityRequest(BaseModel):
    """Node similarity request."""
    graph_id: str
    node_id: str
    top_k: int = 10
    similarity_metric: str = "jaccard"  # jaccard, cosine, overlap


# ==============================================
# Graph ML Models
# ==============================================

class NodeEmbeddingRequest(BaseModel):
    """Node embedding request."""
    graph_id: str
    algorithm: EmbeddingAlgorithm
    dimensions: int = 128
    walk_length: int = 80
    num_walks: int = 10
    window_size: int = 10


class LinkPredictionRequest(BaseModel):
    """Link prediction request."""
    graph_id: str
    model_id: Optional[str] = None
    node_pairs: Optional[List[List[str]]] = None  # Predict for specific pairs
    top_k: int = 100  # Top k most likely links


class GNNTrainRequest(BaseModel):
    """Train GNN request."""
    graph_id: str
    model_type: str = "gcn"  # gcn, gat, graphsage
    task: str = "node_classification"  # node_classification, link_prediction
    target_property: str
    epochs: int = 100
    learning_rate: float = 0.01


# ==============================================
# Knowledge Graph Models
# ==============================================

class KnowledgeGraphCreate(BaseModel):
    """Create knowledge graph."""
    name: str
    description: str
    ontology_url: Optional[str] = None
    base_uri: str


class EntityExtractionRequest(BaseModel):
    """Entity extraction request."""
    kg_id: str
    text: str
    entity_types: List[str] = ["PERSON", "ORG", "GPE", "PRODUCT"]


class EntityLinkingRequest(BaseModel):
    """Entity linking/resolution."""
    kg_id: str
    entities: List[Dict[str, Any]]
    similarity_threshold: float = 0.85


class SemanticSearchRequest(BaseModel):
    """Semantic search on knowledge graph."""
    kg_id: str
    query: str
    entity_types: Optional[List[str]] = None
    limit: int = 10


class QuestionAnsweringRequest(BaseModel):
    """Question answering on knowledge graph."""
    kg_id: str
    question: str
    max_hops: int = 3


# ==============================================
# Visualization Models
# ==============================================

class VisualizationRequest(BaseModel):
    """Visualization request."""
    graph_id: str
    layout_algorithm: str = "force_directed"  # force_directed, hierarchical, circular
    max_nodes: int = 1000
    node_filter: Optional[Dict] = None
    edge_filter: Optional[Dict] = None


# ==============================================
# Graph Database Management Endpoints
# ==============================================

@app.post("/api/v1/graphs", response_model=Graph)
async def create_graph(
    request: GraphCreate,
    current_user=Depends(require_roles(["admin", "data_engineer"]))
):
    """Create graph database."""
    return Graph(
        graph_id=f"graph_{request.name}",
        name=request.name,
        database_type=request.database_type,
        description=request.description,
        node_count=0,
        edge_count=0,
        node_types=request.node_types,
        edge_types=request.edge_types,
        created_at=datetime.utcnow(),
        status="active"
    )


@app.get("/api/v1/graphs", response_model=List[Graph])
async def list_graphs(
    current_user=Depends(require_roles(["user"]))
):
    """List all graphs."""
    return [
        Graph(
            graph_id="graph_fraud_detection",
            name="fraud_detection",
            database_type=GraphDatabaseType.NEO4J,
            description="Transaction fraud detection network",
            node_count=5000000,
            edge_count=25000000,
            node_types=["Customer", "Account", "Transaction", "Device"],
            edge_types=["OWNS", "TRANSACTED", "LOGGED_IN_FROM"],
            created_at=datetime.utcnow(),
            status="active"
        )
    ]


@app.delete("/api/v1/graphs/{graph_id}")
async def delete_graph(
    graph_id: str,
    current_user=Depends(require_roles(["admin"]))
):
    """Delete graph database."""
    return {
        "graph_id": graph_id,
        "status": "deleted",
        "deleted_at": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/graphs/{graph_id}/stats", response_model=GraphStats)
async def get_graph_stats(
    graph_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Get graph statistics."""
    return GraphStats(
        graph_id=graph_id,
        node_count=5000000,
        edge_count=25000000,
        avg_degree=10.0,
        density=0.000001,
        connected_components=150,
        largest_component_size=4950000,
        avg_clustering_coefficient=0.35
    )


# ==============================================
# Data Import Endpoints
# ==============================================

@app.post("/api/v1/graphs/{graph_id}/import/csv")
async def import_csv(
    graph_id: str,
    request: CSVImportRequest,
    current_user=Depends(require_roles(["data_engineer"]))
):
    """Import CSV files as nodes and edges."""
    return {
        "import_id": "import_001",
        "graph_id": graph_id,
        "status": "processing",
        "nodes_file": request.nodes_file,
        "edges_file": request.edges_file,
        "estimated_completion_minutes": 15,
        "started_at": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/graphs/{graph_id}/import/relational")
async def import_relational(
    graph_id: str,
    request: RelationalImportRequest,
    current_user=Depends(require_roles(["data_engineer"]))
):
    """Import from relational database."""
    return {
        "import_id": "import_002",
        "graph_id": graph_id,
        "status": "processing",
        "node_tables": len(request.node_tables),
        "edge_tables": len(request.edge_tables),
        "estimated_nodes": 1000000,
        "estimated_edges": 5000000,
        "started_at": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/graphs/{graph_id}/import/stream")
async def import_stream(
    graph_id: str,
    request: StreamImportRequest,
    current_user=Depends(require_roles(["data_engineer"]))
):
    """Configure streaming import from Kafka."""
    return {
        "stream_id": "stream_001",
        "graph_id": graph_id,
        "kafka_topic": request.kafka_topic,
        "status": "active",
        "messages_processed": 0,
        "started_at": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/graphs/{graph_id}/import/documents")
async def import_documents(
    graph_id: str,
    document_paths: List[str],
    entity_types: List[str] = ["PERSON", "ORG", "GPE"],
    current_user=Depends(require_roles(["data_engineer"]))
):
    """Extract entities from documents and add to graph."""
    return {
        "extraction_id": "extract_001",
        "graph_id": graph_id,
        "documents": len(document_paths),
        "entity_types": entity_types,
        "status": "processing",
        "estimated_entities": 5000,
        "started_at": datetime.utcnow().isoformat()
    }


# ==============================================
# Graph Query Endpoints
# ==============================================

@app.post("/api/v1/graphs/{graph_id}/query/cypher", response_model=QueryResult)
async def query_cypher(
    graph_id: str,
    query: str,
    parameters: Dict[str, Any] = {},
    limit: int = 100,
    current_user=Depends(require_roles(["analyst", "user"]))
):
    """Execute Cypher query."""
    # Simulate query execution
    results = [
        {"name": "Alice", "title": "Engineer", "connections": 150},
        {"name": "Bob", "title": "Manager", "connections": 200}
    ]

    return QueryResult(
        query_id="query_001",
        rows=results[:limit],
        execution_time_ms=45.3,
        rows_returned=len(results[:limit])
    )


@app.post("/api/v1/graphs/{graph_id}/query/gremlin", response_model=QueryResult)
async def query_gremlin(
    graph_id: str,
    query: str,
    current_user=Depends(require_roles(["analyst", "user"]))
):
    """Execute Gremlin traversal."""
    return QueryResult(
        query_id="query_002",
        rows=[{"path": ["Alice", "Bob", "CEO"], "length": 3}],
        execution_time_ms=32.1,
        rows_returned=1
    )


@app.post("/api/v1/graphs/{graph_id}/query/sparql", response_model=QueryResult)
async def query_sparql(
    graph_id: str,
    query: str,
    current_user=Depends(require_roles(["analyst", "user"]))
):
    """Execute SPARQL query."""
    return QueryResult(
        query_id="query_003",
        rows=[{"subject": "Alice", "predicate": "worksFor", "object": "Acme Corp"}],
        execution_time_ms=28.5,
        rows_returned=1
    )


@app.post("/api/v1/graphs/{graph_id}/neighbors")
async def get_neighbors(
    graph_id: str,
    request: NeighborsRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Get node neighbors (k-hop)."""
    return {
        "node_id": request.node_id,
        "hops": request.hops,
        "neighbors": [
            {
                "node_id": "node_002",
                "node_type": "Customer",
                "distance": 1,
                "edge_type": "TRANSACTED",
                "properties": {"amount": 150.00}
            },
            {
                "node_id": "node_003",
                "node_type": "Customer",
                "distance": 2,
                "edge_type": "SHARED_DEVICE",
                "properties": {"device_id": "device_123"}
            }
        ],
        "total_neighbors": 2
    }


# ==============================================
# Graph Algorithm Endpoints
# ==============================================

@app.post("/api/v1/graphs/{graph_id}/algorithms/pagerank")
async def compute_pagerank(
    graph_id: str,
    request: PageRankRequest,
    current_user=Depends(require_roles(["analyst"]))
):
    """Compute PageRank centrality."""
    return {
        "algorithm": "pagerank",
        "graph_id": graph_id,
        "parameters": {
            "damping_factor": request.damping_factor,
            "iterations": request.max_iterations
        },
        "top_nodes": [
            {"node_id": "node_001", "pagerank": 0.0045, "rank": 1},
            {"node_id": "node_005", "pagerank": 0.0038, "rank": 2},
            {"node_id": "node_012", "pagerank": 0.0032, "rank": 3}
        ],
        "execution_time_seconds": 12.5,
        "convergence_iterations": 15
    }


@app.post("/api/v1/graphs/{graph_id}/algorithms/community")
async def detect_communities(
    graph_id: str,
    request: CommunityDetectionRequest,
    current_user=Depends(require_roles(["analyst"]))
):
    """Detect communities in graph."""
    return {
        "algorithm": request.algorithm,
        "graph_id": graph_id,
        "communities_found": 45,
        "modularity": 0.72,
        "largest_community_size": 150000,
        "communities": [
            {
                "community_id": "comm_001",
                "size": 150000,
                "density": 0.35,
                "top_nodes": ["node_001", "node_002", "node_003"]
            },
            {
                "community_id": "comm_002",
                "size": 120000,
                "density": 0.28,
                "top_nodes": ["node_010", "node_011", "node_012"]
            }
        ],
        "execution_time_seconds": 45.2
    }


@app.post("/api/v1/graphs/{graph_id}/algorithms/shortest-path")
async def find_shortest_path(
    graph_id: str,
    request: ShortestPathRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Find shortest path between nodes."""
    return {
        "graph_id": graph_id,
        "source": request.source_node_id,
        "target": request.target_node_id,
        "path": ["node_001", "node_005", "node_012", "node_020"],
        "path_length": 4,
        "total_weight": 12.5 if request.weight_property else None,
        "execution_time_ms": 8.3
    }


@app.post("/api/v1/graphs/{graph_id}/algorithms/similarity")
async def compute_node_similarity(
    graph_id: str,
    request: NodeSimilarityRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Compute node similarity."""
    return {
        "graph_id": graph_id,
        "node_id": request.node_id,
        "similarity_metric": request.similarity_metric,
        "similar_nodes": [
            {"node_id": "node_050", "similarity": 0.85},
            {"node_id": "node_075", "similarity": 0.78},
            {"node_id": "node_102", "similarity": 0.72}
        ][:request.top_k],
        "execution_time_ms": 125.5
    }


# ==============================================
# Graph ML Endpoints
# ==============================================

@app.post("/api/v1/graphs/{graph_id}/ml/embeddings")
async def generate_embeddings(
    graph_id: str,
    request: NodeEmbeddingRequest,
    current_user=Depends(require_roles(["ml_engineer"]))
):
    """Generate node embeddings."""
    return {
        "embedding_id": "emb_001",
        "graph_id": graph_id,
        "algorithm": request.algorithm.value,
        "dimensions": request.dimensions,
        "nodes_embedded": 5000000,
        "embedding_file": f"s3://embeddings/{graph_id}/embeddings.parquet",
        "training_time_minutes": 25,
        "completed_at": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/graphs/{graph_id}/ml/link-prediction")
async def predict_links(
    graph_id: str,
    request: LinkPredictionRequest,
    current_user=Depends(require_roles(["analyst", "ml_engineer"]))
):
    """Predict missing or future links."""
    return {
        "prediction_id": "pred_001",
        "graph_id": graph_id,
        "model_id": request.model_id or "default_link_predictor",
        "predicted_links": [
            {
                "source": "node_001",
                "target": "node_050",
                "probability": 0.89,
                "edge_type": "LIKELY_TRANSACT"
            },
            {
                "source": "node_002",
                "target": "node_075",
                "probability": 0.82,
                "edge_type": "LIKELY_CONNECT"
            }
        ][:request.top_k],
        "execution_time_ms": 450.2
    }


@app.post("/api/v1/graphs/{graph_id}/ml/train-gnn")
async def train_gnn(
    graph_id: str,
    request: GNNTrainRequest,
    current_user=Depends(require_roles(["ml_engineer"]))
):
    """Train graph neural network."""
    return {
        "training_job_id": "gnn_train_001",
        "graph_id": graph_id,
        "model_type": request.model_type,
        "task": request.task,
        "status": "training",
        "epochs_total": request.epochs,
        "epochs_completed": 0,
        "current_loss": None,
        "current_accuracy": None,
        "started_at": datetime.utcnow().isoformat(),
        "estimated_completion_minutes": 120
    }


@app.get("/api/v1/graphs/{graph_id}/ml/models")
async def list_ml_models(
    graph_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """List trained ML models for graph."""
    return {
        "graph_id": graph_id,
        "models": [
            {
                "model_id": "model_001",
                "model_type": "gnn",
                "task": "node_classification",
                "accuracy": 0.92,
                "trained_at": "2025-01-15T10:00:00Z",
                "status": "deployed"
            },
            {
                "model_id": "model_002",
                "model_type": "link_prediction",
                "task": "link_prediction",
                "auc": 0.88,
                "trained_at": "2025-01-14T15:30:00Z",
                "status": "deployed"
            }
        ]
    }


# ==============================================
# Knowledge Graph Endpoints
# ==============================================

@app.post("/api/v1/knowledge-graphs")
async def create_knowledge_graph(
    kg: KnowledgeGraphCreate,
    current_user=Depends(require_roles(["admin", "knowledge_engineer"]))
):
    """Create knowledge graph."""
    return {
        "kg_id": f"kg_{kg.name}",
        "name": kg.name,
        "description": kg.description,
        "base_uri": kg.base_uri,
        "entity_count": 0,
        "relation_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/knowledge-graphs/{kg_id}/extract")
async def extract_entities(
    kg_id: str,
    request: EntityExtractionRequest,
    current_user=Depends(require_roles(["knowledge_engineer"]))
):
    """Extract entities from text."""
    # Simulate NER extraction
    entities = [
        {"text": "Apple Inc.", "type": "ORG", "start": 0, "end": 10},
        {"text": "Tim Cook", "type": "PERSON", "start": 15, "end": 23},
        {"text": "Cupertino", "type": "GPE", "start": 30, "end": 39}
    ]

    return {
        "kg_id": kg_id,
        "entities_extracted": entities,
        "entity_count": len(entities),
        "relations_inferred": [
            {"subject": "Tim Cook", "predicate": "ceo_of", "object": "Apple Inc."},
            {"subject": "Apple Inc.", "predicate": "located_in", "object": "Cupertino"}
        ]
    }


@app.post("/api/v1/knowledge-graphs/{kg_id}/link")
async def link_entities(
    kg_id: str,
    request: EntityLinkingRequest,
    current_user=Depends(require_roles(["knowledge_engineer"]))
):
    """Entity linking and resolution."""
    return {
        "kg_id": kg_id,
        "entities_processed": len(request.entities),
        "entities_linked": 85,
        "entities_created": 10,
        "entities_merged": 5,
        "similarity_threshold": request.similarity_threshold
    }


@app.post("/api/v1/knowledge-graphs/{kg_id}/search")
async def semantic_search(
    kg_id: str,
    request: SemanticSearchRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Semantic search on knowledge graph."""
    return {
        "kg_id": kg_id,
        "query": request.query,
        "results": [
            {
                "entity_id": "ent_001",
                "entity_type": "PERSON",
                "label": "Tim Cook",
                "score": 0.95,
                "properties": {"role": "CEO", "company": "Apple Inc."}
            },
            {
                "entity_id": "ent_050",
                "entity_type": "ORG",
                "label": "Apple Inc.",
                "score": 0.88,
                "properties": {"industry": "Technology", "founded": 1976}
            }
        ][:request.limit]
    }


@app.post("/api/v1/knowledge-graphs/{kg_id}/qa")
async def question_answering(
    kg_id: str,
    request: QuestionAnsweringRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Answer questions using knowledge graph."""
    return {
        "kg_id": kg_id,
        "question": request.question,
        "answer": "Tim Cook is the CEO of Apple Inc., which is headquartered in Cupertino, California.",
        "confidence": 0.92,
        "supporting_facts": [
            {"subject": "Tim Cook", "predicate": "ceo_of", "object": "Apple Inc."},
            {"subject": "Apple Inc.", "predicate": "headquarters", "object": "Cupertino"}
        ],
        "reasoning_path": ["Tim Cook", "ceo_of", "Apple Inc.", "headquarters", "Cupertino"],
        "execution_time_ms": 85.3
    }


# ==============================================
# Visualization Endpoints
# ==============================================

@app.get("/api/v1/graphs/{graph_id}/visualize")
async def get_visualization(
    graph_id: str,
    layout: str = "force_directed",
    max_nodes: int = 1000,
    current_user=Depends(require_roles(["user"]))
):
    """Get graph visualization data."""
    return {
        "graph_id": graph_id,
        "layout_algorithm": layout,
        "nodes": [
            {"id": "node_001", "label": "Alice", "type": "Person", "x": 100, "y": 200},
            {"id": "node_002", "label": "Bob", "type": "Person", "x": 300, "y": 150}
        ],
        "edges": [
            {"source": "node_001", "target": "node_002", "type": "KNOWS", "weight": 1.0}
        ],
        "total_nodes": 2,
        "total_edges": 1,
        "truncated": False
    }


@app.post("/api/v1/graphs/{graph_id}/visualize/subgraph")
async def visualize_subgraph(
    graph_id: str,
    request: VisualizationRequest,
    current_user=Depends(require_roles(["user"]))
):
    """Visualize subgraph based on filters."""
    return {
        "graph_id": graph_id,
        "layout": request.layout_algorithm,
        "nodes": [],
        "edges": [],
        "filters_applied": {
            "node_filter": request.node_filter,
            "edge_filter": request.edge_filter
        },
        "visualization_url": f"https://viz.dataforge.ai/graphs/{graph_id}/view"
    }


@app.get("/api/v1/graphs/{graph_id}/visualize/layout")
async def get_layout_algorithms(
    graph_id: str,
    current_user=Depends(require_roles(["user"]))
):
    """Get available layout algorithms."""
    return {
        "algorithms": [
            {
                "name": "force_directed",
                "description": "Physics-based spring layout",
                "best_for": "General purpose, small to medium graphs"
            },
            {
                "name": "hierarchical",
                "description": "Top-down tree layout",
                "best_for": "Organizational charts, dependency trees"
            },
            {
                "name": "circular",
                "description": "Nodes arranged in circle",
                "best_for": "Highlighting cycles, symmetric graphs"
            },
            {
                "name": "community_based",
                "description": "Group nodes by community",
                "best_for": "Social networks, clustered data"
            }
        ]
    }
