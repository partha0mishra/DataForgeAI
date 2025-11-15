"""Data lineage tracking using graph database."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class LineageType(str, Enum):
    """Lineage relationship types."""

    DERIVES_FROM = "derives_from"  # Table B derives from Table A
    READS_FROM = "reads_from"  # Process reads from dataset
    WRITES_TO = "writes_to"  # Process writes to dataset
    TRANSFORMS = "transforms"  # Transformation relationship
    COPIES = "copies"  # Copy relationship
    JOINS = "joins"  # Join relationship


@dataclass
class LineageNode:
    """Node in lineage graph."""

    node_id: str
    node_type: str  # dataset, transformation, pipeline, query
    name: str
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class LineageEdge:
    """Edge in lineage graph."""

    source_id: str
    target_id: str
    relationship_type: LineageType
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class LineageGraph:
    """Lineage graph result."""

    nodes: List[LineageNode]
    edges: List[LineageEdge]
    depth: int


class LineageTracker:
    """
    Data lineage tracker using graph database.

    Tracks:
    - Dataset dependencies
    - Transformation lineage
    - Column-level lineage
    - Impact analysis

    Example:
        tracker = LineageTracker()

        # Track transformation
        tracker.track_transformation(
            source_datasets=["raw.customers", "raw.orders"],
            target_dataset="analytics.customer_orders",
            transformation="JOIN customers ON orders.customer_id",
            metadata={"pipeline": "etl_daily"}
        )

        # Get upstream lineage
        lineage = tracker.get_upstream_lineage("analytics.customer_orders")

        # Analyze impact
        impact = tracker.analyze_impact("raw.customers")
    """

    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
    ):
        """
        Initialize lineage tracker.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.logger = logger

        # In-memory storage (replace with Neo4j)
        self.nodes: Dict[str, LineageNode] = {}
        self.edges: List[LineageEdge] = []

        # Neo4j connection (if configured)
        self.driver = None
        if neo4j_uri and neo4j_user and neo4j_password:
            try:
                from neo4j import GraphDatabase

                self.driver = GraphDatabase.driver(
                    neo4j_uri, auth=(neo4j_user, neo4j_password)
                )
                self.logger.info("Connected to Neo4j", uri=neo4j_uri)
            except Exception as e:
                self.logger.warning(
                    "Failed to connect to Neo4j, using in-memory storage",
                    error=str(e),
                )

        self.logger.info("Lineage tracker initialized")

    def add_node(
        self,
        node_id: str,
        node_type: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add node to lineage graph.

        Args:
            node_id: Node identifier
            node_type: Type of node (dataset, transformation, etc.)
            name: Node name
            metadata: Additional metadata
        """
        if node_id in self.nodes:
            # Update existing node
            self.nodes[node_id].metadata.update(metadata or {})
            return

        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
        )

        self.nodes[node_id] = node

        self.logger.debug("Lineage node added", node_id=node_id, node_type=node_type)

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_type: LineageType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add edge to lineage graph.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Type of relationship
            metadata: Additional metadata
        """
        # Ensure nodes exist
        if source_id not in self.nodes:
            self.add_node(source_id, "dataset", source_id)
        if target_id not in self.nodes:
            self.add_node(target_id, "dataset", target_id)

        edge = LineageEdge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
        )

        self.edges.append(edge)

        self.logger.debug(
            "Lineage edge added",
            source=source_id,
            target=target_id,
            relationship=relationship_type.value,
        )

    def track_transformation(
        self,
        source_datasets: List[str],
        target_dataset: str,
        transformation: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track transformation lineage.

        Args:
            source_datasets: Source dataset IDs
            target_dataset: Target dataset ID
            transformation: Transformation description (SQL, code, etc.)
            metadata: Additional metadata (pipeline, job, timestamp, etc.)
        """
        # Add target node
        self.add_node(
            node_id=target_dataset,
            node_type="dataset",
            name=target_dataset,
            metadata={"transformation": transformation, **(metadata or {})},
        )

        # Add source nodes and edges
        for source in source_datasets:
            self.add_node(
                node_id=source,
                node_type="dataset",
                name=source,
            )

            self.add_edge(
                source_id=source,
                target_id=target_dataset,
                relationship_type=LineageType.DERIVES_FROM,
                metadata={"transformation": transformation, **(metadata or {})},
            )

        self.logger.info(
            "Transformation tracked",
            sources=len(source_datasets),
            target=target_dataset,
        )

    def get_upstream_lineage(
        self,
        dataset_id: str,
        max_depth: int = 5,
    ) -> LineageGraph:
        """
        Get upstream lineage (dependencies).

        Args:
            dataset_id: Dataset identifier
            max_depth: Maximum traversal depth

        Returns:
            Lineage graph
        """
        visited_nodes = set()
        visited_edges = []
        queue = [(dataset_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if depth >= max_depth or current_id in visited_nodes:
                continue

            visited_nodes.add(current_id)

            # Find upstream edges
            for edge in self.edges:
                if edge.target_id == current_id:
                    visited_edges.append(edge)
                    queue.append((edge.source_id, depth + 1))

        # Build graph
        nodes = [self.nodes[node_id] for node_id in visited_nodes if node_id in self.nodes]

        graph = LineageGraph(nodes=nodes, edges=visited_edges, depth=max_depth)

        self.logger.info(
            "Upstream lineage retrieved",
            dataset=dataset_id,
            nodes=len(nodes),
            edges=len(visited_edges),
        )

        return graph

    def get_downstream_lineage(
        self,
        dataset_id: str,
        max_depth: int = 5,
    ) -> LineageGraph:
        """
        Get downstream lineage (consumers).

        Args:
            dataset_id: Dataset identifier
            max_depth: Maximum traversal depth

        Returns:
            Lineage graph
        """
        visited_nodes = set()
        visited_edges = []
        queue = [(dataset_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if depth >= max_depth or current_id in visited_nodes:
                continue

            visited_nodes.add(current_id)

            # Find downstream edges
            for edge in self.edges:
                if edge.source_id == current_id:
                    visited_edges.append(edge)
                    queue.append((edge.target_id, depth + 1))

        # Build graph
        nodes = [self.nodes[node_id] for node_id in visited_nodes if node_id in self.nodes]

        graph = LineageGraph(nodes=nodes, edges=visited_edges, depth=max_depth)

        self.logger.info(
            "Downstream lineage retrieved",
            dataset=dataset_id,
            nodes=len(nodes),
            edges=len(visited_edges),
        )

        return graph

    def analyze_impact(self, dataset_id: str) -> Dict[str, Any]:
        """
        Analyze impact of changes to a dataset.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Impact analysis
        """
        # Get downstream lineage
        downstream = self.get_downstream_lineage(dataset_id, max_depth=10)

        # Count affected datasets
        affected_datasets = [
            n.node_id for n in downstream.nodes if n.node_type == "dataset"
        ]

        # Group by depth
        depth_map: Dict[int, List[str]] = {}
        queue = [(dataset_id, 0)]
        visited = set()

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited:
                continue

            visited.add(current_id)

            if depth not in depth_map:
                depth_map[depth] = []
            depth_map[depth].append(current_id)

            # Find children
            for edge in self.edges:
                if edge.source_id == current_id:
                    queue.append((edge.target_id, depth + 1))

        return {
            "source_dataset": dataset_id,
            "total_affected": len(affected_datasets),
            "affected_datasets": affected_datasets,
            "max_depth": max(depth_map.keys()) if depth_map else 0,
            "by_depth": depth_map,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_lineage_path(
        self,
        source_id: str,
        target_id: str,
    ) -> Optional[List[str]]:
        """
        Find lineage path between two datasets.

        Args:
            source_id: Source dataset ID
            target_id: Target dataset ID

        Returns:
            Path of dataset IDs or None if no path exists
        """
        # BFS to find shortest path
        queue = [(source_id, [source_id])]
        visited = set()

        while queue:
            current_id, path = queue.pop(0)

            if current_id == target_id:
                return path

            if current_id in visited:
                continue

            visited.add(current_id)

            # Find neighbors
            for edge in self.edges:
                if edge.source_id == current_id:
                    new_path = path + [edge.target_id]
                    queue.append((edge.target_id, new_path))

        return None

    def close(self):
        """Close connections."""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j connection closed")
