"""
Tests for core pipeline generation functionality.
"""

import json
from unittest.mock import Mock, patch

import pytest

from agentic_data_pipeline.core import PipelineGenerator, XAIClient
from agentic_data_pipeline.models import (
    LLMProvider,
    PipelineConfig,
    PipelineOutput,
    Platform,
    Orchestrator,
)


class TestXAIClient:
    """Tests for xAI client."""

    @pytest.fixture
    def client(self):
        """Create a test xAI client."""
        config = {
            "api_key": "test-key",
            "model": "grok-beta",
            "temperature": 0.0,
            "max_tokens": 1000,
        }
        with patch("agentic_data_pipeline.core.OpenAI"):
            return XAIClient(config)

    def test_init(self, client):
        """Test client initialization."""
        assert client.temperature == 0.0
        assert client.max_tokens == 1000

    def test_generate(self, client):
        """Test text generation."""
        # Mock the OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Generated text"))]

        with patch.object(client.client.chat.completions, "create", return_value=mock_response):
            result = client.generate("Test prompt")
            assert result == "Generated text"

    def test_test_connection_success(self, client):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="hello world"))]

        with patch.object(client.client.chat.completions, "create", return_value=mock_response):
            result = client.test_connection()
            assert result.success is True
            assert result.model == "grok-beta"
            assert result.latency_ms > 0

    def test_test_connection_failure(self, client):
        """Test failed connection test."""
        with patch.object(
            client.client.chat.completions,
            "create",
            side_effect=Exception("Connection failed"),
        ):
            result = client.test_connection()
            assert result.success is False
            assert "Connection failed" in result.error


class TestPipelineGenerator:
    """Tests for pipeline generator."""

    @pytest.fixture
    def generator(self):
        """Create a test generator."""
        config = PipelineConfig(
            provider=LLMProvider.XAI,
            model="grok-beta",
            temperature=0.0,
            max_tokens=1000,
        )
        with patch("agentic_data_pipeline.core.XAIClient"):
            return PipelineGenerator(config)

    def test_init(self, generator):
        """Test generator initialization."""
        assert generator.config.provider == LLMProvider.XAI
        assert generator.config.temperature == 0.0

    def test_generate_success(self, generator):
        """Test successful pipeline generation."""
        # Mock LLM response
        mock_pipeline = {
            "pipeline_name": "test_pipeline",
            "platform": "databricks",
            "orchestrator": "airflow",
            "description": "Test pipeline",
            "estimated_monthly_cost_usd": 100.0,
            "files": [{"path": "test.py", "content": "print('hello')"}],
            "dependencies": ["pip install pytest"],
            "setup_instructions": "Run pip install",
        }

        with patch.object(
            generator.llm_client, "generate", return_value=json.dumps(mock_pipeline)
        ):
            result = generator.generate("Create a test pipeline")

            assert isinstance(result, PipelineOutput)
            assert result.pipeline_name == "test_pipeline"
            assert result.platform == Platform.DATABRICKS
            assert result.orchestrator == Orchestrator.AIRFLOW
            assert len(result.files) == 1

    def test_generate_invalid_json(self, generator):
        """Test handling of invalid JSON response."""
        with patch.object(generator.llm_client, "generate", return_value="Invalid JSON"):
            with pytest.raises(ValueError, match="invalid JSON"):
                generator.generate("Create a test pipeline")

    def test_generate_missing_fields(self, generator):
        """Test handling of missing required fields."""
        incomplete_pipeline = {
            "pipeline_name": "test",
            # Missing required fields
        }

        with patch.object(
            generator.llm_client, "generate", return_value=json.dumps(incomplete_pipeline)
        ):
            with pytest.raises(ValueError):
                generator.generate("Create a test pipeline")


@pytest.mark.integration
class TestPipelineGeneratorIntegration:
    """Integration tests (require actual API keys)."""

    @pytest.mark.skip(reason="Requires API key")
    def test_real_generation(self):
        """Test with real LLM API (skipped by default)."""
        generator = PipelineGenerator()
        result = generator.generate(
            "Create a simple pipeline that copies CSV files from S3 to Snowflake"
        )

        assert isinstance(result, PipelineOutput)
        assert result.pipeline_name
        assert len(result.files) > 0
