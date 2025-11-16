"""Base LLM client interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.

    Provides a unified interface for different LLM providers.
    """

    def __init__(self, model_name: str, api_key: str, **kwargs: Any):
        """
        Initialize LLM client.

        Args:
            model_name: Name of the model to use
            api_key: API key for authentication
            **kwargs: Additional provider-specific options
        """
        self.model_name = model_name
        self.api_key = api_key
        self.config = kwargs
        self.logger = get_logger(__name__, model=model_name)

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs: Any
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Additional generation parameters

        Returns:
            str: Generated text
        """
        pass

    @abstractmethod
    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs: Any
    ) -> str:
        """
        Generate chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            str: Generated response
        """
        pass

    def _log_generation(
        self,
        prompt: str,
        response: str,
        tokens_used: int = 0
    ) -> None:
        """Log generation details."""
        self.logger.info(
            "LLM generation",
            model=self.model_name,
            prompt_length=len(prompt),
            response_length=len(response),
            tokens=tokens_used
        )

        increment_counter(
            "llm_generations_total",
            labels={"model": self.model_name}
        )

        if tokens_used > 0:
            increment_counter(
                "llm_tokens_used",
                value=tokens_used,
                labels={"model": self.model_name}
            )
