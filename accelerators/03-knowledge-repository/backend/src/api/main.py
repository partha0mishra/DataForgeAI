"""FastAPI application for Knowledge Repository."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration

# Import knowledge repository modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from indexing.document_processor import DocumentProcessor
from retrieval.rag_engine import RAGEngine

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DataForge Knowledge Repository API",
    description="API for knowledge management and RAG-based Q&A",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
document_processor = DocumentProcessor(chunk_size=512, chunk_overlap=50)
rag_engine = RAGEngine(llm_provider="openai")

# In-memory storage (replace with database in production)
indexed_documents = []


# Models
class QueryRequest(BaseModel):
    """RAG query request."""

    question: str
    top_k: int = 5
    temperature: float = 0.7


class QueryResponse(BaseModel):
    """RAG query response."""

    question: str
    answer: str
    sources: List[dict]
    confidence: float
    timestamp: str


class SearchRequest(BaseModel):
    """Semantic search request."""

    query: str
    top_k: int = 10


class IndexStatus(BaseModel):
    """Index status."""

    total_documents: int
    total_chunks: int
    last_updated: str


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DataForge Knowledge Repository API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    increment_counter("health_checks")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/index/file")
@track_duration("index_file_duration")
async def index_file(
    file: UploadFile = File(...),
    user: str = "system",
):
    """
    Index a single file.

    Upload a file to be indexed into the knowledge base.
    """
    logger.info("File upload for indexing", filename=file.filename, user=user)

    try:
        # Save uploaded file temporarily
        temp_path = Path(f"/tmp/{file.filename}")
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Process file
        chunks = document_processor.process_file(str(temp_path))

        # Convert chunks to documents
        documents = [chunk.to_dict() for chunk in chunks]

        # Add to indexed documents
        indexed_documents.extend(documents)

        # Re-index in RAG engine
        rag_engine.index_documents(indexed_documents)

        # Clean up
        temp_path.unlink()

        increment_counter("files_indexed")

        logger.info(
            "File indexed successfully",
            filename=file.filename,
            chunks=len(chunks),
        )

        return {
            "filename": file.filename,
            "chunks_created": len(chunks),
            "total_indexed": len(indexed_documents),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("File indexing failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
@track_duration("rag_query_duration")
async def rag_query(request: QueryRequest):
    """
    Answer question using RAG.

    Retrieves relevant context and generates an answer using LLM.
    """
    logger.info("RAG query received", question=request.question[:100])

    try:
        if not indexed_documents:
            raise HTTPException(
                status_code=400,
                detail="No documents indexed. Please index documents first.",
            )

        # Query RAG engine
        response = rag_engine.query(
            question=request.question,
            top_k=request.top_k,
            temperature=request.temperature,
        )

        increment_counter("rag_queries")

        logger.info(
            "RAG query complete",
            confidence=response.confidence,
            sources=len(response.sources),
        )

        return QueryResponse(
            question=response.question,
            answer=response.answer,
            sources=response.sources,
            confidence=response.confidence,
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error("RAG query failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
@track_duration("search_duration")
async def semantic_search(request: SearchRequest):
    """
    Semantic search across indexed documents.

    Returns most relevant documents without generating an answer.
    """
    logger.info("Search request", query=request.query[:100])

    try:
        if not indexed_documents:
            return {
                "results": [],
                "count": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Use RAG engine's retrieval (without answer generation)
        results = rag_engine._retrieve_documents(request.query, request.top_k)

        increment_counter("searches")

        logger.info("Search complete", results=len(results))

        return {
            "query": request.query,
            "results": results,
            "count": len(results),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Search failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/index/status", response_model=IndexStatus)
async def get_index_status():
    """Get index status and statistics."""
    # Count unique documents (by source)
    unique_sources = set(
        doc["metadata"].get("source", "unknown") for doc in indexed_documents
    )

    return IndexStatus(
        total_documents=len(unique_sources),
        total_chunks=len(indexed_documents),
        last_updated=datetime.utcnow().isoformat(),
    )


@app.delete("/index/clear")
async def clear_index():
    """Clear all indexed documents."""
    logger.warning("Clearing index")

    global indexed_documents
    indexed_documents = []

    return {
        "status": "cleared",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/metrics")
async def get_metrics():
    """Get knowledge repository metrics."""
    unique_sources = set(
        doc["metadata"].get("source", "unknown") for doc in indexed_documents
    )

    return {
        "index": {
            "total_documents": len(unique_sources),
            "total_chunks": len(indexed_documents),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
