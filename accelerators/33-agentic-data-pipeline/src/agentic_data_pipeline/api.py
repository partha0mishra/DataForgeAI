"""
FastAPI backend for pipeline generation.
"""

import logging
import time
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .config import config_loader, settings
from .core import PipelineGenerator, create_generator
from .database import db_manager
from .models import (
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    PipelineConfig,
    TestConnectionRequest,
    TestConnectionResponse,
)
from .utils import create_zip_file

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agentic Data Pipeline API",
    description="Generate production-ready data pipelines from natural language using GenAI",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config_loader.get("security.allowed_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Agentic Data Pipeline Generator API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/test-connection", response_model=TestConnectionResponse)
async def test_llm_connection(request: TestConnectionRequest) -> TestConnectionResponse:
    """Test connection to an LLM provider.

    Args:
        request: Connection test request with provider details

    Returns:
        Connection test response with status and latency
    """
    try:
        logger.info(f"Testing connection to {request.provider.value}")

        # Create temporary config
        llm_config = config_loader.get_llm_config(request.provider.value)
        if request.api_key:
            llm_config["api_key"] = request.api_key
        if request.base_url:
            llm_config["base_url"] = request.base_url
        if request.model:
            llm_config["model"] = request.model

        # Create generator and test
        config = PipelineConfig(
            provider=request.provider,
            model=llm_config.get("model", ""),
            **request.additional_config,
        )
        generator = PipelineGenerator(config)
        result = generator.test_connection()

        logger.info(f"Connection test result: {result.success}")
        return result

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return TestConnectionResponse(success=False, message="Connection test failed", error=str(e))


@app.post("/api/generate", response_model=GenerationResponse)
async def generate_pipeline(request: GenerationRequest) -> GenerationResponse:
    """Generate a data pipeline from natural language.

    Args:
        request: Generation request with prompt and optional config

    Returns:
        Generated pipeline with code files and metadata
    """
    start_time = time.time()

    try:
        logger.info(f"Generating pipeline from prompt: {request.prompt[:100]}...")

        # Create generator
        if request.config:
            generator = PipelineGenerator(request.config)
        else:
            generator = create_generator()

        # Generate pipeline
        pipeline_output = generator.generate(request.prompt)

        generation_time = time.time() - start_time

        # Save to database
        try:
            config_dict = request.config.model_dump() if request.config else {}
            db_manager.save_generation(
                prompt=request.prompt,
                pipeline_output=pipeline_output,
                config=config_dict,
                generation_time_seconds=generation_time,
            )
        except Exception as e:
            logger.error(f"Failed to save generation to database: {e}")

        logger.info(
            f"Successfully generated pipeline '{pipeline_output.pipeline_name}' in {generation_time:.2f}s"
        )

        return GenerationResponse(
            success=True,
            pipeline=pipeline_output,
            generation_time_seconds=generation_time,
            model_used=generator.config.model,
        )

    except Exception as e:
        logger.error(f"Pipeline generation failed: {e}")
        generation_time = time.time() - start_time

        return GenerationResponse(
            success=False,
            error=str(e),
            generation_time_seconds=generation_time,
            model_used="",
        )


@app.post("/api/download")
async def download_pipeline(pipeline_name: str, files: List[Dict[str, str]]) -> StreamingResponse:
    """Download generated pipeline as a ZIP file.

    Args:
        pipeline_name: Name of the pipeline
        files: List of files with 'path' and 'content' keys

    Returns:
        StreamingResponse with ZIP file
    """
    try:
        logger.info(f"Creating ZIP file for pipeline: {pipeline_name}")

        # Convert to file format expected by create_zip_file
        file_list = [(f["path"], f["content"]) for f in files]

        # Create ZIP file in memory
        zip_buffer = create_zip_file(file_list)

        # Return as streaming response
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={pipeline_name}.zip"},
        )

    except Exception as e:
        logger.error(f"Failed to create ZIP file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/examples")
async def get_examples() -> List[str]:
    """Get list of example prompts.

    Returns:
        List of example prompts from few-shot examples
    """
    try:
        from .prompts import PromptManager

        prompt_manager = PromptManager()
        return prompt_manager.get_example_prompts()
    except Exception as e:
        logger.error(f"Failed to get examples: {e}")
        return []


@app.get("/api/stats")
async def get_stats() -> Dict:
    """Get database statistics.

    Returns:
        Dictionary with generation statistics
    """
    try:
        return db_manager.get_stats()
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/generations/recent")
async def get_recent_generations(limit: int = 10) -> List[Dict]:
    """Get recent generations.

    Args:
        limit: Maximum number to return

    Returns:
        List of recent generations
    """
    try:
        generations = db_manager.get_recent_generations(limit)
        return [g.model_dump() for g in generations]
    except Exception as e:
        logger.error(f"Failed to get recent generations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RatingRequest(BaseModel):
    """Request to rate a generation."""

    generation_id: int
    rating: int
    feedback: Optional[str] = None


@app.post("/api/rate")
async def rate_generation(request: RatingRequest) -> Dict[str, str]:
    """Rate a generated pipeline.

    Args:
        request: Rating request with generation ID and rating

    Returns:
        Success message
    """
    try:
        db_manager.update_rating(request.generation_id, request.rating, request.feedback)
        return {"message": "Rating saved successfully"}
    except Exception as e:
        logger.error(f"Failed to save rating: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agentic_data_pipeline.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
