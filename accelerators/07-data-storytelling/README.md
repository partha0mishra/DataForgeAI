# Accelerator 7: Data Storytelling

Transform raw data and statistical insights into compelling narratives using AI-powered storytelling.

## Overview

The Data Storytelling accelerator automatically extracts insights from data, generates natural language narratives using LLMs, and builds comprehensive reports in multiple formats. It combines statistical analysis with advanced AI to create compelling data stories for different audiences.

## Features

### Insight Extraction
- **Automatic Pattern Detection**: Detects trends, spikes, drops, correlations, outliers, and distributions
- **Statistical Analysis**: Linear regression, Z-scores, Pearson correlation, IQR, skewness
- **Confidence Scoring**: Each insight includes a confidence score (0-1)
- **Visualization Suggestions**: Recommends appropriate chart types for each insight
- **Multiple Insight Types**:
  - Trends (increasing/decreasing patterns)
  - Spikes (sudden increases)
  - Drops (sudden decreases)
  - Correlations (relationships between variables)
  - Outliers (anomalous data points)
  - Distributions (data patterns)
  - Comparisons (category differences)

### Narrative Generation
- **LLM-Powered Stories**: Uses OpenAI GPT-4 to generate natural language narratives
- **Multiple Writing Styles**:
  - Executive: Concise, action-oriented summaries
  - Detailed: Comprehensive technical analysis
  - Casual: Accessible, conversational tone
  - Technical: In-depth statistical explanations
  - Storytelling: Engaging narrative approach
- **Structured Outputs**: Title, summary, sections, key findings, recommendations
- **Context-Aware**: Tailors narrative based on context and target audience
- **Fallback Support**: Works without LLM for basic narratives

### Report Building
- **Complete Reports**: Combines data summary, insights, and narratives
- **Multiple Export Formats**:
  - Markdown (for documentation)
  - HTML (for web display)
  - JSON (for programmatic access)
- **Professional Styling**: Clean, readable HTML with CSS
- **Metadata Tracking**: Report ID, timestamps, dataset information

### REST API
- **FastAPI Implementation**: High-performance async API
- **Multiple Endpoints**:
  - Extract insights from uploaded files
  - Generate narratives from data
  - Create complete HTML/Markdown stories
  - Export reports in different formats
- **OpenAPI Documentation**: Interactive API docs at /docs
- **File Upload Support**: CSV, Parquet, JSON, Excel

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key (for narrative generation)
export OPENAI_API_KEY='your-api-key-here'
```

### Run Example

```bash
cd accelerators/07-data-storytelling
python examples/storytelling_example.py
```

This will:
1. Create sample e-commerce data (365 days)
2. Extract insights (trends, spikes, correlations, outliers)
3. Generate AI-powered narrative
4. Build complete report
5. Export to Markdown, HTML, and JSON

Generated files:
- `examples/sample_ecommerce_data.csv` - Sample data
- `examples/report.md` - Markdown report
- `examples/report.html` - HTML report (open in browser)
- `examples/report.json` - JSON report

### Start API Server

```bash
cd accelerators/07-data-storytelling
uvicorn src.api.main:app --reload --port 8007
```

Visit http://localhost:8007/docs for interactive API documentation.

## Usage

### Extract Insights

```python
from insights import InsightExtractor
import pandas as pd

# Load your data
df = pd.read_csv("data.csv")

# Initialize extractor
extractor = InsightExtractor(confidence_threshold=0.6)

# Extract insights
insights = extractor.extract_insights(df, max_insights=10)

# Display insights
for insight in insights:
    print(f"{insight.title} (confidence: {insight.confidence:.0%})")
    print(f"  {insight.description}")
    print(f"  Suggested viz: {insight.visualization_suggestion}")
```

### Generate Narrative

```python
from narrative import NarrativeGenerator, NarrativeStyle
import os

# Initialize generator
generator = NarrativeGenerator(
    llm_api_key=os.getenv("OPENAI_API_KEY"),
    llm_model="gpt-4",
    style=NarrativeStyle.EXECUTIVE
)

# Generate narrative
narrative = generator.generate_narrative(
    insights=insights,
    context="Q4 2024 Sales Performance",
    audience="executive team",
    style=NarrativeStyle.EXECUTIVE
)

print(f"Title: {narrative.title}")
print(f"Summary: {narrative.summary}")
print("\nKey Findings:")
for finding in narrative.key_findings:
    print(f"  • {finding}")
```

### Build Report

```python
from reports import ReportBuilder

# Initialize builder
builder = ReportBuilder()

# Create report
report = builder.create_report(
    data=df,
    insights=insights,
    narrative=narrative,
    title="Q4 2024 Performance Report"
)

# Export as HTML
html = builder.export_html(report)
with open("report.html", "w") as f:
    f.write(html)

# Export as Markdown
markdown = builder.export_markdown(report)
with open("report.md", "w") as f:
    f.write(markdown)

# Export as JSON
json_output = builder.export_json(report)
with open("report.json", "w") as f:
    f.write(json_output)
```

### API Usage

```bash
# Extract insights from file
curl -X POST "http://localhost:8007/insights/extract" \
  -F "file=@data.csv" \
  -F "max_insights=10" \
  -F "confidence_threshold=0.6"

# Generate narrative
curl -X POST "http://localhost:8007/narrative/generate" \
  -F "file=@data.csv" \
  -F "context=Sales Analysis" \
  -F "audience=executives" \
  -F "style=executive"

# Create complete HTML story
curl -X POST "http://localhost:8007/story/create" \
  -F "file=@data.csv" \
  -F "title=Sales Report" \
  -F "context=Q4 2024" \
  -F "style=executive" \
  > report.html
```

## Configuration

### Insight Extraction

```python
extractor = InsightExtractor(
    confidence_threshold=0.6,  # Minimum confidence for insights (0-1)
)

insights = extractor.extract_insights(
    df,
    max_insights=10,           # Maximum insights to extract
    columns=None,              # Specific columns to analyze (None = all)
)
```

### Narrative Generation

```python
generator = NarrativeGenerator(
    llm_api_key="your-key",
    llm_model="gpt-4",          # Model to use
    style=NarrativeStyle.EXECUTIVE,  # Default style
    temperature=0.7,            # Generation temperature
)

narrative = generator.generate_narrative(
    insights=insights,
    context="",                 # Business context
    audience="general",         # Target audience
    style=NarrativeStyle.DETAILED,  # Override style
    format=NarrativeFormat.MARKDOWN,  # Output format
    max_length=2000,           # Max tokens
)
```

### Report Building

```python
builder = ReportBuilder()

report = builder.create_report(
    data=df,
    insights=insights,
    narrative=narrative,
    title="Report Title",
    summary=None,              # Auto-generated if None
    metadata={}                # Additional metadata
)
```

## API Endpoints

### Insights

- `POST /insights/extract` - Extract insights from uploaded file
  - Parameters: file, max_insights, confidence_threshold
  - Returns: List of insights

### Narrative

- `POST /narrative/generate` - Generate narrative from data
  - Parameters: file, context, audience, style, format, max_length
  - Returns: Generated narrative

### Storytelling

- `POST /story/create` - Create complete HTML story
  - Parameters: file, title, context, audience, style
  - Returns: HTML report

- `POST /story/create/markdown` - Create Markdown story
  - Parameters: file, title, context, audience, style
  - Returns: Markdown report

- `POST /story/create/json` - Create JSON story
  - Parameters: file, title, context, audience, style
  - Returns: JSON report

### Reports

- `POST /reports/export/markdown` - Export report as Markdown
  - Request body: Report object
  - Returns: Markdown text

- `POST /reports/export/html` - Export report as HTML
  - Request body: Report object
  - Returns: HTML text

## Insight Types

### TREND
- Detects increasing/decreasing patterns using linear regression
- Requires R² > 0.5 for significance
- Metrics: slope, r_squared, percent_change
- Visualization: line_chart

### SPIKE
- Detects sudden increases using Z-score analysis
- Requires Z-score > 2 for significance
- Metrics: max_value, mean_value, z_score, percent_increase
- Visualization: line_chart with markers

### DROP
- Detects sudden decreases using Z-score analysis
- Requires Z-score < -2 for significance
- Metrics: min_value, mean_value, z_score, percent_decrease
- Visualization: line_chart with markers

### CORRELATION
- Detects relationships between variables using Pearson correlation
- Requires |r| > 0.7 for significance
- Metrics: correlation_coefficient, p_value
- Visualization: scatter_chart

### OUTLIER
- Detects anomalous data points using IQR method
- Points outside Q1 - 1.5*IQR or Q3 + 1.5*IQR
- Metrics: outlier_count, outlier_percentage, outlier_values
- Visualization: box_plot

### DISTRIBUTION
- Analyzes data distribution using skewness
- Requires |skewness| > 1 for significance
- Metrics: skewness, mean, median, std_dev
- Visualization: histogram

### COMPARISON
- Compares categories for significant differences
- Requires >20% difference for significance
- Metrics: category_values, max_category, min_category, difference_percent
- Visualization: bar_chart

## Narrative Styles

### EXECUTIVE
- Concise, action-oriented
- Focus on key findings and recommendations
- Minimal technical details
- Ideal for: C-suite, board presentations

### DETAILED
- Comprehensive analysis
- Includes statistical details
- Thorough explanations
- Ideal for: Data teams, analysts

### CASUAL
- Accessible language
- Conversational tone
- Minimal jargon
- Ideal for: General audiences, stakeholders

### TECHNICAL
- In-depth statistical analysis
- Methodology explanations
- Technical terminology
- Ideal for: Data scientists, researchers

### STORYTELLING
- Narrative-driven approach
- Engaging flow
- Context and implications
- Ideal for: Presentations, reports

## Export Formats

### Markdown
- Clean, readable text
- GitHub-flavored markdown
- Tables and lists
- Easy to version control

### HTML
- Professional styling
- CSS-formatted
- Browser-ready
- Includes all sections

### JSON
- Programmatic access
- Structured data
- Easy to parse
- Integration-friendly

## Architecture

```
src/
├── insights/
│   └── insight_extractor.py    # Statistical analysis
├── narrative/
│   └── narrative_generator.py  # LLM-powered narrative
├── reports/
│   └── report_builder.py       # Report assembly & export
└── api/
    └── main.py                 # FastAPI REST API
```

## Environment Variables

```bash
# Required for narrative generation
OPENAI_API_KEY=your-openai-api-key

# Optional: Model selection
OPENAI_MODEL=gpt-4  # Default: gpt-4

# Optional: API configuration
API_HOST=0.0.0.0    # Default: 0.0.0.0
API_PORT=8007       # Default: 8007
```

## Deployment

### Docker

```bash
docker build -t dataforge-storytelling .
docker run -p 8007:8007 \
  -e OPENAI_API_KEY=your-key \
  dataforge-storytelling
```

### Kubernetes

```bash
kubectl apply -f k8s/
```

## Performance

- **Insight Extraction**: ~100ms for 1000 rows, ~1s for 100k rows
- **Narrative Generation**: ~5-10s (depends on LLM response time)
- **Report Building**: ~50ms for standard report
- **Export**: <100ms for all formats

## Limitations

- Narrative generation requires OpenAI API key (fallback available)
- Statistical analysis works best with numeric data
- Large datasets (>1M rows) may require sampling
- LLM costs apply for narrative generation

## Future Enhancements

- Support for additional LLM providers (Anthropic, Cohere)
- Custom insight types via plugins
- Interactive HTML reports with charts
- PDF export support
- Scheduled report generation
- Multi-language narrative generation
- Custom narrative templates

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/dataforge-ai
- Documentation: https://docs.dataforge.ai
- API Docs: http://localhost:8007/docs (when running)

## License

MIT License - see LICENSE file for details
