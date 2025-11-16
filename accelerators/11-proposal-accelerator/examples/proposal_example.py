"""Example: Proposal generation workflow."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from templates.template_manager import TemplateManager
from generation.proposal_generator import ProposalGenerator


def main():
    """Run proposal generation example."""
    print("=" * 80)
    print(" DataForge Proposal Accelerator - Example")
    print("=" * 80)

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\nWARNING: OPENAI_API_KEY not set!")
        print("Set API key with: export OPENAI_API_KEY='your-key'")
        return

    # Initialize components
    template_manager = TemplateManager()
    proposal_generator = ProposalGenerator(llm_api_key=api_key)

    # List templates
    print("\n1. Available Templates:")
    templates = template_manager.list_templates()
    for t in templates:
        print(f"  - {t.name} ({t.proposal_type.value})")

    # Generate proposal
    print("\n2. Generating Proposal...")

    requirements = """
    Build a custom data analytics platform with the following features:
    - Real-time data ingestion from multiple sources
    - Interactive dashboards and visualizations
    - Machine learning model deployment
    - Role-based access control
    - API for third-party integrations
    """

    template = templates[0]  # Use first template

    proposal = proposal_generator.generate_proposal(
        template=template,
        requirements=requirements,
        client_name="Acme Corporation",
        budget=150000.0,
    )

    print(f"✓ Generated proposal: {proposal.proposal_id}")
    print(f"  Client: {proposal.client_name}")
    print(f"  Estimated Cost: ${proposal.estimated_cost:,.2f}")
    print(f"  Estimated Duration: {proposal.estimated_duration_days} days")

    print("\n3. Proposal Sections:")
    for section_title, content in proposal.sections.items():
        print(f"\n{section_title}:")
        print(content[:200] + "..." if len(content) > 200 else content)

    print("\n" + "=" * 80)
    print(" Example Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
