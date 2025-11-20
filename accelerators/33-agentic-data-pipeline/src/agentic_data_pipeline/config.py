"""
Configuration management for the application.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and config files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # LLM Provider
    llm_provider: str = Field(default="xai", description="LLM provider to use")

    # xAI / Grok
    xai_api_key: Optional[str] = Field(default=None, description="xAI API key")
    xai_model: str = Field(default="grok-beta", description="xAI model name")
    xai_base_url: str = Field(default="https://api.x.ai/v1", description="xAI base URL")

    # Azure OpenAI
    azure_openai_api_key: Optional[str] = Field(default=None, description="Azure OpenAI API key")
    azure_openai_endpoint: Optional[str] = Field(
        default=None, description="Azure OpenAI endpoint"
    )
    azure_openai_deployment: str = Field(
        default="gpt-4o", description="Azure OpenAI deployment name"
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview", description="Azure OpenAI API version"
    )

    # AWS Bedrock
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(
        default=None, description="AWS secret access key"
    )
    aws_region: str = Field(default="us-east-1", description="AWS region")
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0", description="Bedrock model ID"
    )

    # Local LLM
    local_llm_base_url: str = Field(
        default="http://localhost:1234/v1", description="Local LLM base URL"
    )
    local_llm_model: str = Field(default="local-model", description="Local LLM model name")
    local_llm_api_key: str = Field(default="not-needed", description="Local LLM API key")

    # Application
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Log level")
    database_url: str = Field(
        default="sqlite:///./data/pipelines.db", description="Database URL"
    )

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="API auto-reload")

    # Streamlit
    streamlit_server_port: int = Field(default=8501, description="Streamlit server port")
    streamlit_server_address: str = Field(
        default="0.0.0.0", description="Streamlit server address"
    )

    # RAG
    chroma_persist_directory: str = Field(
        default="./data/chroma", description="ChromaDB persist directory"
    )
    enable_rag: bool = Field(default=True, description="Enable RAG")

    # Generation
    default_temperature: float = Field(default=0.0, description="Default temperature")
    default_max_tokens: int = Field(default=8000, description="Default max tokens")
    enable_few_shot: bool = Field(default=True, description="Enable few-shot examples")

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for the specified provider."""
        if provider == "xai":
            return self.xai_api_key
        elif provider == "azure_openai":
            return self.azure_openai_api_key
        elif provider == "aws_bedrock":
            return None  # Bedrock uses AWS credentials
        elif provider == "local":
            return self.local_llm_api_key
        return None


class ConfigLoader:
    """Load configuration from YAML file."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self._config = yaml.safe_load(f)
        else:
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def get_llm_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get LLM configuration for the specified provider."""
        provider = provider or self.get("llm.provider", "xai")
        llm_config = self.get("llm", {})
        provider_config = llm_config.get("providers", {}).get(provider, {})

        return {
            "provider": provider,
            "temperature": llm_config.get("temperature", 0.0),
            "max_tokens": llm_config.get("max_tokens", 8000),
            "timeout": llm_config.get("timeout", 120),
            "max_retries": llm_config.get("max_retries", 3),
            **provider_config,
        }

    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return self._config


# Global settings instance
settings = Settings()

# Global config loader instance
config_loader = ConfigLoader()
