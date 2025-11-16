"""LLM client wrapper for consistent AI integration."""

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import time


@dataclass
class LLMResponse:
    """LLM response wrapper."""

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    response_time_ms: float


class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        provider: str = "openai",
    ):
        """Initialize LLM client.

        Args:
            api_key: API key for LLM provider
            model: Model name
            temperature: Generation temperature (0-1)
            max_tokens: Maximum tokens to generate
            provider: Provider name (openai, anthropic, etc.)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider

        # Initialize provider-specific client
        self._init_client()

    def _init_client(self):
        """Initialize provider-specific client."""
        if self.provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional provider-specific arguments

        Returns:
            Generated text content
        """
        start_time = time.time()

        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs,
            )

            content = response.choices[0].message.content
            return content

        raise ValueError(f"Unsupported provider: {self.provider}")

    def generate_completion(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate completion from prompt.

        Args:
            prompt: Text prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional provider-specific arguments

        Returns:
            Generated text
        """
        messages = [{"role": "user", "content": prompt}]
        return self.generate_chat(messages, temperature, max_tokens, **kwargs)

    def generate_with_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate with detailed response metadata.

        Args:
            messages: List of message dicts
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional arguments

        Returns:
            LLMResponse with metadata
        """
        start_time = time.time()

        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs,
            )

            response_time = (time.time() - start_time) * 1000

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=response.choices[0].finish_reason,
                response_time_ms=response_time,
            )

        raise ValueError(f"Unsupported provider: {self.provider}")

    def generate_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-ada-002",
    ) -> List[List[float]]:
        """Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Embedding model name

        Returns:
            List of embedding vectors
        """
        if self.provider == "openai":
            response = self.client.embeddings.create(
                model=model,
                input=texts,
            )

            return [item.embedding for item in response.data]

        raise ValueError(f"Unsupported provider: {self.provider}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text (approximate).

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count
        """
        # Simple approximation: ~4 characters per token
        return len(text) // 4

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to maximum tokens.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens

        Returns:
            Truncated text
        """
        estimated_chars = max_tokens * 4
        if len(text) <= estimated_chars:
            return text

        return text[:estimated_chars] + "..."
