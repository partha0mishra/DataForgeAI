"""Example: Complete data storytelling workflow."""

import os
from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from insights.insight_extractor import InsightExtractor
from narrative.narrative_generator import NarrativeGenerator, NarrativeStyle
from reports.report_builder import ReportBuilder


def print_section(title: str):
    """Print section header."""
    print()
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)
    print()


def create_sample_data():
    """Create sample e-commerce data."""
    print("Creating sample e-commerce data...")

    np.random.seed(42)

    # Generate sales data
    dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")

    data = {
        "date": dates,
        "revenue": np.random.randint(5000, 20000, size=len(dates))
        + np.sin(np.arange(len(dates)) * 2 * np.pi / 365) * 5000
        + np.random.randn(len(dates)) * 1000,
        "orders": np.random.randint(100, 400, size=len(dates)),
        "customers": np.random.randint(80, 350, size=len(dates)),
        "avg_order_value": np.random.uniform(30, 100, size=len(dates)),
        "conversion_rate": np.random.uniform(0.02, 0.08, size=len(dates)),
        "category": np.random.choice(
            ["Electronics", "Clothing", "Home", "Books", "Sports"],
            size=len(dates),
        ),
        "region": np.random.choice(
            ["North", "South", "East", "West"],
            size=len(dates),
        ),
    }

    df = pd.DataFrame(data)

    # Add some trends
    # Revenue growing over time
    df["revenue"] = df["revenue"] + np.arange(len(df)) * 20

    # Add a spike
    df.loc[180:185, "revenue"] *= 1.5
    df.loc[180:185, "orders"] *= 1.4

    # Save to CSV
    output_path = Path(__file__).parent / "sample_ecommerce_data.csv"
    df.to_csv(output_path, index=False)

    print(f"✓ Created {len(df)} rows of sample data")
    print(f"✓ Saved to: {output_path}")
    print()
    print("Data summary:")
    print(df.describe())

    return df, output_path


def main():
    """Run complete data storytelling example."""
    print("=" * 80)
    print(" DataForge Data Storytelling - Complete Example")
    print("=" * 80)

    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print()
        print("WARNING: OPENAI_API_KEY not set!")
        print("Narrative generation will be skipped.")
        print("Set API key with: export OPENAI_API_KEY='your-key'")
        print()

    # Step 1: Create sample data
    print_section("1. Create Sample E-commerce Data")

    df, data_file = create_sample_data()

    # Step 2: Initialize components
    print_section("2. Initialize Data Storytelling Components")

    insight_extractor = InsightExtractor(confidence_threshold=0.6)
    print("✓ Insight extractor initialized")

    report_builder = ReportBuilder()
    print("✓ Report builder initialized")

    if api_key:
        narrative_generator = NarrativeGenerator(
            llm_api_key=api_key,
            llm_model="gpt-4",
            style=NarrativeStyle.EXECUTIVE,
        )
        print("✓ Narrative generator initialized")
    else:
        narrative_generator = None
        print("✗ Narrative generator skipped (no API key)")

    # Step 3: Extract insights
    print_section("3. Extract Insights from Data")

    insights = insight_extractor.extract_insights(df, max_insights=10)

    print(f"✓ Extracted {len(insights)} insights")
    print()
    print("Top insights:")
    for i, insight in enumerate(insights[:5], 1):
        print(f"\n{i}. {insight.title}")
        print(f"   Type: {insight.type.value}")
        print(f"   {insight.description}")
        print(f"   Confidence: {insight.confidence:.0%}")
        print(f"   Visualization: {insight.visualization_suggestion}")

    # Step 4: Generate narrative (if API key available)
    if narrative_generator:
        print_section("4. Generate AI-Powered Narrative")

        narrative = narrative_generator.generate_narrative(
            insights=insights,
            context="Q4 2024 E-commerce Performance Analysis",
            audience="executive team",
            style=NarrativeStyle.EXECUTIVE,
        )

        print(f"✓ Narrative generated")
        print()
        print(f"Title: {narrative.title}")
        print()
        print(f"Summary: {narrative.summary}")
        print()
        print(f"Sections: {len(narrative.sections)}")
        for section in narrative.sections:
            print(f"  - {section['title']}")
        print()
        print(f"Key Findings: {len(narrative.key_findings)}")
        for finding in narrative.key_findings:
            print(f"  • {finding}")
        print()
        print(f"Recommendations: {len(narrative.recommendations)}")
        for rec in narrative.recommendations:
            print(f"  • {rec}")

    else:
        print_section("4. Generate Narrative (SKIPPED - No API Key)")
        # Create a simple narrative without LLM
        from narrative.narrative_generator import Narrative, NarrativeFormat

        narrative = Narrative(
            title="E-commerce Performance Analysis",
            summary="Analysis of key metrics and trends from the e-commerce data.",
            sections=[
                {
                    "title": "Overview",
                    "content": "This report analyzes e-commerce performance data including revenue trends, order patterns, and customer behavior.",
                }
            ],
            key_findings=[insight.title for insight in insights[:3]],
            recommendations=[
                "Monitor identified trends closely",
                "Investigate anomalies and spikes",
                "Optimize based on insights",
            ],
            format=NarrativeFormat.MARKDOWN,
            metadata={"insights_count": len(insights)},
        )
        print("✓ Simple narrative created (without LLM)")

    # Step 5: Build complete report
    print_section("5. Build Complete Report")

    report = report_builder.create_report(
        data=df,
        insights=insights,
        narrative=narrative,
        title="Q4 2024 E-commerce Performance Report",
    )

    print(f"✓ Report created")
    print(f"  Report ID: {report.report_id}")
    print(f"  Title: {report.title}")
    print(f"  Insights: {len(report.insights)}")
    print(f"  Dataset: {report.dataset_info['rows']:,} rows × {report.dataset_info['columns']} columns")

    # Step 6: Export report in multiple formats
    print_section("6. Export Report in Multiple Formats")

    # Export as Markdown
    markdown = report_builder.export_markdown(report)
    md_path = Path(__file__).parent / "report.md"
    md_path.write_text(markdown)
    print(f"✓ Markdown report saved to: {md_path}")
    print(f"  Size: {len(markdown):,} characters")

    # Export as HTML
    html = report_builder.export_html(report)
    html_path = Path(__file__).parent / "report.html"
    html_path.write_text(html)
    print(f"✓ HTML report saved to: {html_path}")
    print(f"  Size: {len(html):,} characters")

    # Export as JSON
    json_output = report_builder.export_json(report)
    json_path = Path(__file__).parent / "report.json"
    json_path.write_text(json_output)
    print(f"✓ JSON report saved to: {json_path}")
    print(f"  Size: {len(json_output):,} characters")

    # Step 7: Display report preview
    print_section("7. Report Preview (First 1000 characters)")

    print(markdown[:1000])
    print("\n... [truncated] ...\n")

    # Final summary
    print_section("Example Complete!")

    print("Summary:")
    print(f"  ✓ Created sample e-commerce dataset ({len(df)} days)")
    print(f"  ✓ Extracted {len(insights)} insights")
    print(f"  ✓ Generated {'AI-powered' if narrative_generator else 'simple'} narrative")
    print(f"  ✓ Built complete report")
    print(f"  ✓ Exported in 3 formats (Markdown, HTML, JSON)")
    print()
    print("Generated files:")
    print(f"  1. {data_file} - Sample data")
    print(f"  2. {md_path} - Markdown report")
    print(f"  3. {html_path} - HTML report")
    print(f"  4. {json_path} - JSON report")
    print()
    print("Insight types found:")
    insight_types = {}
    for insight in insights:
        insight_types[insight.type.value] = insight_types.get(insight.type.value, 0) + 1
    for itype, count in sorted(insight_types.items()):
        print(f"  - {itype}: {count}")
    print()
    print("Next steps:")
    print("  1. View HTML report in browser: open", html_path)
    print("  2. Start API: uvicorn src.api.main:app --reload --port 8006")
    print("  3. Try API at http://localhost:8006/docs")
    print("  4. Upload your own data for storytelling")
    print()


if __name__ == "__main__":
    main()
