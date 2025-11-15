"""FastAPI REST API for Process Optimization."""

import os
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mining.process_miner import ProcessMiner
from analysis.bottleneck_analyzer import BottleneckAnalyzer
from optimization.optimizer import ProcessOptimizer

# Initialize FastAPI app
app = FastAPI(
    title="DataForge Process Optimization",
    description="Business process mining, analysis, and optimization",
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

# Initialize components
process_miner = ProcessMiner()
bottleneck_analyzer = BottleneckAnalyzer()

# Initialize optimizer with LLM if API key available
api_key = os.getenv("OPENAI_API_KEY")
process_optimizer = ProcessOptimizer(llm_api_key=api_key) if api_key else ProcessOptimizer()


# Pydantic models
class ProcessDiscoveryRequest(BaseModel):
    """Process discovery request."""

    case_id_column: str = Field("case_id", description="Case ID column name")
    activity_column: str = Field("activity", description="Activity column name")
    timestamp_column: str = Field("timestamp", description="Timestamp column name")
    resource_column: Optional[str] = Field(None, description="Resource column name")
    outcome_column: Optional[str] = Field(None, description="Outcome column name")


class BottleneckAnalysisRequest(BaseModel):
    """Bottleneck analysis request."""

    duration_threshold_percentile: float = Field(0.75, description="Duration threshold percentile")
    frequency_threshold_std: float = Field(2.0, description="Frequency threshold std devs")
    waiting_time_threshold_hours: float = Field(24.0, description="Waiting time threshold")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "llm_enabled": api_key is not None,
    }


# Process discovery
@app.post("/process/discover")
async def discover_process(
    file: UploadFile = File(...),
    case_id_column: str = "case_id",
    activity_column: str = "activity",
    timestamp_column: str = "timestamp",
    resource_column: Optional[str] = None,
    outcome_column: Optional[str] = None,
):
    """Discover process from event log."""
    try:
        # Read event log
        event_log = pd.read_csv(file.file)

        # Discover process
        discovered = process_miner.discover_process(
            event_log=event_log,
            case_id_column=case_id_column,
            activity_column=activity_column,
            timestamp_column=timestamp_column,
            resource_column=resource_column,
            outcome_column=outcome_column,
        )

        # Build response
        return {
            "process_name": discovered.process_name,
            "total_cases": discovered.total_cases,
            "unique_activities": discovered.unique_activities,
            "start_activities": discovered.start_activities,
            "end_activities": discovered.end_activities,
            "steps": {
                activity: {
                    "count": step.count,
                    "avg_duration_hours": step.avg_duration,
                    "min_duration_hours": step.min_duration,
                    "max_duration_hours": step.max_duration,
                    "resources": step.resources,
                }
                for activity, step in discovered.steps.items()
            },
            "top_paths": [
                {
                    "steps": path.steps,
                    "count": path.count,
                    "avg_duration_hours": path.avg_total_duration,
                    "success_rate": path.success_rate,
                }
                for path in discovered.paths[:10]
            ],
            "statistics": discovered.statistics,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Bottleneck analysis
@app.post("/process/analyze")
async def analyze_bottlenecks(
    file: UploadFile = File(...),
    case_id_column: str = "case_id",
    activity_column: str = "activity",
    timestamp_column: str = "timestamp",
    resource_column: Optional[str] = None,
    outcome_column: Optional[str] = None,
    duration_threshold_percentile: float = 0.75,
    frequency_threshold_std: float = 2.0,
    waiting_time_threshold_hours: float = 24.0,
):
    """Analyze process for bottlenecks."""
    try:
        # Read event log
        event_log = pd.read_csv(file.file)

        # Discover process
        discovered = process_miner.discover_process(
            event_log=event_log,
            case_id_column=case_id_column,
            activity_column=activity_column,
            timestamp_column=timestamp_column,
            resource_column=resource_column,
            outcome_column=outcome_column,
        )

        # Analyze bottlenecks
        analyzer = BottleneckAnalyzer(
            duration_threshold_percentile=duration_threshold_percentile,
            frequency_threshold_std=frequency_threshold_std,
            waiting_time_threshold_hours=waiting_time_threshold_hours,
        )

        analysis = analyzer.analyze(
            discovered_process=discovered,
            event_log=event_log,
            case_id_column=case_id_column,
            activity_column=activity_column,
            timestamp_column=timestamp_column,
            resource_column=resource_column,
        )

        # Build response
        return {
            "total_bottlenecks": analysis.total_bottlenecks,
            "high_severity_count": analysis.high_severity_count,
            "medium_severity_count": analysis.medium_severity_count,
            "low_severity_count": analysis.low_severity_count,
            "overall_health_score": analysis.overall_health_score,
            "bottlenecks": [
                {
                    "activity": b.activity,
                    "type": b.bottleneck_type,
                    "severity": b.severity,
                    "impact": b.impact,
                    "evidence": b.evidence,
                    "recommendations": b.recommendations,
                }
                for b in analysis.bottlenecks
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Complete optimization
@app.post("/process/optimize")
async def optimize_process(
    file: UploadFile = File(...),
    case_id_column: str = "case_id",
    activity_column: str = "activity",
    timestamp_column: str = "timestamp",
    resource_column: Optional[str] = None,
    outcome_column: Optional[str] = None,
):
    """Discover, analyze, and optimize process."""
    try:
        # Read event log
        event_log = pd.read_csv(file.file)

        # Discover process
        discovered = process_miner.discover_process(
            event_log=event_log,
            case_id_column=case_id_column,
            activity_column=activity_column,
            timestamp_column=timestamp_column,
            resource_column=resource_column,
            outcome_column=outcome_column,
        )

        # Analyze bottlenecks
        analysis = bottleneck_analyzer.analyze(
            discovered_process=discovered,
            event_log=event_log,
            case_id_column=case_id_column,
            activity_column=activity_column,
            timestamp_column=timestamp_column,
            resource_column=resource_column,
        )

        # Generate optimization plan
        optimization_plan = process_optimizer.optimize(
            discovered_process=discovered,
            bottleneck_analysis=analysis,
        )

        # Build response
        return {
            "process": {
                "name": discovered.process_name,
                "total_cases": discovered.total_cases,
                "unique_activities": discovered.unique_activities,
                "avg_duration_hours": discovered.statistics.get("avg_case_duration_hours", 0),
            },
            "analysis": {
                "health_score": analysis.overall_health_score,
                "total_bottlenecks": analysis.total_bottlenecks,
                "high_severity": analysis.high_severity_count,
            },
            "optimization": {
                "current_health_score": optimization_plan.current_health_score,
                "projected_health_score": optimization_plan.projected_health_score,
                "total_recommendations": len(optimization_plan.recommendations),
                "quick_wins": len(optimization_plan.quick_wins),
                "strategic_initiatives": len(optimization_plan.strategic_initiatives),
                "total_estimated_savings_hours": optimization_plan.total_estimated_savings_hours,
            },
            "recommendations": [
                {
                    "title": r.title,
                    "description": r.description,
                    "category": r.category,
                    "priority": r.priority,
                    "estimated_impact": r.estimated_impact,
                    "implementation_effort": r.implementation_effort,
                    "estimated_savings_hours": r.estimated_savings_hours,
                }
                for r in optimization_plan.recommendations
            ],
            "quick_wins": [
                {
                    "title": r.title,
                    "description": r.description,
                    "estimated_savings_hours": r.estimated_savings_hours,
                }
                for r in optimization_plan.quick_wins
            ],
            "roadmap": optimization_plan.implementation_roadmap,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Export BPMN
@app.post("/process/export/bpmn")
async def export_bpmn(
    file: UploadFile = File(...),
    case_id_column: str = "case_id",
    activity_column: str = "activity",
    timestamp_column: str = "timestamp",
):
    """Export discovered process as BPMN."""
    try:
        # Read event log
        event_log = pd.read_csv(file.file)

        # Discover process
        discovered = process_miner.discover_process(
            event_log=event_log,
            case_id_column=case_id_column,
            activity_column=activity_column,
            timestamp_column=timestamp_column,
        )

        # Export BPMN
        bpmn_xml = process_miner.export_bpmn(discovered)

        return {"bpmn": bpmn_xml}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8009)
