"""FastAPI REST API for Proposal Accelerator."""

import os
from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from templates.template_manager import TemplateManager
from generation.proposal_generator import ProposalGenerator

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


app = FastAPI(title="DataForge Proposal Accelerator", version="0.1.0", description="DataForge AI Accelerator")
# Include authentication router if available
if AUTH_ENABLED:
    auth_router = create_auth_router()
    app.include_router(auth_router)


template_manager = TemplateManager()

api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    proposal_generator = ProposalGenerator(llm_api_key=api_key)
else:
    proposal_generator = None


class ProposalRequest(BaseModel):
    """Proposal generation request."""
    template_id: str
    client_name: str
    requirements: str
    budget: Optional[float] = None


@app.get("/health")
async def health_check():
    """Health check."""
    return {
        "status": "healthy",
        "llm_enabled": api_key is not None,
    }


@app.get("/templates")
async def list_templates():
    """List available templates."""
    templates = template_manager.list_templates()

    return {
        "templates": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "type": t.proposal_type.value,
                "sections": len(t.sections),
            }
            for t in templates
        ]
    }


@app.post("/proposals/generate")
async def generate_proposal(request: ProposalRequest):
    """Generate a proposal."""
    if not proposal_generator:
        raise HTTPException(
            status_code=500,
            detail="Proposal generator not initialized - OPENAI_API_KEY required",
        )

    template = template_manager.get_template(request.template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    proposal = proposal_generator.generate_proposal(
        template=template,
        requirements=request.requirements,
        client_name=request.client_name,
        budget=request.budget,
    )

    return {
        "proposal_id": proposal.proposal_id,
        "title": proposal.title,
        "client_name": proposal.client_name,
        "sections": proposal.sections,
        "estimated_cost": proposal.estimated_cost,
        "estimated_duration_days": proposal.estimated_duration_days,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
