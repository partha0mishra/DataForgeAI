"""xAI Grok client implementation."""

from typing import Any, Dict, List, Optional

import requests

from dataforge_ai_core.llm_clients.base import BaseLLMClient


class GrokClient(BaseLLMClient):
    """
    xAI Grok LLM client.

    Example:
        client = GrokClient(api_key="your-xai-key")

        response = client.generate("Explain machine learning")

        # Or use chat
        response = client.generate_chat([
            {"role": "user", "content": "What is a data lake?"}
        ])
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "grok-beta",
        api_base_url: str = "https://api.x.ai/v1",
        **kwargs: Any
    ):
        """
        Initialize Grok client.

        Args:
            api_key: xAI API key
            model_name: Model name (grok-beta, etc.)
            api_base_url: API base URL
            **kwargs: Additional options
        """
        super().__init__(model_name=model_name, api_key=api_key, **kwargs)

        self.api_base_url = api_base_url

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
            "Generating completion with Grok",
            model=self.model_name,
            prompt_length=len(prompt)
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        response = requests.post(
            f"{self.api_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        generated_text = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)

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
            "Generating chat completion with Grok",
            model=self.model_name,
            num_messages=len(messages)
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        response = requests.post(
            f"{self.api_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        generated_text = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)

        prompt = str(messages)
        self._log_generation(prompt, generated_text, tokens_used)

        return generated_text
