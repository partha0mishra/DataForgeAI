"""DataForge AI Core - GenAI and LLM utilities."""

__version__ = "0.1.0"

from dataforge_ai_core.llm_clients.base import BaseLLMClient
from dataforge_ai_core.llm_clients.openai import OpenAIClient

__all__ = ["BaseLLMClient", "OpenAIClient"]
