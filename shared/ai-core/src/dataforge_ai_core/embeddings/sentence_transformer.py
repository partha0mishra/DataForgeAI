"""Sentence Transformer embeddings implementation."""

from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from dataforge_common.logging import get_logger


class SentenceTransformerEmbeddings:
    """
    Sentence Transformer embeddings.

    Provides text embeddings using sentence-transformers models.

    Example:
        embedder = SentenceTransformerEmbeddings()

        # Embed single text
        embedding = embedder.embed_text("This is a sample document")

        # Embed multiple texts
        embeddings = embedder.embed_texts([
            "First document",
            "Second document"
        ])
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embeddings model.

        Args:
            model_name: Sentence transformers model name
        """
        self.model_name = model_name
        self.logger = get_logger(__name__, model=model_name)

        self.logger.info("Loading embedding model", model=model_name)
        self.model = SentenceTransformer(model_name)

        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self.logger.info(
            "Model loaded",
            model=model_name,
            embedding_dim=self.embedding_dim
        )

    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed single text.

        Args:
            text: Text to embed

        Returns:
            numpy array: Text embedding vector
        """
        self.logger.debug("Embedding text", length=len(text))

        embedding = self.model.encode(text, convert_to_numpy=True)

        return embedding

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for encoding

        Returns:
            numpy array: Matrix of embeddings (n_texts, embedding_dim)
        """
        self.logger.info(
            "Embedding texts",
            count=len(texts),
            batch_size=batch_size
        )

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100
        )

        self.logger.info(
            "Embeddings complete",
            count=len(texts),
            shape=embeddings.shape
        )

        return embeddings

    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            float: Cosine similarity score (0-1)
        """
        emb1 = self.embed_text(text1)
        emb2 = self.embed_text(text2)

        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (
            np.linalg.norm(emb1) * np.linalg.norm(emb2)
        )

        return float(similarity)
