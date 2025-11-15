"""RAG (Retrieval-Augmented Generation) engine."""

from dataclasses import dataclass
from typing import List, Optional

from dataforge_ai_core.embeddings import SentenceTransformerEmbeddings
from dataforge_ai_core.llm_clients import OpenAIClient
from dataforge_common.logging import get_logger
from dataforge_common.monitoring import track_duration

logger = get_logger(__name__)


@dataclass
class RAGResponse:
    """RAG query response."""

    question: str
    answer: str
    sources: List[dict]
    confidence: float
    metadata: dict


class RAGEngine:
    """
    Retrieval-Augmented Generation engine.

    Combines vector search with LLM generation to answer questions
    using context from the knowledge base.

    Example:
        rag = RAGEngine(
            vector_store_path="./vectors",
            llm_api_key="your-key"
        )

        response = rag.query("How do I deploy to Kubernetes?")
        print(response.answer)
        for source in response.sources:
            print(f"  - {source['filename']}")
    """

    def __init__(
        self,
        vector_store_path: str = "./vectors",
        llm_provider: str = "openai",
        llm_api_key: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        top_k: int = 5,
        temperature: float = 0.7,
    ):
        """
        Initialize RAG engine.

        Args:
            vector_store_path: Path to vector store
            llm_provider: LLM provider (openai, grok)
            llm_api_key: API key for LLM
            embedding_model: Embedding model name
            top_k: Number of documents to retrieve
            temperature: LLM temperature
        """
        self.vector_store_path = vector_store_path
        self.top_k = top_k
        self.temperature = temperature
        self.logger = logger

        # Initialize embeddings
        self.embedder = SentenceTransformerEmbeddings(model_name=embedding_model)

        # Initialize LLM
        if llm_provider == "openai":
            self.llm = OpenAIClient(api_key=llm_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        # In-memory document store (replace with actual vector DB)
        self.documents = []
        self.document_embeddings = None

        self.logger.info(
            "RAG engine initialized",
            llm_provider=llm_provider,
            embedding_model=embedding_model,
        )

    def index_documents(self, documents: List[dict]) -> None:
        """
        Index documents into vector store.

        Args:
            documents: List of document dicts with 'content' and 'metadata'
        """
        self.logger.info("Indexing documents", count=len(documents))

        self.documents = documents

        # Extract text content
        texts = [doc["content"] for doc in documents]

        # Generate embeddings
        self.document_embeddings = self.embedder.embed_texts(texts)

        self.logger.info(
            "Documents indexed",
            count=len(documents),
            embedding_dim=self.document_embeddings.shape[1],
        )

    @track_duration("rag_query_duration")
    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> RAGResponse:
        """
        Query the knowledge base using RAG.

        Args:
            question: User question
            top_k: Number of documents to retrieve (override default)
            temperature: LLM temperature (override default)

        Returns:
            RAGResponse: Answer with sources
        """
        top_k = top_k or self.top_k
        temperature = temperature or self.temperature

        self.logger.info("Processing RAG query", question=question[:100])

        # Step 1: Retrieve relevant documents
        relevant_docs = self._retrieve_documents(question, top_k)

        self.logger.debug(
            "Retrieved documents",
            count=len(relevant_docs),
        )

        # Step 2: Build context from documents
        context = self._build_context(relevant_docs)

        # Step 3: Generate answer using LLM
        answer = self._generate_answer(question, context, temperature)

        # Step 4: Calculate confidence (simple heuristic)
        confidence = self._calculate_confidence(relevant_docs)

        # Create response
        response = RAGResponse(
            question=question,
            answer=answer,
            sources=[
                {
                    "content": doc["content"][:200] + "...",
                    "metadata": doc["metadata"],
                    "score": doc["score"],
                }
                for doc in relevant_docs
            ],
            confidence=confidence,
            metadata={
                "top_k": top_k,
                "temperature": temperature,
                "context_length": len(context),
            },
        )

        self.logger.info(
            "RAG query complete",
            confidence=confidence,
            sources=len(relevant_docs),
        )

        return response

    def _retrieve_documents(self, query: str, top_k: int) -> List[dict]:
        """
        Retrieve most relevant documents using vector similarity.

        Args:
            query: Search query
            top_k: Number of documents to return

        Returns:
            List of relevant documents with scores
        """
        import numpy as np

        # Generate query embedding
        query_embedding = self.embedder.embed_text(query)

        # Calculate cosine similarity with all documents
        similarities = np.dot(self.document_embeddings, query_embedding) / (
            np.linalg.norm(self.document_embeddings, axis=1)
            * np.linalg.norm(query_embedding)
        )

        # Get top-k most similar documents
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        # Return documents with scores
        results = []
        for idx in top_indices:
            doc = self.documents[idx].copy()
            doc["score"] = float(similarities[idx])
            results.append(doc)

        return results

    def _build_context(self, documents: List[dict]) -> str:
        """
        Build context string from retrieved documents.

        Args:
            documents: Retrieved documents

        Returns:
            Context string for LLM
        """
        context_parts = []

        for i, doc in enumerate(documents, 1):
            source = doc["metadata"].get("filename", "Unknown")
            content = doc["content"]

            context_parts.append(f"[Source {i}: {source}]\n{content}\n")

        return "\n".join(context_parts)

    def _generate_answer(
        self,
        question: str,
        context: str,
        temperature: float,
    ) -> str:
        """
        Generate answer using LLM with context.

        Args:
            question: User question
            context: Retrieved context
            temperature: LLM temperature

        Returns:
            Generated answer
        """
        prompt = f"""Answer the following question based on the provided context.
If the answer cannot be found in the context, say "I don't have enough information to answer that question."

Context:
{context}

Question: {question}

Answer:"""

        answer = self.llm.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=500,
        )

        return answer.strip()

    def _calculate_confidence(self, documents: List[dict]) -> float:
        """
        Calculate confidence score for the answer.

        Simple heuristic based on retrieval scores.
        """
        if not documents:
            return 0.0

        # Average of top document scores
        avg_score = sum(doc["score"] for doc in documents) / len(documents)

        # Normalize to 0-1
        return min(1.0, avg_score)
