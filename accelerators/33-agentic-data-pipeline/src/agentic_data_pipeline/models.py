"""
Pydantic models for structured LLM output and configuration.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator


class Platform(str, Enum):
    """Supported data platforms."""

    DATABRICKS = "databricks"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    SYNAPSE = "synapse"
    REDSHIFT = "redshift"
    AWS_GLUE = "aws_glue"
    FABRIC = "fabric"


class Orchestrator(str, Enum):
    """Supported orchestration tools."""

    AIRFLOW = "airflow"
    DELTA_LIVE_TABLES = "delta_live_tables"
    DBT = "dbt"
    MAGE = "mage"
    PREFECT = "prefect"
    SNOWPARK = "snowpark"
    SYNAPSE_PIPELINE = "synapse_pipeline"


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    XAI = "xai"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    LOCAL = "local"


class GeneratedFile(BaseModel):
    """A single generated file in the pipeline."""

    path: str = Field(..., description="Relative path of the file")
    content: str = Field(..., description="Full content of the file")
    file_type: Optional[str] = Field(None, description="File type (python, sql, yaml, etc.)")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Ensure path doesn't start with /."""
        return v.lstrip("/")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is not empty."""
        if not v.strip():
            raise ValueError("File content cannot be empty")
        return v


class PipelineOutput(BaseModel):
    """Structured output from LLM for pipeline generation."""

    pipeline_name: str = Field(..., description="Name of the pipeline (snake_case)")
    platform: Platform = Field(..., description="Target data platform")
    orchestrator: Orchestrator = Field(..., description="Orchestration tool to use")
    description: str = Field(..., description="Detailed description of the pipeline")
    estimated_monthly_cost_usd: float = Field(
        ..., ge=0, description="Estimated monthly cost in USD"
    )
    estimated_execution_time_minutes: Optional[float] = Field(
        None, ge=0, description="Estimated execution time in minutes"
    )
    files: List[GeneratedFile] = Field(..., min_length=1, description="List of generated files")
    dependencies: List[str] = Field(
        default_factory=list, description="List of pip/install commands"
    )
    setup_instructions: str = Field(
        ..., description="Markdown string with setup and deployment instructions"
    )
    architecture_notes: Optional[str] = Field(
        None, description="Additional architecture decisions and notes"
    )
    security_considerations: Optional[str] = Field(
        None, description="Security best practices implemented"
    )

    @field_validator("pipeline_name")
    @classmethod
    def validate_pipeline_name(cls, v: str) -> str:
        """Ensure pipeline name is valid snake_case."""
        if not v.replace("_", "").isalnum():
            raise ValueError("Pipeline name must be alphanumeric with underscores")
        return v.lower()

    @field_validator("files")
    @classmethod
    def validate_files(cls, v: List[GeneratedFile]) -> List[GeneratedFile]:
        """Ensure at least one file is generated."""
        if len(v) == 0:
            raise ValueError("At least one file must be generated")
        return v


class PipelineConfig(BaseModel):
    """Configuration for LLM and generation parameters."""

    provider: LLMProvider = Field(default=LLMProvider.XAI, description="LLM provider to use")
    model: str = Field(..., description="Model name/ID")
    temperature: float = Field(default=0.0, ge=0, le=2, description="Sampling temperature")
    max_tokens: int = Field(default=8000, ge=1000, le=32000, description="Maximum tokens")
    timeout: int = Field(default=120, ge=10, le=600, description="Request timeout in seconds")
    enable_rag: bool = Field(default=True, description="Enable RAG for better generations")
    enable_few_shot: bool = Field(
        default=True, description="Include few-shot examples in prompt"
    )
    api_key: Optional[str] = Field(None, description="API key for the provider")
    base_url: Optional[str] = Field(None, description="Base URL for API")
    additional_config: Dict[str, Any] = Field(
        default_factory=dict, description="Additional provider-specific config"
    )


class GenerationRequest(BaseModel):
    """Request model for pipeline generation."""

    prompt: str = Field(..., min_length=10, max_length=5000, description="Natural language prompt")
    config: Optional[PipelineConfig] = Field(None, description="Override default configuration")
    include_tests: bool = Field(default=True, description="Generate test files")
    include_docs: bool = Field(default=True, description="Generate documentation")


class GenerationResponse(BaseModel):
    """Response model for pipeline generation."""

    success: bool = Field(..., description="Whether generation was successful")
    pipeline: Optional[PipelineOutput] = Field(None, description="Generated pipeline output")
    error: Optional[str] = Field(None, description="Error message if failed")
    generation_time_seconds: float = Field(..., description="Time taken to generate")
    tokens_used: Optional[int] = Field(None, description="Total tokens used")
    model_used: str = Field(..., description="Model that generated the output")


class SavedGeneration(BaseModel):
    """Model for saved generations in database."""

    id: Optional[int] = None
    prompt: str
    pipeline_output: Dict[str, Any]
    config: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_rating: Optional[int] = Field(None, ge=0, le=5)
    feedback: Optional[str] = None
    tokens_used: Optional[int] = None
    generation_time_seconds: float


class TestConnectionRequest(BaseModel):
    """Request to test LLM connection."""

    provider: LLMProvider
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    additional_config: Dict[str, Any] = Field(default_factory=dict)


class TestConnectionResponse(BaseModel):
    """Response from LLM connection test."""

    success: bool
    message: str
    latency_ms: Optional[float] = None
    model: Optional[str] = None
    error: Optional[str] = None
