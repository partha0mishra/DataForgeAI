"""
Agentic Data Pipeline Generator

A GenAI-powered tool to generate production-ready data pipelines from natural language.
"""

__version__ = "0.1.0"
__author__ = "DataForgeAI Team"

from .models import PipelineConfig, GeneratedFile, PipelineOutput

__all__ = ["PipelineConfig", "GeneratedFile", "PipelineOutput"]
