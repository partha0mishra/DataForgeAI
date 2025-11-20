"""
RAG (Retrieval-Augmented Generation) capabilities for improving pipeline generation.
"""

import logging
from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from .config import settings
from .database import db_manager
from .models import SavedGeneration

logger = logging.getLogger(__name__)


class RAGManager:
    """Manage RAG operations using ChromaDB."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "pipeline_generations",
    ):
        self.persist_directory = persist_directory or settings.chroma_persist_directory

        # Ensure directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )

        # Use default embedding function (all-MiniLM-L6-v2)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Pipeline generation history for RAG"},
        )

        logger.info(f"RAG initialized with {self.collection.count()} existing generations")

    def add_generation(self, generation: SavedGeneration) -> None:
        """Add a generation to the RAG collection.

        Args:
            generation: Saved generation to add
        """
        try:
            # Create document text from prompt and pipeline details
            pipeline_output = generation.pipeline_output
            document = f"""
Prompt: {generation.prompt}

Pipeline Name: {pipeline_output.get('pipeline_name', 'N/A')}
Platform: {pipeline_output.get('platform', 'N/A')}
Orchestrator: {pipeline_output.get('orchestrator', 'N/A')}
Description: {pipeline_output.get('description', 'N/A')}

Architecture Notes: {pipeline_output.get('architecture_notes', 'N/A')}
            """.strip()

            # Create metadata
            metadata = {
                "generation_id": str(generation.id),
                "platform": pipeline_output.get("platform", "unknown"),
                "orchestrator": pipeline_output.get("orchestrator", "unknown"),
                "rating": generation.user_rating or 0,
                "created_at": generation.created_at.isoformat(),
            }

            # Add to collection
            self.collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[f"gen_{generation.id}"],
            )

            logger.info(f"Added generation {generation.id} to RAG collection")

        except Exception as e:
            logger.error(f"Failed to add generation to RAG: {e}")

    def search_similar(
        self,
        query: str,
        n_results: int = 3,
        min_rating: Optional[int] = None,
        platform: Optional[str] = None,
    ) -> List[dict]:
        """Search for similar generations.

        Args:
            query: Search query (user prompt)
            n_results: Number of results to return
            min_rating: Minimum rating filter
            platform: Platform filter

        Returns:
            List of similar generations with metadata
        """
        try:
            # Build where clause for filtering
            where = {}
            if min_rating is not None:
                where["rating"] = {"$gte": min_rating}
            if platform:
                where["platform"] = platform

            # Search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where if where else None,
            )

            # Format results
            similar_generations = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    similar_generations.append(
                        {
                            "document": doc,
                            "metadata": results["metadatas"][0][i],
                            "distance": results["distances"][0][i] if results.get("distances") else None,
                        }
                    )

            logger.info(f"Found {len(similar_generations)} similar generations")
            return similar_generations

        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []

    def sync_from_database(self, min_rating: int = 4) -> int:
        """Sync highly-rated generations from database to RAG.

        Args:
            min_rating: Minimum rating to include

        Returns:
            Number of generations added
        """
        try:
            # Get highly-rated generations from database
            generations = db_manager.get_highly_rated_generations(min_rating=min_rating, limit=100)

            added = 0
            for generation in generations:
                # Check if already in collection
                try:
                    self.collection.get(ids=[f"gen_{generation.id}"])
                    # Already exists, skip
                    continue
                except Exception:
                    # Doesn't exist, add it
                    self.add_generation(generation)
                    added += 1

            logger.info(f"Synced {added} new generations to RAG")
            return added

        except Exception as e:
            logger.error(f"Failed to sync from database: {e}")
            return 0

    def get_stats(self) -> dict:
        """Get RAG collection statistics.

        Returns:
            Dictionary with stats
        """
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name,
                "persist_directory": self.persist_directory,
            }
        except Exception as e:
            logger.error(f"Failed to get RAG stats: {e}")
            return {"error": str(e)}


# Global RAG manager instance (lazy initialization)
_rag_manager: Optional[RAGManager] = None


def get_rag_manager() -> RAGManager:
    """Get or create the global RAG manager instance.

    Returns:
        RAG manager instance
    """
    global _rag_manager
    if _rag_manager is None:
        _rag_manager = RAGManager()
    return _rag_manager
