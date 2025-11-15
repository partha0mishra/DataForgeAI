"""Narrative generator for creating stories from data insights using LLM."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from dataforge_ai_core.llm_clients import OpenAIClient
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class NarrativeStyle(str, Enum):
    """Narrative writing styles."""

    EXECUTIVE = "executive"  # Brief, business-focused
    DETAILED = "detailed"  # Comprehensive analysis
    CASUAL = "casual"  # Conversational tone
    TECHNICAL = "technical"  # Technical depth
    STORYTELLING = "storytelling"  # Engaging narrative


class NarrativeFormat(str, Enum):
    """Output formats."""

    MARKDOWN = "markdown"
    HTML = "html"
    PLAIN_TEXT = "plain_text"
    JSON = "json"


@dataclass
class Narrative:
    """Generated narrative."""

    title: str
    summary: str
    sections: List[Dict[str, str]]
    key_findings: List[str]
    recommendations: List[str]
    format: NarrativeFormat
    metadata: Dict[str, Any]


class NarrativeGenerator:
    """
    Generate narratives from data insights using LLM.

    Provides:
    - Story generation from insights
    - Multiple writing styles
    - Structured narratives
    - Key findings extraction
    - Recommendations

    Example:
        generator = NarrativeGenerator(
            llm_api_key="your-key",
            style=NarrativeStyle.EXECUTIVE
        )

        narrative = generator.generate_narrative(
            insights=insights,
            context="Q4 sales analysis",
            audience="executive team"
        )

        print(narrative.title)
        print(narrative.summary)
        for section in narrative.sections:
            print(f"## {section['title']}")
            print(section['content'])
    """

    def __init__(
        self,
        llm_api_key: str,
        llm_model: str = "gpt-4",
        style: NarrativeStyle = NarrativeStyle.EXECUTIVE,
    ):
        """
        Initialize narrative generator.

        Args:
            llm_api_key: OpenAI API key
            llm_model: Model to use (gpt-4, gpt-3.5-turbo)
            style: Default writing style
        """
        self.llm_client = OpenAIClient(api_key=llm_api_key, model_name=llm_model)
        self.style = style
        self.logger = logger

        self.logger.info(
            "Narrative generator initialized",
            model=llm_model,
            style=style.value,
        )

    def generate_narrative(
        self,
        insights: List[Any],  # List[Insight]
        context: str = "",
        audience: str = "general",
        style: Optional[NarrativeStyle] = None,
        format: NarrativeFormat = NarrativeFormat.MARKDOWN,
        max_length: int = 2000,
    ) -> Narrative:
        """
        Generate narrative from insights.

        Args:
            insights: List of insights to narrativize
            context: Additional context about the data
            audience: Target audience
            style: Writing style (uses default if not specified)
            format: Output format
            max_length: Maximum length in words

        Returns:
            Generated narrative
        """
        style = style or self.style

        # Build prompt
        prompt = self._build_prompt(insights, context, audience, style, max_length)

        # Generate narrative
        self.logger.info(
            "Generating narrative",
            insights=len(insights),
            style=style.value,
            audience=audience,
        )

        response = self.llm_client.generate_chat(
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt(style),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            max_tokens=max_length * 2,  # Approximate tokens
        )

        # Parse response
        narrative = self._parse_narrative(response, format, insights)

        self.logger.info("Narrative generated", sections=len(narrative.sections))

        return narrative

    def _build_prompt(
        self,
        insights: List[Any],
        context: str,
        audience: str,
        style: NarrativeStyle,
        max_length: int,
    ) -> str:
        """Build prompt for LLM."""
        # Format insights
        insights_text = []
        for i, insight in enumerate(insights, 1):
            insights_text.append(
                f"{i}. **{insight.title}** ({insight.type.value})\n"
                f"   - {insight.description}\n"
                f"   - Confidence: {insight.confidence:.0%}\n"
                f"   - Metrics: {insight.metrics}"
            )

        insights_formatted = "\n\n".join(insights_text)

        prompt = f"""
I need you to create a data story from the following insights.

**Context:** {context or 'General data analysis'}

**Audience:** {audience}

**Style:** {style.value}

**Maximum length:** ~{max_length} words

**Insights to analyze:**

{insights_formatted}

Please create a compelling narrative that:
1. Has a clear title that captures the main theme
2. Starts with an executive summary (2-3 sentences)
3. Organizes insights into logical sections
4. Explains the significance of each finding
5. Provides actionable recommendations
6. Uses clear, {style.value} language

Structure your response as:

# TITLE
[Compelling title here]

# SUMMARY
[2-3 sentence executive summary]

# SECTION_1: [Section Title]
[Content explaining related insights...]

# SECTION_2: [Section Title]
[Content explaining related insights...]

# KEY_FINDINGS
- [Key finding 1]
- [Key finding 2]
- [Key finding 3]

# RECOMMENDATIONS
- [Recommendation 1]
- [Recommendation 2]
- [Recommendation 3]
"""

        return prompt

    def _get_system_prompt(self, style: NarrativeStyle) -> str:
        """Get system prompt based on style."""
        style_prompts = {
            NarrativeStyle.EXECUTIVE: "You are a business analyst creating executive briefings. Be concise, focus on impact, and use business language.",
            NarrativeStyle.DETAILED: "You are a data analyst providing comprehensive analysis. Include context, methodology, and detailed explanations.",
            NarrativeStyle.CASUAL: "You are a data storyteller making insights accessible. Use conversational language and relatable examples.",
            NarrativeStyle.TECHNICAL: "You are a data scientist writing technical analysis. Include statistical details, methodology, and technical accuracy.",
            NarrativeStyle.STORYTELLING: "You are a narrative writer creating engaging data stories. Use compelling language, structure, and flow.",
        }

        return style_prompts.get(
            style,
            "You are a data analyst creating narratives from insights.",
        )

    def _parse_narrative(
        self,
        response: str,
        format: NarrativeFormat,
        insights: List[Any],
    ) -> Narrative:
        """Parse LLM response into Narrative object."""
        lines = response.strip().split("\n")

        title = ""
        summary = ""
        sections = []
        key_findings = []
        recommendations = []

        current_section = None
        current_content = []
        in_findings = False
        in_recommendations = False

        for line in lines:
            line = line.strip()

            if line.startswith("# TITLE"):
                current_section = "title"
                continue
            elif line.startswith("# SUMMARY"):
                current_section = "summary"
                continue
            elif line.startswith("# SECTION_"):
                # Save previous section
                if current_content and current_section and current_section.startswith("section_"):
                    sections.append({
                        "title": current_section.replace("section_", "").replace("_", " ").title(),
                        "content": "\n".join(current_content).strip(),
                    })
                    current_content = []

                # Extract section title
                section_title = line.split(":", 1)[1].strip() if ":" in line else line
                current_section = f"section_{len(sections) + 1}"
                current_content = []
                continue
            elif line.startswith("# KEY_FINDINGS"):
                in_findings = True
                in_recommendations = False
                current_section = "findings"
                continue
            elif line.startswith("# RECOMMENDATIONS"):
                in_recommendations = True
                in_findings = False
                current_section = "recommendations"
                continue

            # Process content based on current section
            if current_section == "title" and line:
                title = line.lstrip("#").strip()
                current_section = None
            elif current_section == "summary" and line:
                summary += line + " "
            elif current_section and current_section.startswith("section_"):
                if line:
                    current_content.append(line)
            elif in_findings and line.startswith("-"):
                key_findings.append(line.lstrip("- ").strip())
            elif in_recommendations and line.startswith("-"):
                recommendations.append(line.lstrip("- ").strip())

        # Save last section
        if current_content and current_section and current_section.startswith("section_"):
            sections.append({
                "title": current_section.replace("section_", "").replace("_", " ").title(),
                "content": "\n".join(current_content).strip(),
            })

        # Default values if parsing failed
        if not title:
            title = "Data Insights Report"
        if not summary:
            summary = f"Analysis of {len(insights)} key insights from the data."
        if not sections:
            sections = [{
                "title": "Findings",
                "content": response,
            }]

        narrative = Narrative(
            title=title,
            summary=summary.strip(),
            sections=sections,
            key_findings=key_findings,
            recommendations=recommendations,
            format=format,
            metadata={
                "insights_count": len(insights),
                "sections_count": len(sections),
            },
        )

        return narrative

    def format_narrative(self, narrative: Narrative, format: NarrativeFormat) -> str:
        """
        Format narrative to specified format.

        Args:
            narrative: Narrative object
            format: Desired output format

        Returns:
            Formatted narrative string
        """
        if format == NarrativeFormat.MARKDOWN:
            return self._format_markdown(narrative)
        elif format == NarrativeFormat.HTML:
            return self._format_html(narrative)
        elif format == NarrativeFormat.PLAIN_TEXT:
            return self._format_plain_text(narrative)
        elif format == NarrativeFormat.JSON:
            import json
            return json.dumps({
                "title": narrative.title,
                "summary": narrative.summary,
                "sections": narrative.sections,
                "key_findings": narrative.key_findings,
                "recommendations": narrative.recommendations,
                "metadata": narrative.metadata,
            }, indent=2)

    def _format_markdown(self, narrative: Narrative) -> str:
        """Format as Markdown."""
        md = f"# {narrative.title}\n\n"
        md += f"## Executive Summary\n\n{narrative.summary}\n\n"

        for section in narrative.sections:
            md += f"## {section['title']}\n\n{section['content']}\n\n"

        if narrative.key_findings:
            md += "## Key Findings\n\n"
            for finding in narrative.key_findings:
                md += f"- {finding}\n"
            md += "\n"

        if narrative.recommendations:
            md += "## Recommendations\n\n"
            for rec in narrative.recommendations:
                md += f"- {rec}\n"
            md += "\n"

        return md

    def _format_html(self, narrative: Narrative) -> str:
        """Format as HTML."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{narrative.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0; }}
        ul {{ line-height: 1.8; }}
    </style>
</head>
<body>
    <h1>{narrative.title}</h1>
    <div class="summary">
        <strong>Executive Summary:</strong> {narrative.summary}
    </div>
"""

        for section in narrative.sections:
            html += f"    <h2>{section['title']}</h2>\n"
            html += f"    <p>{section['content'].replace(chr(10), '<br>')}</p>\n"

        if narrative.key_findings:
            html += "    <h2>Key Findings</h2>\n    <ul>\n"
            for finding in narrative.key_findings:
                html += f"        <li>{finding}</li>\n"
            html += "    </ul>\n"

        if narrative.recommendations:
            html += "    <h2>Recommendations</h2>\n    <ul>\n"
            for rec in narrative.recommendations:
                html += f"        <li>{rec}</li>\n"
            html += "    </ul>\n"

        html += """
</body>
</html>
"""
        return html

    def _format_plain_text(self, narrative: Narrative) -> str:
        """Format as plain text."""
        text = f"{narrative.title}\n"
        text += "=" * len(narrative.title) + "\n\n"
        text += f"EXECUTIVE SUMMARY\n{narrative.summary}\n\n"

        for section in narrative.sections:
            text += f"{section['title'].upper()}\n"
            text += "-" * len(section['title']) + "\n"
            text += f"{section['content']}\n\n"

        if narrative.key_findings:
            text += "KEY FINDINGS\n"
            text += "-" * 12 + "\n"
            for finding in narrative.key_findings:
                text += f"• {finding}\n"
            text += "\n"

        if narrative.recommendations:
            text += "RECOMMENDATIONS\n"
            text += "-" * 15 + "\n"
            for rec in narrative.recommendations:
                text += f"• {rec}\n"
            text += "\n"

        return text
