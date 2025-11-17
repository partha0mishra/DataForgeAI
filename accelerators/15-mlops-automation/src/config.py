"""Configuration management for MLOps accelerator."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_artifact_root: str = "s3://mlflow-artifacts"
    mlflow_s3_bucket: str = "mlflow-artifacts"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600
    
    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # API
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    log_level: str = "INFO"
    
    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    
    # Deployment
    deployment_namespace: str = "production"
    kubernetes_cluster_url: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
