# DataForge AI Core Library

GenAI and LLM utilities for the DataForge AI Platform.

## Features

- **LLM Clients**: Unified interface for xAI Grok, OpenAI, Anthropic Claude
- **Embeddings**: Sentence transformers and OpenAI embeddings
- **RAG Pipeline**: Retrieval-augmented generation components
- **Prompt Templates**: Reusable prompts for common data tasks

## Installation

```bash
pip install dataforge-ai-core
```

## Usage

### LLM Clients

```python
from dataforge_ai_core.llm_clients import GrokClient, OpenAIClient

# Use xAI Grok
grok = GrokClient(api_key="your-xai-key")
response = grok.generate("Explain data normalization")

# Use OpenAI
openai = OpenAIClient(api_key="your-openai-key")
response = openai.generate("Write a SQL query to find top customers")
```

### Embeddings

```python
from dataforge_ai_core.embeddings import SentenceTransformerEmbeddings

embedder = SentenceTransformerEmbeddings()
embedding = embedder.embed_text("This is a sample document")
```

### RAG Pipeline

```python
from dataforge_ai_core.rag import RAGPipeline

rag = RAGPipeline(
    embedder=embedder,
    llm_client=grok,
    vector_store_path="./vectors"
)

# Index documents
rag.index_documents(["doc1.txt", "doc2.txt"])

# Query
response = rag.query("How do I configure Airflow?")
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```
