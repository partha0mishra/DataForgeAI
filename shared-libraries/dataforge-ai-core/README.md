# DataForge AI Core

AI/ML utilities and LLM integration for DataForge AI Platform.

## Installation

```bash
pip install -e .
```

## Components

- **llm.py** - Unified LLM client supporting OpenAI (extensible to other providers)

## Usage

```python
from dataforge_ai_core.llm import LLMClient
import os

# Initialize client
client = LLMClient(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4",
    temperature=0.7,
)

# Generate chat completion
response = client.generate_chat(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain machine learning in simple terms."},
    ]
)
print(response)

# Generate from simple prompt
response = client.generate_completion("Write a haiku about data")
print(response)

# Get detailed response with metadata
detailed = client.generate_with_response(
    messages=[{"role": "user", "content": "Hello!"}]
)
print(f"Model: {detailed.model}")
print(f"Tokens: {detailed.usage['total_tokens']}")
print(f"Time: {detailed.response_time_ms}ms")

# Generate embeddings
embeddings = client.generate_embeddings(
    texts=["Hello world", "Machine learning"]
)
print(f"Embedding dimension: {len(embeddings[0])}")
```

## Supported Providers

- ✅ OpenAI (GPT-4, GPT-3.5-turbo, embeddings)
- 🔜 Anthropic Claude (coming soon)
- 🔜 Cohere (coming soon)

## License

MIT
