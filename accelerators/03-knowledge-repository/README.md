# Knowledge Repository with RAG

AI-powered knowledge management system with Retrieval-Augmented Generation (RAG) for intelligent question answering.

## Features

- **Document Indexing**: Process and index documents from various formats (Markdown, text, code, JSON, YAML)
- **Intelligent Chunking**: Multiple strategies (fixed, recursive) that respect document structure
- **Vector Search**: Semantic search using sentence transformers embeddings
- **RAG-based Q&A**: Answer questions using retrieved context and LLM generation
- **Multiple LLM Support**: OpenAI GPT-4, GPT-3.5-turbo (extensible to other providers)
- **REST API**: FastAPI-based API for indexing and querying
- **Audit Trail**: Complete logging and monitoring integration

## Quick Start

### 1. Install Dependencies

```bash
cd accelerators/03-knowledge-repository
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-api-key"
export DATAFORGE_ENV="development"
```

### 3. Run Example

```bash
python examples/rag_example.py
```

This will:
- Create sample documentation files
- Index documents with chunking
- Ask questions using RAG
- Display answers with sources and confidence scores

### 4. Start API Server

```bash
cd backend
uvicorn src.api.main:app --reload --port 8002
```

API will be available at: http://localhost:8002

## API Endpoints

### Index a File

```bash
curl -X POST "http://localhost:8002/index/file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@docs/guide.md" \
  -F "user=admin"
```

### Ask a Question (RAG)

```bash
curl -X POST "http://localhost:8002/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I create an Airflow DAG?",
    "top_k": 5,
    "temperature": 0.7
  }'
```

Response:
```json
{
  "question": "How do I create an Airflow DAG?",
  "answer": "To create a DAG in Airflow, import the DAG class...",
  "sources": [
    {
      "content": "[Source 1: airflow_guide.md] A DAG is...",
      "metadata": {
        "source": "/path/to/airflow_guide.md",
        "filename": "airflow_guide.md",
        "chunk_index": 0
      },
      "score": 0.89
    }
  ],
  "confidence": 0.85,
  "timestamp": "2025-11-15T10:30:00Z"
}
```

### Semantic Search

```bash
curl -X POST "http://localhost:8002/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "data quality validation",
    "top_k": 10
  }'
```

### Get Index Status

```bash
curl http://localhost:8002/index/status
```

Response:
```json
{
  "total_documents": 25,
  "total_chunks": 143,
  "last_updated": "2025-11-15T10:30:00Z"
}
```

## Architecture

### Document Processing Pipeline

```
Documents → Extract Text → Chunk Text → Generate Embeddings → Vector Store
                ↓              ↓              ↓                    ↓
         (PDF, MD, TXT)   (Recursive)   (Sentence-BERT)      (In-Memory)
```

### RAG Query Pipeline

```
Question → Query Embedding → Vector Search → Context Building → LLM Generation → Answer
                                    ↓              ↓                  ↓
                            (Top-K Similar)  (Format Context)  (OpenAI GPT-4)
```

## Components

### 1. Document Processor (`backend/src/indexing/document_processor.py`)

Handles document processing and chunking:

```python
from indexing.document_processor import DocumentProcessor

processor = DocumentProcessor(
    chunk_size=512,
    chunk_overlap=50,
    chunk_strategy="recursive"
)

# Process single file
chunks = processor.process_file("./docs/guide.md")

# Process directory
chunks = processor.process_directory(
    "./docs",
    file_extensions=[".md", ".txt", ".py"],
    recursive=True
)
```

**Chunking Strategies:**
- **Fixed**: Simple fixed-size chunks with overlap
- **Recursive**: Respects paragraphs and sentences for better context

### 2. RAG Engine (`backend/src/retrieval/rag_engine.py`)

Combines retrieval and generation:

```python
from retrieval.rag_engine import RAGEngine

rag = RAGEngine(
    llm_provider="openai",
    llm_api_key="your-key",
    embedding_model="all-MiniLM-L6-v2",
    top_k=5
)

# Index documents
documents = [chunk.to_dict() for chunk in chunks]
rag.index_documents(documents)

# Query
response = rag.query("How do I deploy to production?")
print(response.answer)
print(f"Confidence: {response.confidence:.2%}")
for source in response.sources:
    print(f"  - {source['metadata']['filename']}")
```

### 3. API Server (`backend/src/api/main.py`)

FastAPI application with endpoints for indexing and querying.

## Configuration

### Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4  # or gpt-3.5-turbo

# Embedding Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2

# API Configuration
KNOWLEDGE_API_PORT=8002
KNOWLEDGE_API_HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
DATAFORGE_ENV=development
```

### Chunking Configuration

Adjust chunking parameters based on your use case:

```python
# For short documents (tweets, chat messages)
processor = DocumentProcessor(chunk_size=256, chunk_overlap=25)

# For medium documents (articles, documentation)
processor = DocumentProcessor(chunk_size=512, chunk_overlap=50)

# For long documents (books, research papers)
processor = DocumentProcessor(chunk_size=1024, chunk_overlap=100)
```

## Supported File Types

- **Markdown**: `.md`
- **Text**: `.txt`
- **Code**: `.py`, `.js`, `.java`, `.cpp`, `.c`
- **Configuration**: `.json`, `.yaml`, `.yml`
- **ReStructuredText**: `.rst`

## Example Use Cases

### 1. Technical Documentation Q&A

Index your project documentation and allow developers to ask questions:

```python
processor.process_directory("./docs")
response = rag.query("How do I configure authentication?")
```

### 2. Code Search and Understanding

Index your codebase for semantic code search:

```python
processor.process_directory("./src", file_extensions=[".py", ".js"])
response = rag.query("Where is the database connection handled?")
```

### 3. Knowledge Base for Support

Build a customer support knowledge base:

```python
processor.process_directory("./kb/support")
response = rag.query("How do I reset my password?")
```

## Monitoring

The API includes built-in monitoring with Prometheus metrics:

- `rag_query_duration`: Query execution time
- `rag_queries_total`: Total number of queries
- `files_indexed_total`: Total files indexed
- `index_file_duration`: File indexing time

Access metrics at: http://localhost:8002/metrics

## Integration with Other Accelerators

### With Pipeline Automation (Accelerator 1)

Schedule periodic indexing of new documents:

```python
# Airflow DAG
from airflow.operators.python import PythonOperator

def index_new_docs():
    processor.process_directory("/data/new_docs")

index_task = PythonOperator(
    task_id="index_knowledge_base",
    python_callable=index_new_docs,
    dag=dag
)
```

### With Data Quality (Accelerator 2)

Index quality check documentation:

```python
processor.process_directory("./quality_rules")
response = rag.query("What are the validation rules for customer data?")
```

## Deployment

### Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### Docker

```bash
docker build -t knowledge-repository:latest .
docker run -p 8002:8002 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  knowledge-repository:latest
```

## Testing

Run tests:

```bash
pytest tests/ -v
```

## Troubleshooting

### Issue: "No documents indexed"

Make sure to index documents before querying:
```python
processor.process_directory("./docs")
rag.index_documents(documents)
```

### Issue: "OpenAI API key not found"

Set the environment variable:
```bash
export OPENAI_API_KEY="your-key"
```

### Issue: Poor answer quality

Try:
1. Increase `top_k` to retrieve more context
2. Adjust `chunk_size` for better context boundaries
3. Use recursive chunking strategy
4. Fine-tune temperature (lower = more focused)

## License

Part of DataForge AI Platform - MIT License
