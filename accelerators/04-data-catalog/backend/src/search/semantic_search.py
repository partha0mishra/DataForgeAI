"""Semantic search engine for data catalog."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from dataforge_ai_core.embeddings import SentenceTransformerEmbeddings
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Search result."""

    dataset_id: str
    name: str
    description: str
    score: float
    metadata: Dict[str, Any]
    matched_fields: List[str]


class SemanticSearchEngine:
    """
    Semantic search engine for data catalog.

    Combines:
    - Keyword search
    - Vector similarity search
    - Metadata filtering

    Example:
        search = SemanticSearchEngine()

        # Index datasets
        search.index_dataset(
            dataset_id="customers",
            name="Customer Profiles",
            description="Customer demographics and contact info",
            metadata={"tags": ["customer", "pii"]}
        )

        # Search
        results = search.search(
            query="customer contact information",
            top_k=10
        )

        for result in results:
            print(f"{result.name}: {result.score:.2f}")
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        elasticsearch_host: Optional[str] = None,
    ):
        """
        Initialize semantic search engine.

        Args:
            embedding_model: Sentence transformer model
            elasticsearch_host: Elasticsearch host (optional)
        """
        self.embedding_model = embedding_model
        self.elasticsearch_host = elasticsearch_host
        self.logger = logger

        # Initialize embeddings
        self.embedder = SentenceTransformerEmbeddings(model_name=embedding_model)

        # In-memory storage (replace with Elasticsearch)
        self.indexed_datasets: Dict[str, Dict[str, Any]] = {}
        self.embeddings: Optional[np.ndarray] = None
        self.dataset_ids: List[str] = []

        self.logger.info(
            "Semantic search engine initialized",
            embedding_model=embedding_model,
        )

    def index_dataset(
        self,
        dataset_id: str,
        name: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
    ) -> None:
        """
        Index a dataset for search.

        Args:
            dataset_id: Dataset identifier
            name: Dataset name
            description: Dataset description
            metadata: Additional metadata
            columns: Column names
        """
        # Build searchable text
        text_parts = [name, description]

        if columns:
            text_parts.append(" ".join(columns))

        if metadata and "tags" in metadata:
            text_parts.append(" ".join(metadata["tags"]))

        searchable_text = " ".join(text_parts)

        # Store dataset
        self.indexed_datasets[dataset_id] = {
            "dataset_id": dataset_id,
            "name": name,
            "description": description,
            "metadata": metadata or {},
            "columns": columns or [],
            "searchable_text": searchable_text,
        }

        # Regenerate embeddings
        self._rebuild_embeddings()

        self.logger.debug("Dataset indexed", dataset_id=dataset_id)

    def _rebuild_embeddings(self) -> None:
        """Rebuild embeddings for all indexed datasets."""
        if not self.indexed_datasets:
            self.embeddings = None
            self.dataset_ids = []
            return

        # Extract texts
        texts = []
        self.dataset_ids = []

        for dataset_id, data in self.indexed_datasets.items():
            texts.append(data["searchable_text"])
            self.dataset_ids.append(dataset_id)

        # Generate embeddings
        self.embeddings = self.embedder.embed_texts(texts)

        self.logger.debug(
            "Embeddings rebuilt",
            datasets=len(self.indexed_datasets),
            embedding_dim=self.embeddings.shape[1],
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        hybrid_alpha: float = 0.5,
    ) -> List[SearchResult]:
        """
        Search datasets using hybrid search.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Metadata filters
            hybrid_alpha: Balance between semantic (1.0) and keyword (0.0) search

        Returns:
            List of search results
        """
        if not self.indexed_datasets:
            return []

        # Semantic search
        semantic_scores = self._semantic_search(query, top_k * 2)

        # Keyword search
        keyword_scores = self._keyword_search(query, top_k * 2)

        # Combine scores
        combined_scores: Dict[str, float] = {}

        for dataset_id, score in semantic_scores.items():
            combined_scores[dataset_id] = score * hybrid_alpha

        for dataset_id, score in keyword_scores.items():
            combined_scores[dataset_id] = (
                combined_scores.get(dataset_id, 0) + score * (1 - hybrid_alpha)
            )

        # Apply filters
        if filters:
            combined_scores = self._apply_filters(combined_scores, filters)

        # Sort by score
        sorted_results = sorted(
            combined_scores.items(), key=lambda x: x[1], reverse=True
        )[:top_k]

        # Build results
        results = []
        for dataset_id, score in sorted_results:
            data = self.indexed_datasets[dataset_id]

            # Identify matched fields
            matched_fields = self._identify_matched_fields(query, data)

            result = SearchResult(
                dataset_id=dataset_id,
                name=data["name"],
                description=data["description"],
                score=score,
                metadata=data["metadata"],
                matched_fields=matched_fields,
            )
            results.append(result)

        self.logger.info("Search completed", query=query[:50], results=len(results))

        return results

    def _semantic_search(self, query: str, top_k: int) -> Dict[str, float]:
        """Perform semantic search using embeddings."""
        if self.embeddings is None:
            return {}

        # Generate query embedding
        query_embedding = self.embedder.embed_text(query)

        # Calculate cosine similarity
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        # Get top-k
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        # Build results
        scores = {}
        for idx in top_indices:
            dataset_id = self.dataset_ids[idx]
            scores[dataset_id] = float(similarities[idx])

        return scores

    def _keyword_search(self, query: str, top_k: int) -> Dict[str, float]:
        """Perform keyword-based search."""
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scores = {}

        for dataset_id, data in self.indexed_datasets.items():
            searchable_text = data["searchable_text"].lower()

            # Calculate term frequency score
            term_count = sum(1 for term in query_terms if term in searchable_text)

            if term_count > 0:
                # Normalize by query length
                score = term_count / len(query_terms)

                # Boost if exact phrase match
                if query_lower in searchable_text:
                    score *= 1.5

                # Boost if match in name
                if query_lower in data["name"].lower():
                    score *= 2.0

                scores[dataset_id] = score

        return scores

    def _apply_filters(
        self,
        scores: Dict[str, float],
        filters: Dict[str, Any],
    ) -> Dict[str, float]:
        """Apply metadata filters to search results."""
        filtered_scores = {}

        for dataset_id, score in scores.items():
            data = self.indexed_datasets[dataset_id]
            metadata = data["metadata"]

            # Check filters
            passes_filters = True

            if "tags" in filters:
                filter_tags = set(filters["tags"])
                dataset_tags = set(metadata.get("tags", []))
                if not filter_tags.intersection(dataset_tags):
                    passes_filters = False

            if "owner" in filters:
                if metadata.get("owner") != filters["owner"]:
                    passes_filters = False

            if "dataset_type" in filters:
                if metadata.get("dataset_type") != filters["dataset_type"]:
                    passes_filters = False

            if passes_filters:
                filtered_scores[dataset_id] = score

        return filtered_scores

    def _identify_matched_fields(
        self,
        query: str,
        data: Dict[str, Any],
    ) -> List[str]:
        """Identify which fields matched the query."""
        query_lower = query.lower()
        matched = []

        if query_lower in data["name"].lower():
            matched.append("name")

        if query_lower in data["description"].lower():
            matched.append("description")

        if any(query_lower in col.lower() for col in data["columns"]):
            matched.append("columns")

        tags = data["metadata"].get("tags", [])
        if any(query_lower in tag.lower() for tag in tags):
            matched.append("tags")

        return matched

    def remove_dataset(self, dataset_id: str) -> None:
        """Remove dataset from index."""
        if dataset_id in self.indexed_datasets:
            del self.indexed_datasets[dataset_id]
            self._rebuild_embeddings()

            self.logger.debug("Dataset removed from index", dataset_id=dataset_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            "total_indexed": len(self.indexed_datasets),
            "embedding_model": self.embedding_model,
            "embedding_dimension": (
                self.embeddings.shape[1] if self.embeddings is not None else 0
            ),
        }
