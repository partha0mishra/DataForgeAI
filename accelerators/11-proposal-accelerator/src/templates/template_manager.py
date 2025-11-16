"""Proposal template management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class ProposalType(Enum):
    """Types of proposals."""
    SOFTWARE_DEVELOPMENT = "software_development"
    CONSULTING = "consulting"
    DATA_ANALYTICS = "data_analytics"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class ProposalSection:
    """A section of a proposal."""
    title: str
    content: str
    order: int = 0


@dataclass
class ProposalTemplate:
    """A proposal template."""
    template_id: str
    name: str
    proposal_type: ProposalType
    sections: List[ProposalSection] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


class TemplateManager:
    """Manage proposal templates."""

    def __init__(self):
        """Initialize template manager."""
        self.templates: Dict[str, ProposalTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default templates."""
        # Software development template
        software_template = ProposalTemplate(
            template_id="template_software_001",
            name="Software Development Proposal",
            proposal_type=ProposalType.SOFTWARE_DEVELOPMENT,
            sections=[
                ProposalSection("Executive Summary", "", 1),
                ProposalSection("Project Scope", "", 2),
                ProposalSection("Technical Approach", "", 3),
                ProposalSection("Timeline & Milestones", "", 4),
                ProposalSection("Cost Breakdown", "", 5),
                ProposalSection("Team & Resources", "", 6),
                ProposalSection("Terms & Conditions", "", 7),
            ],
            variables=["client_name", "project_name", "budget", "timeline"],
        )
        self.templates[software_template.template_id] = software_template

        # Data analytics template
        analytics_template = ProposalTemplate(
            template_id="template_analytics_001",
            name="Data Analytics Proposal",
            proposal_type=ProposalType.DATA_ANALYTICS,
            sections=[
                ProposalSection("Executive Summary", "", 1),
                ProposalSection("Business Objectives", "", 2),
                ProposalSection("Data Analysis Approach", "", 3),
                ProposalSection("Deliverables", "", 4),
                ProposalSection("Timeline", "", 5),
                ProposalSection("Investment", "", 6),
            ],
            variables=["client_name", "use_case", "data_sources", "budget"],
        )
        self.templates[analytics_template.template_id] = analytics_template

    def get_template(self, template_id: str) -> ProposalTemplate:
        """Get template by ID."""
        return self.templates.get(template_id)

    def list_templates(self) -> List[ProposalTemplate]:
        """List all templates."""
        return list(self.templates.values())
