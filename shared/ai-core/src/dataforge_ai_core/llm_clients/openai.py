"""OpenAI LLM client implementation."""

from typing import Any, Dict, List, Optional

from openai import OpenAI

from dataforge_ai_core.llm_clients.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """
    OpenAI LLM client.

    Supports GPT-4, GPT-3.5-turbo, and other OpenAI models.

    Example:
        client = OpenAIClient(
            api_key="your-openai-key",
            model_name="gpt-4"
        )

        response = client.generate("Explain data pipelines")

        # Or use chat
        response = client.generate_chat([
            {"role": "system", "content": "You are a data engineer"},
            {"role": "user", "content": "How do I optimize Spark jobs?"}
        ])
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4",
        **kwargs: Any
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model_name: Model name (gpt-4, gpt-3.5-turbo, etc.)
            **kwargs: Additional OpenAI options
        """
        super().__init__(model_name=model_name, api_key=api_key, **kwargs)

        self.client = OpenAI(api_key=api_key)

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
            **kwargs: Additional parameters

        Returns:
            str: Generated text
        """
        self.logger.debug(
            "Generating completion",
            model=self.model_name,
            prompt_length=len(prompt)
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        generated_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        self._log_generation(prompt, generated_text, tokens_used)

        return generated_text

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
        self.logger.debug(
            "Generating chat completion",
            model=self.model_name,
            num_messages=len(messages)
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        generated_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        prompt = str(messages)
        self._log_generation(prompt, generated_text, tokens_used)

        return generated_text

    def generate_structured(
        self,
        prompt: str,
        response_format: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output.

        Args:
            prompt: Input prompt
            response_format: JSON schema for response
            **kwargs: Additional parameters

        Returns:
            dict: Parsed JSON response
        """
        import json

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            **kwargs
        )

        generated_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        self._log_generation(prompt, generated_text, tokens_used)

        return json.loads(generated_text)
