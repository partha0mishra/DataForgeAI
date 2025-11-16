"""AI-powered proposal generation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from dataforge_ai_core.llm import LLMClient
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GeneratedProposal:
    """A generated proposal."""
    proposal_id: str
    title: str
    client_name: str
    sections: Dict[str, str]
    estimated_cost: float
    estimated_duration_days: int
    generated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProposalGenerator:
    """Generate proposals using AI."""

    def __init__(self, llm_api_key: str, llm_model: str = "gpt-4"):
        """Initialize proposal generator."""
        self.llm_client = LLMClient(api_key=llm_api_key, model=llm_model)

    def generate_proposal(
        self,
        template,
        requirements: str,
        client_name: str,
        budget: Optional[float] = None,
    ) -> GeneratedProposal:
        """Generate proposal from requirements."""
        logger.info(f"Generating proposal for {client_name}")

        proposal_id = f"proposal_{datetime.utcnow().timestamp()}"

        # Generate each section
        sections = {}

        for section in template.sections:
            content = self._generate_section(
                section_title=section.title,
                requirements=requirements,
                client_name=client_name,
                budget=budget,
            )
            sections[section.title] = content

        # Estimate cost and timeline
        cost = self._estimate_cost(requirements, budget)
        duration = self._estimate_duration(requirements)

        proposal = GeneratedProposal(
            proposal_id=proposal_id,
            title=f"Proposal for {client_name}",
            client_name=client_name,
            sections=sections,
            estimated_cost=cost,
            estimated_duration_days=duration,
        )

        logger.info(f"Generated proposal: {proposal_id}")

        return proposal

    def _generate_section(
        self,
        section_title: str,
        requirements: str,
        client_name: str,
        budget: Optional[float],
    ) -> str:
        """Generate a proposal section."""
        budget_str = f"${budget:,.2f}" if budget else "To be determined"
        prompt = f"""Generate the "{section_title}" section for a business proposal.

Client: {client_name}
Requirements: {requirements}
Budget: {budget_str}

Write a professional, concise section (2-3 paragraphs) that addresses the requirements.
"""

        response = self.llm_client.generate_chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert proposal writer.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
        )

        return response.strip()

    def _estimate_cost(self, requirements: str, budget: Optional[float]) -> float:
        """Estimate project cost."""
        if budget:
            return budget

        # Simple estimation based on requirements length
        base_cost = 10000
        complexity_factor = len(requirements) / 100
        estimated_cost = base_cost * (1 + complexity_factor * 0.5)

        return round(estimated_cost, -3)  # Round to nearest 1000

    def _estimate_duration(self, requirements: str) -> int:
        """Estimate project duration in days."""
        # Simple estimation
        base_duration = 30
        complexity_factor = len(requirements) / 100
        estimated_duration = int(base_duration * (1 + complexity_factor * 0.3))

        return estimated_duration
