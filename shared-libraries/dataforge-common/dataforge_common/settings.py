"""Pydantic settings for DataForge AI platform."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataForgeSettings(BaseSettings):
    """DataForge AI platform settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Environment
    environment: str = Field(default="development", alias="DATAFORGE_ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    # PostgreSQL Database
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="dataforge", alias="POSTGRES_USER")
    postgres_password: str = Field(default="dataforge", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="dataforge", alias="POSTGRES_DB")

    # Redis Cache
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    # JWT Authentication
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Security
    admin_password: str = Field(default="admin123", alias="ADMIN_PASSWORD")
    max_login_attempts: int = Field(default=5, alias="MAX_LOGIN_ATTEMPTS")
    login_lockout_duration: int = Field(default=900, alias="LOGIN_LOCKOUT_DURATION")

    # Kafka
    kafka_bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_security_protocol: str = Field(default="PLAINTEXT", alias="KAFKA_SECURITY_PROTOCOL")
    kafka_group_id: str = Field(default="dataforge-consumer-group", alias="KAFKA_GROUP_ID")

    # Monitoring
    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    grafana_port: int = Field(default=3000, alias="GRAFANA_PORT")

    # OpenTelemetry
    otel_exporter_otlp_endpoint: Optional[str] = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_service_name: str = Field(default="dataforge-ai", alias="OTEL_SERVICE_NAME")

    # GenAI API Keys
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    xai_api_key: Optional[str] = Field(default=None, alias="XAI_API_KEY")

    # Cloud Providers
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")

    azure_subscription_id: Optional[str] = Field(default=None, alias="AZURE_SUBSCRIPTION_ID")
    azure_tenant_id: Optional[str] = Field(default=None, alias="AZURE_TENANT_ID")

    gcp_project_id: Optional[str] = Field(default=None, alias="GCP_PROJECT_ID")
    gcp_credentials_path: Optional[str] = Field(default=None, alias="GOOGLE_APPLICATION_CREDENTIALS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    # Feature Flags
    enable_data_quality_checks: bool = Field(default=True, alias="ENABLE_DATA_QUALITY_CHECKS")
    enable_genai_features: bool = Field(default=True, alias="ENABLE_GENAI_FEATURES")
    enable_streaming: bool = Field(default=True, alias="ENABLE_STREAMING")

    @property
    def database_url(self) -> str:
        """Get PostgreSQL database URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        """Get async PostgreSQL database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() in ("production", "prod")

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() in ("development", "dev")


# Global settings instance
_settings: Optional[DataForgeSettings] = None


def get_settings() -> DataForgeSettings:
    """Get global settings instance.

    Returns:
        DataForge settings instance
    """
    global _settings
    if _settings is None:
        _settings = DataForgeSettings()
    return _settings


def reload_settings() -> DataForgeSettings:
    """Reload settings from environment.

    Returns:
        Fresh settings instance
    """
    global _settings
    _settings = DataForgeSettings()
    return _settings
