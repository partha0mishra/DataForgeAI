"""FastAPI REST API for Conversational Analytics."""

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from query.query_processor import QueryProcessor
from sql.sql_generator import SQLGenerator
from execution.query_executor import QueryExecutor
from conversational.analytics_engine import ConversationalAnalyticsEngine

# Initialize FastAPI app
app = FastAPI(
    title="DataForge Conversational Analytics",
    description="Natural language interface for data analytics",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components (will be configured at startup)
query_processor = None
sql_generator = None
query_executor = None
analytics_engine = None


# Pydantic models
class DatabaseConnection(BaseModel):
    """Database connection configuration."""

    name: str = Field(..., description="Connection name")
    dialect: str = Field("postgresql", description="SQL dialect")
    host: Optional[str] = Field(None, description="Database host")
    port: Optional[int] = Field(None, description="Database port")
    database: Optional[str] = Field(None, description="Database name")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password")
    connection_string: Optional[str] = Field(None, description="Full connection string")


class QuestionRequest(BaseModel):
    """Natural language question request."""

    question: str = Field(..., description="Natural language question")
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    connection_name: str = Field("default", description="Database connection name")
    result_format: str = Field("table", description="Result format (table, summary, text, json, markdown)")
    execute: bool = Field(True, description="Execute query or just generate SQL")


class SQLRequest(BaseModel):
    """SQL query request."""

    query: str = Field(..., description="SQL query")
    connection_name: str = Field("default", description="Database connection name")
    result_format: str = Field("table", description="Result format")


class OptimizeRequest(BaseModel):
    """SQL optimization request."""

    query: str = Field(..., description="SQL query to optimize")
    connection_name: str = Field("default", description="Database connection name")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global query_processor, sql_generator, query_executor, analytics_engine

    # Initialize components
    query_processor = QueryProcessor()

    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        sql_generator = SQLGenerator(llm_api_key=api_key, llm_model="gpt-4")
    else:
        print("WARNING: OPENAI_API_KEY not set - SQL generation will not work")
        sql_generator = None

    query_executor = QueryExecutor()

    # Initialize analytics engine if we have SQL generator
    if sql_generator:
        analytics_engine = ConversationalAnalyticsEngine(
            query_processor=query_processor,
            sql_generator=sql_generator,
            query_executor=query_executor,
        )


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "components": {
            "query_processor": query_processor is not None,
            "sql_generator": sql_generator is not None,
            "query_executor": query_executor is not None,
            "analytics_engine": analytics_engine is not None,
        },
    }


# Connection management
@app.post("/connections")
async def create_connection(connection: DatabaseConnection):
    """Create database connection."""
    if not query_executor:
        raise HTTPException(status_code=500, detail="Query executor not initialized")

    try:
        query_executor.connect(
            name=connection.name,
            connection_string=connection.connection_string,
            host=connection.host,
            port=connection.port,
            database=connection.database,
            username=connection.username,
            password=connection.password,
            dialect=connection.dialect,
        )

        return {
            "message": f"Connection '{connection.name}' created successfully",
            "name": connection.name,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/connections/{connection_name}")
async def delete_connection(connection_name: str):
    """Delete database connection."""
    if not query_executor:
        raise HTTPException(status_code=500, detail="Query executor not initialized")

    query_executor.disconnect(connection_name)

    return {"message": f"Connection '{connection_name}' deleted"}


@app.get("/connections/{connection_name}/schema")
async def get_schema(connection_name: str):
    """Get database schema."""
    if not query_executor:
        raise HTTPException(status_code=500, detail="Query executor not initialized")

    try:
        schema = query_executor.get_schema(connection_name)
        return schema

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Natural language queries
@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """Ask a question in natural language."""
    if not analytics_engine:
        raise HTTPException(
            status_code=500,
            detail="Analytics engine not initialized - check OPENAI_API_KEY",
        )

    try:
        response = analytics_engine.ask(
            question=request.question,
            session_id=request.session_id,
            connection_name=request.connection_name,
            result_format=request.result_format,
            execute=request.execute,
        )

        return {
            "natural_query": response.natural_query,
            "sql_query": response.sql_query,
            "explanation": response.explanation,
            "results": response.results.to_dict(orient="records") if response.results is not None else None,
            "formatted_results": response.formatted_results,
            "execution_time_ms": response.execution_time_ms,
            "confidence": response.confidence,
            "warnings": response.warnings,
            "metadata": response.metadata,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sql/execute")
async def execute_sql(request: SQLRequest):
    """Execute SQL query directly."""
    if not query_executor:
        raise HTTPException(status_code=500, detail="Query executor not initialized")

    try:
        result = query_executor.execute_query(
            query=request.query,
            connection_name=request.connection_name,
        )

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        formatted = query_executor.format_result(
            result=result,
            format=request.result_format,
        )

        return {
            "query": request.query,
            "results": result.data.to_dict(orient="records") if result.data is not None else None,
            "formatted_results": formatted.content,
            "row_count": result.row_count,
            "column_count": result.column_count,
            "execution_time_ms": result.execution_time_ms,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sql/explain")
async def explain_sql(request: SQLRequest):
    """Explain SQL query in natural language."""
    if not analytics_engine:
        raise HTTPException(status_code=500, detail="Analytics engine not initialized")

    try:
        explanation = analytics_engine.explain_query(request.query)

        return {
            "query": request.query,
            "explanation": explanation,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sql/optimize")
async def optimize_sql(request: OptimizeRequest):
    """Optimize SQL query."""
    if not analytics_engine:
        raise HTTPException(status_code=500, detail="Analytics engine not initialized")

    try:
        optimized_query = analytics_engine.optimize_query(
            query=request.query,
            connection_name=request.connection_name,
        )

        return {
            "original_query": request.query,
            "optimized_query": optimized_query,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Session management
@app.post("/sessions")
async def create_session():
    """Create new conversation session."""
    if not analytics_engine:
        raise HTTPException(status_code=500, detail="Analytics engine not initialized")

    session_id = analytics_engine.create_session()

    return {
        "session_id": session_id,
        "message": "Session created successfully",
    }


@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for session."""
    if not analytics_engine:
        raise HTTPException(status_code=500, detail="Analytics engine not initialized")

    history = analytics_engine.get_conversation_history(session_id)

    return {
        "session_id": session_id,
        "message_count": len(history),
        "messages": history,
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete conversation session."""
    if not analytics_engine:
        raise HTTPException(status_code=500, detail="Analytics engine not initialized")

    analytics_engine.delete_session(session_id)

    return {"message": f"Session '{session_id}' deleted"}


@app.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """Clear conversation history."""
    if not analytics_engine:
        raise HTTPException(status_code=500, detail="Analytics engine not initialized")

    analytics_engine.clear_conversation(session_id)

    return {"message": f"Session '{session_id}' cleared"}


# Utility endpoints
@app.get("/suggestions")
async def get_suggestions(
    partial_query: str = Query(..., description="Partial natural language query"),
    connection_name: str = Query("default", description="Database connection name"),
):
    """Get query suggestions."""
    if not analytics_engine:
        raise HTTPException(status_code=500, detail="Analytics engine not initialized")

    try:
        suggestions = analytics_engine.get_suggestions(
            partial_query=partial_query,
            connection_name=connection_name,
        )

        return {"suggestions": suggestions}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/validate")
async def validate_question(
    question: str = Query(..., description="Natural language question"),
    connection_name: str = Query("default", description="Database connection name"),
):
    """Validate if question can be answered."""
    if not analytics_engine:
        raise HTTPException(status_code=500, detail="Analytics engine not initialized")

    try:
        validation = analytics_engine.validate_question(
            question=question,
            connection_name=connection_name,
        )

        return validation

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/schema/summary")
async def get_schema_summary(
    connection_name: str = Query("default", description="Database connection name"),
):
    """Get schema summary."""
    if not analytics_engine:
        raise HTTPException(status_code=500, detail="Analytics engine not initialized")

    try:
        summary = analytics_engine.get_schema_summary(connection_name)
        return summary

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8008)
