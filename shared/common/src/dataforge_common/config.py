"""Configuration management for DataForge platform."""

import os
from enum import Enum
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    This class automatically loads configuration from:
    1. Environment variables
    2. .env file (if present)
    3. Default values

    Example:
        settings = Settings()
        print(settings.database_url)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Core Platform Settings
    dataforge_env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment",
    )
    log_level: str = Field(default="INFO", description="Logging level")
    secret_key: str = Field(
        default="changeme-in-production",
        description="Secret key for encryption",
    )
    timezone: str = Field(default="UTC", description="Application timezone")

    # Database Configuration
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="dataforge", description="PostgreSQL database")
    postgres_user: str = Field(default="dataforge", description="PostgreSQL user")
    postgres_password: str = Field(
        default="changeme", description="PostgreSQL password"
    )

    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")

    # GenAI Configuration
    xai_api_key: Optional[str] = Field(default=None, description="xAI API key")
    xai_api_base_url: str = Field(
        default="https://api.x.ai/v1", description="xAI API base URL"
    )
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key"
    )

    # AWS Configuration
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(
        default=None, description="AWS secret key"
    )
    aws_default_region: str = Field(default="us-east-1", description="AWS region")
    aws_s3_bucket: Optional[str] = Field(default=None, description="S3 bucket name")

    # Monitoring
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OpenTelemetry collector endpoint",
    )
    enable_monitoring: bool = Field(
        default=True, description="Enable monitoring/observability"
    )

    # Authentication
    jwt_secret_key: Optional[str] = Field(default=None, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(
        default=24, description="JWT token expiration in hours"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is acceptable."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper

    @property
    def database_url(self) -> str:
        """Generate PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.dataforge_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.dataforge_env == Environment.DEVELOPMENT

    def get_jwt_secret(self) -> str:
        """Get JWT secret key with fallback."""
        return self.jwt_secret_key or self.secret_key


# Global settings instance (singleton pattern)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance (singleton).

    Returns:
        Settings: Application configuration

    Example:
        settings = get_settings()
        db_url = settings.database_url
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Force reload of settings (useful for testing).

    Returns:
        Settings: Newly loaded application configuration
    """
    global _settings
    _settings = Settings()
    return _settings
