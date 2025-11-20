"""
Core LLM abstraction layer with multi-provider support.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import boto3
from anthropic import Anthropic
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from openai import AzureOpenAI, OpenAI

from .config import config_loader, settings
from .models import (
    LLMProvider,
    PipelineConfig,
    PipelineOutput,
    TestConnectionResponse,
)
from .prompts import PromptManager

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temperature = config.get("temperature", 0.0)
        self.max_tokens = config.get("max_tokens", 8000)
        self.timeout = config.get("timeout", 120)
        self.max_retries = config.get("max_retries", 3)

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate text from the LLM."""
        pass

    @abstractmethod
    def test_connection(self) -> TestConnectionResponse:
        """Test the connection to the LLM provider."""
        pass


class XAIClient(LLMClient):
    """xAI / Grok API client."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        api_key = settings.xai_api_key or config.get("api_key")
        if not api_key:
            raise ValueError("xAI API key is required")

        self.client = OpenAI(
            api_key=api_key,
            base_url=settings.xai_base_url,
            timeout=self.timeout,
        )
        self.model = settings.xai_model

    def generate(self, prompt: str) -> str:
        """Generate text using xAI Grok API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"xAI generation failed: {e}")
            raise

    def test_connection(self) -> TestConnectionResponse:
        """Test xAI connection."""
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'hello world'"}],
                max_tokens=10,
            )
            latency_ms = (time.time() - start_time) * 1000
            return TestConnectionResponse(
                success=True,
                message=f"Successfully connected to xAI ({self.model})",
                latency_ms=latency_ms,
                model=self.model,
            )
        except Exception as e:
            return TestConnectionResponse(
                success=False, message="Failed to connect to xAI", error=str(e)
            )


class AzureOpenAIClient(LLMClient):
    """Azure OpenAI client."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        api_key = settings.azure_openai_api_key or config.get("api_key")
        endpoint = settings.azure_openai_endpoint or config.get("endpoint")

        if not api_key or not endpoint:
            raise ValueError("Azure OpenAI API key and endpoint are required")

        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=endpoint,
            timeout=self.timeout,
        )
        self.deployment = settings.azure_openai_deployment

    def generate(self, prompt: str) -> str:
        """Generate text using Azure OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Azure OpenAI generation failed: {e}")
            raise

    def test_connection(self) -> TestConnectionResponse:
        """Test Azure OpenAI connection."""
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": "Say 'hello world'"}],
                max_tokens=10,
            )
            latency_ms = (time.time() - start_time) * 1000
            return TestConnectionResponse(
                success=True,
                message=f"Successfully connected to Azure OpenAI ({self.deployment})",
                latency_ms=latency_ms,
                model=self.deployment,
            )
        except Exception as e:
            return TestConnectionResponse(
                success=False, message="Failed to connect to Azure OpenAI", error=str(e)
            )


class BedrockClient(LLMClient):
    """AWS Bedrock client."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        self.model_id = settings.bedrock_model_id

    def generate(self, prompt: str) -> str:
        """Generate text using AWS Bedrock."""
        try:
            # Claude models use Anthropic format
            if "claude" in self.model_id.lower():
                body = json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                )
            # Llama models use Meta format
            elif "llama" in self.model_id.lower():
                body = json.dumps(
                    {
                        "prompt": prompt,
                        "max_gen_len": self.max_tokens,
                        "temperature": self.temperature,
                    }
                )
            else:
                raise ValueError(f"Unsupported Bedrock model: {self.model_id}")

            response = self.bedrock.invoke_model(modelId=self.model_id, body=body)

            response_body = json.loads(response["body"].read())

            # Extract content based on model
            if "claude" in self.model_id.lower():
                return response_body["content"][0]["text"]
            elif "llama" in self.model_id.lower():
                return response_body["generation"]

        except Exception as e:
            logger.error(f"Bedrock generation failed: {e}")
            raise

    def test_connection(self) -> TestConnectionResponse:
        """Test Bedrock connection."""
        start_time = time.time()
        try:
            # Use appropriate format based on model
            if "claude" in self.model_id.lower():
                body = json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Say 'hello world'"}],
                    }
                )
            else:
                body = json.dumps({"prompt": "Say 'hello world'", "max_gen_len": 10})

            self.bedrock.invoke_model(modelId=self.model_id, body=body)
            latency_ms = (time.time() - start_time) * 1000

            return TestConnectionResponse(
                success=True,
                message=f"Successfully connected to AWS Bedrock ({self.model_id})",
                latency_ms=latency_ms,
                model=self.model_id,
            )
        except Exception as e:
            return TestConnectionResponse(
                success=False, message="Failed to connect to AWS Bedrock", error=str(e)
            )


class LocalLLMClient(LLMClient):
    """Local LLM client (OpenAI-compatible endpoint)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        base_url = settings.local_llm_base_url or config.get("base_url")
        api_key = settings.local_llm_api_key or config.get("api_key", "not-needed")

        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=self.timeout)
        self.model = settings.local_llm_model

    def generate(self, prompt: str) -> str:
        """Generate text using local LLM."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Local LLM generation failed: {e}")
            raise

    def test_connection(self) -> TestConnectionResponse:
        """Test local LLM connection."""
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'hello world'"}],
                max_tokens=10,
            )
            latency_ms = (time.time() - start_time) * 1000
            return TestConnectionResponse(
                success=True,
                message=f"Successfully connected to Local LLM ({self.model})",
                latency_ms=latency_ms,
                model=self.model,
            )
        except Exception as e:
            return TestConnectionResponse(
                success=False, message="Failed to connect to Local LLM", error=str(e)
            )


class PipelineGenerator:
    """Generate data pipelines using LLMs."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or self._get_default_config()
        self.llm_client = self._create_llm_client()
        self.prompt_manager = PromptManager()

    def _get_default_config(self) -> PipelineConfig:
        """Get default configuration."""
        llm_config = config_loader.get_llm_config()
        provider = LLMProvider(llm_config["provider"])

        return PipelineConfig(
            provider=provider,
            model=llm_config.get("model", ""),
            temperature=llm_config.get("temperature", 0.0),
            max_tokens=llm_config.get("max_tokens", 8000),
            timeout=llm_config.get("timeout", 120),
            enable_rag=settings.enable_rag,
            enable_few_shot=settings.enable_few_shot,
        )

    def _create_llm_client(self) -> LLMClient:
        """Create LLM client based on provider."""
        llm_config = config_loader.get_llm_config(self.config.provider.value)

        if self.config.provider == LLMProvider.XAI:
            return XAIClient(llm_config)
        elif self.config.provider == LLMProvider.AZURE_OPENAI:
            return AzureOpenAIClient(llm_config)
        elif self.config.provider == LLMProvider.AWS_BEDROCK:
            return BedrockClient(llm_config)
        elif self.config.provider == LLMProvider.LOCAL:
            return LocalLLMClient(llm_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    def generate(self, user_prompt: str) -> PipelineOutput:
        """Generate a data pipeline from natural language."""
        logger.info(f"Generating pipeline from prompt: {user_prompt[:100]}...")

        # Build full prompt with system instructions and few-shot examples
        full_prompt = self.prompt_manager.build_prompt(
            user_prompt=user_prompt,
            include_few_shot=self.config.enable_few_shot,
        )

        # Generate response from LLM
        logger.info(f"Calling LLM ({self.config.provider.value})...")
        raw_response = self.llm_client.generate(full_prompt)

        # Parse JSON response
        logger.info("Parsing LLM response...")
        try:
            # Extract JSON from response (handle potential markdown code blocks)
            json_str = raw_response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()

            pipeline_dict = json.loads(json_str)
            pipeline_output = PipelineOutput(**pipeline_dict)

            logger.info(f"Successfully generated pipeline: {pipeline_output.pipeline_name}")
            return pipeline_output

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {raw_response[:500]}")
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create PipelineOutput: {e}")
            raise ValueError(f"Failed to validate pipeline output: {str(e)}")

    def test_connection(self) -> TestConnectionResponse:
        """Test the LLM connection."""
        return self.llm_client.test_connection()


def create_generator(provider: Optional[str] = None) -> PipelineGenerator:
    """Factory function to create a pipeline generator."""
    if provider:
        llm_config = config_loader.get_llm_config(provider)
        config = PipelineConfig(
            provider=LLMProvider(provider),
            model=llm_config.get("model", ""),
            temperature=llm_config.get("temperature", 0.0),
            max_tokens=llm_config.get("max_tokens", 8000),
        )
        return PipelineGenerator(config)
    return PipelineGenerator()
