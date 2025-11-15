"""Report builder for creating complete data stories."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Report:
    """Complete data story report."""

    report_id: str
    title: str
    summary: str
    dataset_info: Dict[str, Any]
    insights: List[Any]
    narrative: Any  # Narrative object
    visualizations: List[Dict[str, str]]
    metadata: Dict[str, Any]
    created_at: datetime
    format: str


class ReportBuilder:
    """
    Build complete data story reports.

    Combines:
    - Data summary
    - Insights
    - Narrative
    - Visualizations
    - Formatting

    Example:
        builder = ReportBuilder()

        report = builder.create_report(
            data=df,
            insights=insights,
            narrative=narrative,
            title="Q4 Sales Analysis"
        )

        # Export report
        markdown = builder.export_markdown(report)
        html = builder.export_html(report)
    """

    def __init__(self):
        """Initialize report builder."""
        self.logger = logger
        self.logger.info("Report builder initialized")

    def create_report(
        self,
        data: pd.DataFrame,
        insights: List[Any],
        narrative: Any,
        title: str,
        visualizations: Optional[List[Dict[str, str]]] = None,
    ) -> Report:
        """
        Create complete report.

        Args:
            data: Source DataFrame
            insights: List of insights
            narrative: Generated narrative
            title: Report title
            visualizations: Optional list of visualization specs

        Returns:
            Complete report
        """
        report_id = f"report_{datetime.utcnow().timestamp()}"

        # Generate dataset info
        dataset_info = self._generate_dataset_info(data)

        report = Report(
            report_id=report_id,
            title=title,
            summary=narrative.summary,
            dataset_info=dataset_info,
            insights=insights,
            narrative=narrative,
            visualizations=visualizations or [],
            metadata={
                "created_at": datetime.utcnow().isoformat(),
                "rows": len(data),
                "columns": len(data.columns),
                "insights_count": len(insights),
            },
            created_at=datetime.utcnow(),
            format="markdown",
        )

        self.logger.info("Report created", report_id=report_id, insights=len(insights))

        return report

    def _generate_dataset_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate dataset summary information."""
        return {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_values": df.isnull().sum().to_dict(),
            "memory_usage": df.memory_usage(deep=True).sum(),
        }

    def export_markdown(self, report: Report) -> str:
        """Export report as Markdown."""
        md = f"# {report.title}\n\n"

        # Metadata
        md += f"**Report ID:** {report.report_id}\n\n"
        md += f"**Generated:** {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # Summary
        md += f"## Executive Summary\n\n{report.summary}\n\n"

        # Dataset info
        md += "## Dataset Overview\n\n"
        md += f"- **Rows:** {report.dataset_info['rows']:,}\n"
        md += f"- **Columns:** {report.dataset_info['columns']}\n"
        md += f"- **Column Names:** {', '.join(report.dataset_info['column_names'])}\n\n"

        # Narrative sections
        for section in report.narrative.sections:
            md += f"## {section['title']}\n\n"
            md += f"{section['content']}\n\n"

        # Key findings
        if report.narrative.key_findings:
            md += "## Key Findings\n\n"
            for finding in report.narrative.key_findings:
                md += f"- {finding}\n"
            md += "\n"

        # Recommendations
        if report.narrative.recommendations:
            md += "## Recommendations\n\n"
            for rec in report.narrative.recommendations:
                md += f"- {rec}\n"
            md += "\n"

        # Detailed insights
        md += "## Detailed Insights\n\n"
        for i, insight in enumerate(report.insights, 1):
            md += f"### {i}. {insight.title}\n\n"
            md += f"**Type:** {insight.type.value}\n\n"
            md += f"**Description:** {insight.description}\n\n"
            md += f"**Confidence:** {insight.confidence:.0%}\n\n"
            md += f"**Affected Columns:** {', '.join(insight.affected_columns)}\n\n"

            if insight.metrics:
                md += "**Metrics:**\n"
                for key, value in insight.metrics.items():
                    if isinstance(value, float):
                        md += f"- {key}: {value:.3f}\n"
                    else:
                        md += f"- {key}: {value}\n"
                md += "\n"

        return md

    def export_html(self, report: Report) -> str:
        """Export report as HTML."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{report.title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 35px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        h3 {{
            color: #555;
            margin-top: 25px;
        }}
        .metadata {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary {{
            background: #e8f4f8;
            padding: 20px;
            border-left: 4px solid #3498db;
            margin: 20px 0;
            font-size: 1.1em;
        }}
        .insight {{
            background: #f9f9f9;
            padding: 20px;
            margin: 15px 0;
            border-radius: 5px;
            border-left: 4px solid #95a5a6;
        }}
        .insight-title {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.1em;
        }}
        .confidence {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        .confidence-high {{ background: #2ecc71; color: white; }}
        .confidence-medium {{ background: #f39c12; color: white; }}
        .confidence-low {{ background: #e74c3c; color: white; }}
        ul {{
            line-height: 1.8;
        }}
        .metric {{
            display: inline-block;
            margin: 5px 10px 5px 0;
            padding: 5px 10px;
            background: #ecf0f1;
            border-radius: 3px;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report.title}</h1>

        <div class="metadata">
            <strong>Report ID:</strong> {report.report_id}<br>
            <strong>Generated:</strong> {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Dataset:</strong> {report.dataset_info['rows']:,} rows × {report.dataset_info['columns']} columns
        </div>

        <div class="summary">
            <strong>Executive Summary</strong><br><br>
            {report.summary}
        </div>

        <h2>Dataset Overview</h2>
        <ul>
            <li><strong>Rows:</strong> {report.dataset_info['rows']:,}</li>
            <li><strong>Columns:</strong> {report.dataset_info['columns']}</li>
            <li><strong>Column Names:</strong> {', '.join(report.dataset_info['column_names'])}</li>
        </ul>
"""

        # Narrative sections
        for section in report.narrative.sections:
            html += f"        <h2>{section['title']}</h2>\n"
            html += f"        <p>{section['content'].replace(chr(10), '<br>')}</p>\n"

        # Key findings
        if report.narrative.key_findings:
            html += "        <h2>Key Findings</h2>\n"
            html += "        <ul>\n"
            for finding in report.narrative.key_findings:
                html += f"            <li>{finding}</li>\n"
            html += "        </ul>\n"

        # Recommendations
        if report.narrative.recommendations:
            html += "        <h2>Recommendations</h2>\n"
            html += "        <ul>\n"
            for rec in report.narrative.recommendations:
                html += f"            <li>{rec}</li>\n"
            html += "        </ul>\n"

        # Detailed insights
        html += "        <h2>Detailed Insights</h2>\n"
        for i, insight in enumerate(report.insights, 1):
            confidence_class = (
                "confidence-high" if insight.confidence > 0.8
                else "confidence-medium" if insight.confidence > 0.6
                else "confidence-low"
            )

            html += f"""
        <div class="insight">
            <div class="insight-title">{i}. {insight.title}</div>
            <div style="margin: 10px 0;">
                <strong>Type:</strong> {insight.type.value} &nbsp;
                <span class="confidence {confidence_class}">
                    {insight.confidence:.0%} confidence
                </span>
            </div>
            <p>{insight.description}</p>
            <div>
                <strong>Affected Columns:</strong> {', '.join(insight.affected_columns)}
            </div>
"""

            if insight.metrics:
                html += "            <div style=\"margin-top: 10px;\">\n"
                for key, value in insight.metrics.items():
                    if isinstance(value, float):
                        html += f"                <span class=\"metric\">{key}: {value:.3f}</span>\n"
                    else:
                        html += f"                <span class=\"metric\">{key}: {value}</span>\n"
                html += "            </div>\n"

            html += "        </div>\n"

        html += """
    </div>
</body>
</html>
"""
        return html

    def export_json(self, report: Report) -> str:
        """Export report as JSON."""
        import json

        report_dict = {
            "report_id": report.report_id,
            "title": report.title,
            "summary": report.summary,
            "created_at": report.created_at.isoformat(),
            "dataset_info": report.dataset_info,
            "narrative": {
                "sections": report.narrative.sections,
                "key_findings": report.narrative.key_findings,
                "recommendations": report.narrative.recommendations,
            },
            "insights": [
                {
                    "type": insight.type.value,
                    "title": insight.title,
                    "description": insight.description,
                    "confidence": insight.confidence,
                    "metrics": insight.metrics,
                    "affected_columns": insight.affected_columns,
                }
                for insight in report.insights
            ],
            "metadata": report.metadata,
        }

        return json.dumps(report_dict, indent=2)
