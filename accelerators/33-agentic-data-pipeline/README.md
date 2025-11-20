# 🚀 Agentic Data Pipeline Generator

**DataForgeAI Accelerator #33**

> **Generate production-ready data pipelines from natural language using GenAI**

Transform natural language descriptions like *"Ingest CSV from S3 to Snowflake using dbt"* into complete, deployable data pipelines in seconds. Powered by state-of-the-art LLMs (xAI Grok, GPT-4, Claude 3.5, or local models).

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## ✨ Features

### 🤖 **Multi-LLM Support**
- **xAI Grok** (default, optimized for code quality)
- **Azure OpenAI** (GPT-4o, GPT-4 Turbo)
- **AWS Bedrock** (Claude 3.5 Sonnet, Llama 3.1)
- **Local LLM** (via LM Studio or any OpenAI-compatible endpoint)

### 🎯 **What You Get**
Every generation includes:
- ✅ **Complete, runnable code** (Airflow DAGs, dbt models, notebooks, SQL)
- ✅ **Data quality tests** (dbt tests, Great Expectations)
- ✅ **Security best practices** (secret management, encryption, RBAC)
- ✅ **Cost estimates** (monthly USD with breakdown)
- ✅ **Deployment instructions** (step-by-step setup guide)
- ✅ **Architecture documentation** (diagrams, decisions, trade-offs)

### 🏗️ **Supported Platforms & Orchestrators**

| Platform | Orchestrators Supported |
|----------|------------------------|
| **Databricks** | Delta Live Tables, Airflow, dbt |
| **Snowflake** | Snowpark, dbt, Airflow, Dynamic Tables |
| **BigQuery** | Scheduled Queries, dbt, Airflow |
| **Azure Synapse** | Synapse Pipelines, Airflow |
| **AWS Glue** | Step Functions, Airflow |
| **Redshift** | dbt, Airflow |
| **Microsoft Fabric** | Data Factory, dbt |

### 🎨 **Beautiful Interfaces**

1. **Streamlit Web UI** - Intuitive, responsive interface with:
   - LLM configuration sidebar with "Test Connection" button
   - Curated example prompts
   - Syntax-highlighted code preview (multiple files in tabs)
   - Cost estimates and execution time predictions
   - "Refine" feature for iterative improvements
   - One-click ZIP download

2. **FastAPI Backend** - RESTful API for programmatic access

3. **Rich CLI** - Beautiful terminal experience with:
   - Interactive mode
   - Batch generation
   - Connection testing
   - Progress spinners and color output

### 🧠 **Advanced Features**

- **RAG (Retrieval-Augmented Generation)**: Learns from past successful generations
- **Few-Shot Learning**: Includes 10+ curated examples for consistent quality
- **Structured Output**: Guaranteed valid JSON with Pydantic validation
- **Database Logging**: Tracks all generations with user ratings for continuous improvement
- **Docker Ready**: One-command deployment with `docker-compose up`

---

## 📸 Screenshots

### Streamlit UI
```
┌─────────────────────────────────────────────────────────────┐
│  🚀 Agentic Data Pipeline Generator                         │
│  Generate production-ready data pipelines from natural     │
│  language using GenAI                                        │
├─────────────────────────────────────────────────────────────┤
│  🎯 Describe your data pipeline:                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Ingest daily CSV sales files from S3, cleanse them, │  │
│  │ and load into Snowflake using dbt with medallion    │  │
│  │ architecture                                          │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                              │
│  ✨ Generate Pipeline    🔄 Refine                          │
├─────────────────────────────────────────────────────────────┤
│  📋 Pipeline Overview                                       │
│  Platform: Snowflake | Orchestrator: Airflow | Cost: $120  │
│                                                              │
│  📄 Generated Files:                                        │
│  [dags/pipeline.py] [dbt/models/silver.sql] [tests/...]    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/agentic-data-pipeline.git
cd agentic-data-pipeline

# Configure environment
cp .env.example .env
# Edit .env and add your LLM API keys

# Start all services
docker-compose up -d

# Access the UI
open http://localhost:8501

# Access the API docs
open http://localhost:8000/docs
```

### Option 2: Local Installation

```bash
# Clone and navigate
git clone https://github.com/your-org/agentic-data-pipeline.git
cd agentic-data-pipeline

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys

# Start Streamlit UI
streamlit run src/agentic_data_pipeline/ui.py

# Or use CLI
agentic-pipeline generate --prompt "Your pipeline description here"

# Or start API server
uvicorn agentic_data_pipeline.api:app --reload
```

---

## 🎓 Usage Examples

### Example 1: Streamlit UI

1. Launch UI: `streamlit run src/agentic_data_pipeline/ui.py`
2. Select LLM provider in sidebar (e.g., xAI)
3. Click "🔌 Test Connection" to verify
4. Choose a curated example OR write custom prompt
5. Click "✨ Generate Pipeline"
6. Review generated code, download ZIP, or refine

### Example 2: CLI

```bash
# Interactive mode (guided prompts)
agentic-pipeline interactive

# Direct generation
agentic-pipeline generate \
  --prompt "Ingest Shopify orders via API to Databricks Delta Lake" \
  --provider xai \
  --output-dir ./my_pipeline

# Test LLM connection
agentic-pipeline test-llm --provider azure_openai

# List example prompts
agentic-pipeline list-examples
```

### Example 3: API

```python
import requests

response = requests.post("http://localhost:8000/api/generate", json={
    "prompt": "Real-time fraud detection from Kinesis to Snowflake",
    "include_tests": True,
    "include_docs": True
})

pipeline = response.json()["pipeline"]
print(f"Generated: {pipeline['pipeline_name']}")
print(f"Cost: ${pipeline['estimated_monthly_cost_usd']}/month")

# Download files programmatically
for file in pipeline["files"]:
    with open(file["path"], "w") as f:
        f.write(file["content"])
```

---

## 🎯 10 Curated Examples

Each example includes full code, tests, and detailed README:

1. **[s3_csv_to_snowflake_dbt](examples/s3_csv_to_snowflake_dbt/)** - Classic batch ETL with medallion architecture
2. **[shopify_api_to_databricks_delta_live](examples/shopify_api_to_databricks_delta_live/)** - Near-real-time API ingestion
3. **[oracle_cdc_to_snowflake](examples/oracle_cdc_to_snowflake/)** - Legacy database migration with CDC
4. **[multi_source_medallion_databricks](examples/multi_source_medallion_databricks/)** - Multi-source lakehouse (Kafka + PostgreSQL)
5. **[kinesis_fraud_detection_realtime](examples/kinesis_fraud_detection_realtime/)** - Low-latency streaming fraud detection
6. **[snowpark_python_native](examples/snowpark_python_native/)** - Snowflake-native Python processing
7. **[ga4_to_bigquery_looker](examples/ga4_to_bigquery_looker/)** - Marketing analytics pipeline
8. **[serverless_glue_athena](examples/serverless_glue_athena/)** - Cost-optimized serverless on AWS
9. **[secure_sqlserver_to_synapse](examples/secure_sqlserver_to_synapse/)** - Enterprise security & governance
10. **[feature_store_churn_with_embeddings](examples/feature_store_churn_with_embeddings/)** - ML features + LLM embeddings

---

## ⚙️ Configuration

### LLM Providers

#### xAI / Grok (Default)
```bash
# .env
LLM_PROVIDER=xai
XAI_API_KEY=your-xai-api-key
XAI_MODEL=grok-beta
```

#### Azure OpenAI
```bash
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

#### AWS Bedrock
```bash
LLM_PROVIDER=aws_bedrock
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

#### Local LLM (LM Studio)
```bash
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_MODEL=local-model
```

### Advanced Settings

Edit `config.yaml`:

```yaml
llm:
  temperature: 0.0  # 0 = deterministic, 1 = creative
  max_tokens: 8000
  timeout: 120

generation:
  cost_estimates:
    databricks_serverless_per_dbu: 0.70
    snowflake_standard_per_credit: 4.00
    # ... customize pricing

rag:
  enabled: true
  top_k_results: 3
  similarity_threshold: 0.7
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐       │
│  │  Streamlit   │  │   FastAPI    │  │    CLI      │       │
│  │     UI       │  │     API      │  │   (Typer)   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘       │
└─────────┼──────────────────┼─────────────────┼──────────────┘
          │                  │                 │
          └──────────────────┼─────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Core Generator  │
                    │  (core.py)       │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │ LLM Client │   │   Prompt    │   │     RAG     │
    │ (xAI, GPT, │   │  Manager    │   │  (Chroma)   │
    │ Claude, etc)│   │             │   │             │
    └────────────┘   └─────────────┘   └─────────────┘
                             │
                    ┌────────▼─────────┐
                    │    Database      │
                    │   (SQLite/PG)    │
                    │  + User Ratings  │
                    └──────────────────┘
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agentic_data_pipeline --cov-report=html

# Test specific provider
pytest -k "test_xai"

# Integration tests
pytest tests/integration/
```

---

## 📚 Documentation

- **[API Reference](docs/api.md)** - Complete API documentation
- **[Configuration Guide](docs/configuration.md)** - All config options explained
- **[Prompt Engineering](docs/prompting.md)** - Writing effective prompts
- **[Custom Examples](docs/custom_examples.md)** - Adding your own templates
- **[Deployment Guide](docs/deployment.md)** - Production deployment best practices

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style guidelines
- How to add new LLM providers
- How to add new platform support
- How to contribute example pipelines

---

## 🛣️ Roadmap

### Q1 2025
- [x] Multi-LLM support (xAI, Azure OpenAI, Bedrock, Local)
- [x] 10 curated examples
- [x] RAG for learning from past generations
- [ ] GitHub Actions for CI/CD generation
- [ ] VS Code extension

### Q2 2025
- [ ] One-click deployment to Databricks/Snowflake/BigQuery
- [ ] Cost optimization recommendations
- [ ] Pipeline performance profiling
- [ ] Terraform/CloudFormation IaC generation
- [ ] Multi-language support (Java, Scala for Spark)

### Q3 2025
- [ ] Real-time collaboration (multiple users)
- [ ] Pipeline versioning and diff
- [ ] A/B testing for prompts
- [ ] Enterprise SSO integration

---

## 📊 Cost Comparison

| Method | Time to Build | Lines of Code | Cost/Month | Maintenance |
|--------|--------------|---------------|------------|-------------|
| **Manual Coding** | 2-5 days | 500-2000 | $0 | High |
| **Copy-Paste Templates** | 4-8 hours | 300-800 | $0 | Medium |
| **Agentic Generator** | **2-5 minutes** | **Auto-generated** | **$5-20** (LLM API) | **Minimal** |

---

## 🙏 Acknowledgments

Built with:
- [LangChain](https://python.langchain.com/) for LLM orchestration
- [Streamlit](https://streamlit.io/) for beautiful UIs
- [FastAPI](https://fastapi.tiangolo.com/) for API
- [ChromaDB](https://www.trychroma.com/) for RAG
- [Pydantic](https://pydantic.dev/) for data validation

Inspired by:
- The amazing data engineering community
- Enterprise clients struggling with boilerplate code
- The vision of AI-assisted software development

---

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/agentic-data-pipeline/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/agentic-data-pipeline/discussions)
- **Email**: support@dataforgeai.com

---

## ⭐ Star History

If this project helps you, please consider giving it a ⭐! It helps us prioritize new features and improvements.

---

**Made with ❤️ by the DataForgeAI Team**

*Accelerate your data engineering, one pipeline at a time.*
