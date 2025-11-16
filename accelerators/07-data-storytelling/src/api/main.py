"""FastAPI application for Data Storytelling."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration

# Import storytelling modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from insights.insight_extractor import InsightExtractor, InsightType
from narrative.narrative_generator import NarrativeGenerator, NarrativeStyle, NarrativeFormat
from reports.report_builder import ReportBuilder

# Import authentication
try:
    from dataforge_common import (
        get_current_user,
        get_optional_user,
        require_roles,
        create_auth_router,
        User,
    )
    AUTH_ENABLED = True
except ImportError:
    print("Warning: dataforge-common not installed. Authentication disabled.")
    AUTH_ENABLED = False


logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DataForge Data Storytelling API",
    description="AI-powered data storytelling with automatic insights and narratives",
    version="0.1.0",
)
# Include authentication router if available
if AUTH_ENABLED:
    auth_router = create_auth_router()
    app.include_router(auth_router)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
insight_extractor = InsightExtractor()
report_builder = ReportBuilder()

# Initialize narrative generator if API key available
narrative_generator = None
if os.getenv("OPENAI_API_KEY"):
    try:
        narrative_generator = NarrativeGenerator(
            llm_api_key=os.getenv("OPENAI_API_KEY"),
            llm_model=os.getenv("OPENAI_MODEL", "gpt-4"),
        )
    except Exception as e:
        logger.warning(f"Narrative generator initialization failed: {e}")


# Models
class InsightRequest(BaseModel):
    """Insight extraction request."""

    max_insights: int = 10
    confidence_threshold: float = 0.6


class NarrativeRequest(BaseModel):
    """Narrative generation request."""

    context: str = ""
    audience: str = "general"
    style: NarrativeStyle = NarrativeStyle.EXECUTIVE
    format: NarrativeFormat = NarrativeFormat.MARKDOWN
    max_length: int = 2000


class StoryRequest(BaseModel):
    """Complete story generation request."""

    title: str
    context: str = ""
    audience: str = "general"
    style: NarrativeStyle = NarrativeStyle.EXECUTIVE
    max_insights: int = 10


# Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DataForge Data Storytelling API",
        "version": "0.1.0",
        "status": "running",
        "narrative_generator_available": narrative_generator is not None,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    increment_counter("health_checks")
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "insight_extractor": True,
            "narrative_generator": narrative_generator is not None,
            "report_builder": True,
        },
    }


@app.post("/insights/extract")
@track_duration("extract_insights_duration")
async def extract_insights(
    file: UploadFile = File(...),
    max_insights: int = 10,
    confidence_threshold: float = 0.6,
):
    """Extract insights from uploaded data file."""
    logger.info("Extracting insights", filename=file.filename)

    try:
        # Read file
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(".json"):
            df = pd.read_json(file.file)
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use CSV, JSON, or Excel.",
            )

        # Extract insights
        insights = insight_extractor.extract_insights(df, max_insights=max_insights)

        increment_counter("insights_extracted")

        return {
            "insights": [
                {
                    "type": insight.type.value,
                    "title": insight.title,
                    "description": insight.description,
                    "confidence": insight.confidence,
                    "metrics": insight.metrics,
                    "affected_columns": insight.affected_columns,
                    "visualization_suggestion": insight.visualization_suggestion,
                }
                for insight in insights
            ],
            "count": len(insights),
            "dataset_rows": len(df),
            "dataset_columns": len(df.columns),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Insight extraction failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/narrative/generate")
@track_duration("generate_narrative_duration")
async def generate_narrative(
    file: UploadFile = File(...),
    context: str = "",
    audience: str = "general",
    style: NarrativeStyle = NarrativeStyle.EXECUTIVE,
    format: NarrativeFormat = NarrativeFormat.MARKDOWN,
):
    """Generate narrative from data insights."""
    if not narrative_generator:
        raise HTTPException(
            status_code=503,
            detail="Narrative generator not available. Set OPENAI_API_KEY environment variable.",
        )

    logger.info("Generating narrative", filename=file.filename, style=style.value)

    try:
        # Read file
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(".json"):
            df = pd.read_json(file.file)
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use CSV, JSON, or Excel.",
            )

        # Extract insights
        insights = insight_extractor.extract_insights(df, max_insights=10)

        if not insights:
            raise HTTPException(
                status_code=400,
                detail="No insights found in the data.",
            )

        # Generate narrative
        narrative = narrative_generator.generate_narrative(
            insights=insights,
            context=context,
            audience=audience,
            style=style,
            format=format,
        )

        increment_counter("narratives_generated")

        # Format narrative
        formatted = narrative_generator.format_narrative(narrative, format)

        return {
            "narrative": {
                "title": narrative.title,
                "summary": narrative.summary,
                "sections": narrative.sections,
                "key_findings": narrative.key_findings,
                "recommendations": narrative.recommendations,
            },
            "formatted_content": formatted,
            "format": format.value,
            "insights_used": len(insights),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Narrative generation failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/story/create", response_class=HTMLResponse)
@track_duration("create_story_duration")
async def create_story(
    file: UploadFile = File(...),
    title: str = "Data Story",
    context: str = "",
    audience: str = "general",
    style: NarrativeStyle = NarrativeStyle.EXECUTIVE,
):
    """Create complete data story (insights + narrative + report)."""
    if not narrative_generator:
        raise HTTPException(
            status_code=503,
            detail="Narrative generator not available. Set OPENAI_API_KEY environment variable.",
        )

    logger.info("Creating complete story", filename=file.filename, title=title)

    try:
        # Read file
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(".json"):
            df = pd.read_json(file.file)
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use CSV, JSON, or Excel.",
            )

        # Extract insights
        insights = insight_extractor.extract_insights(df, max_insights=10)

        if not insights:
            raise HTTPException(
                status_code=400,
                detail="No insights found in the data.",
            )

        # Generate narrative
        narrative = narrative_generator.generate_narrative(
            insights=insights,
            context=context,
            audience=audience,
            style=style,
        )

        # Build report
        report = report_builder.create_report(
            data=df,
            insights=insights,
            narrative=narrative,
            title=title,
        )

        increment_counter("stories_created")

        # Export as HTML
        html = report_builder.export_html(report)

        return html

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Story creation failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/story/create/markdown", response_class=PlainTextResponse)
async def create_story_markdown(
    file: UploadFile = File(...),
    title: str = "Data Story",
    context: str = "",
    audience: str = "general",
    style: NarrativeStyle = NarrativeStyle.EXECUTIVE,
):
    """Create complete data story as Markdown."""
    if not narrative_generator:
        raise HTTPException(
            status_code=503,
            detail="Narrative generator not available. Set OPENAI_API_KEY environment variable.",
        )

    try:
        # Read file
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(".json"):
            df = pd.read_json(file.file)
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format.",
            )

        # Extract insights
        insights = insight_extractor.extract_insights(df, max_insights=10)

        if not insights:
            raise HTTPException(
                status_code=400,
                detail="No insights found in the data.",
            )

        # Generate narrative
        narrative = narrative_generator.generate_narrative(
            insights=insights,
            context=context,
            audience=audience,
            style=style,
        )

        # Build report
        report = report_builder.create_report(
            data=df,
            insights=insights,
            narrative=narrative,
            title=title,
        )

        # Export as Markdown
        markdown = report_builder.export_markdown(report)

        return markdown

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Story creation failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/statistics")
async def get_statistics():
    """Get storytelling statistics."""
    return {
        "services_available": {
            "insight_extraction": True,
            "narrative_generation": narrative_generator is not None,
            "report_building": True,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)
