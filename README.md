# DataForge AI Platform

**AI-Powered Data and Analytics Platform**

DataForge AI is an enterprise-grade, modular data platform that combines traditional data engineering with cutting-edge AI/ML capabilities to accelerate data-driven decision making.

## Architecture Overview

DataForge AI consists of 11 integrated accelerators built on a hybrid monorepo architecture:

### Core Accelerators (Monorepo)
1. **Pipeline Automation** - Intelligent data ingestion and transformation
2. **Data Quality & Governance** - Automated quality checks and compliance
3. **Knowledge Repository** - GenAI-powered documentation and search
4. **Data Catalog** - AI-enhanced metadata management
5. **Model Factory** - Automated ML model development and deployment
6. **BI Dashboarding** - Dynamic visualization and reporting
7. **Data Storytelling** - Automated narrative generation

### Optional Accelerators (Separate Repos)
8. **Conversational Analytics** - Natural language querying
9. **Business Process Optimization** - Process mining and simulation
10. **Data Monetization** - API marketplace and billing
11. **Proposal Accelerator** - AI-powered sales enablement

## Technology Stack

- **Orchestration**: Apache Airflow, Kubernetes
- **Data Processing**: Apache Spark, dbt
- **Data Quality**: Great Expectations, Soda
- **ML/AI**: MLflow, Kubeflow, PyTorch, TensorFlow
- **GenAI**: xAI Grok API, OpenAI, LangChain
- **Storage**: Delta Lake, S3, PostgreSQL
- **Monitoring**: OpenTelemetry, Prometheus, Grafana
- **Languages**: Python 3.11+, SQL, YAML

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Kubernetes cluster (for production)
- AWS/Azure/GCP account (optional)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/yourorg/dataforge-platform.git
cd dataforge-platform

# Install dependencies
make install

# Start all services locally
make dev-up

# Run tests
make test

# Access services:
# - Airflow UI: http://localhost:8080
# - MLflow UI: http://localhost:5000
# - Superset: http://localhost:8088
# - Knowledge Repository: http://localhost:3000
```

### Production Deployment

```bash
# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Deploy to Kubernetes
make deploy-prod

# Or deploy specific accelerator
make deploy-accelerator ACC=01-pipeline-automation
```

## Project Structure

```
dataforge-platform/
├── shared/                    # Shared libraries
│   ├── common/               # Auth, logging, monitoring
│   ├── connectors/           # Data source connectors
│   ├── ai-core/              # GenAI utilities
│   └── data-contracts/       # Schemas and interfaces
├── accelerators/             # Core accelerators
│   ├── 01-pipeline-automation/
│   ├── 02-data-quality-governance/
│   ├── 03-knowledge-repository/
│   ├── 04-data-catalog/
│   ├── 05-model-factory/
│   ├── 08-bi-dashboarding/
│   └── 09-data-storytelling/
├── platform-services/        # Infrastructure services
│   ├── api-gateway/
│   ├── auth-service/
│   ├── monitoring/
│   └── logging/
├── deployments/              # Environment configs
│   ├── local/
│   ├── dev/
│   ├── staging/
│   └── production/
└── terraform/                # Infrastructure as Code
```

## Configuration

### Environment Variables

```bash
# Core Platform
DATAFORGE_ENV=development
DATAFORGE_LOG_LEVEL=INFO

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dataforge
POSTGRES_USER=dataforge
POSTGRES_PASSWORD=changeme

# GenAI
XAI_API_KEY=your-xai-api-key
OPENAI_API_KEY=your-openai-api-key

# Cloud Providers
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_DEFAULT_REGION=us-east-1

# Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## Development

### Adding a New Accelerator

```bash
# Create accelerator structure
make create-accelerator NAME=my-accelerator

# Install dependencies
cd accelerators/my-accelerator
poetry install

# Run tests
pytest tests/

# Build Docker image
docker build -t dataforge/my-accelerator:latest .
```

### Shared Library Development

```python
# Use shared libraries in your code
from dataforge_common.auth import get_jwt_token
from dataforge_common.logging import get_logger
from dataforge_connectors.databases import PostgreSQLConnector
from dataforge_ai_core.llm_clients import GrokClient

logger = get_logger(__name__)
db = PostgreSQLConnector(host="localhost")
llm = GrokClient(api_key="your-key")
```

## Testing

```bash
# Run all tests
make test

# Run specific accelerator tests
make test-accelerator ACC=01-pipeline-automation

# Run integration tests
make test-integration

# Run with coverage
make test-coverage
```

## Monitoring & Observability

Access monitoring dashboards:
- **Grafana**: http://localhost:3001
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686

## Documentation

- [Architecture Guide](docs/architecture/README.md)
- [API Reference](docs/api-reference/README.md)
- [Deployment Guide](docs/deployment-guide/README.md)
- [Developer Guide](docs/developer-guide/README.md)
- [Accelerator Guides](docs/accelerators/README.md)

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes and add tests
3. Run tests: `make test`
4. Commit: `git commit -m "Add my feature"`
5. Push: `git push origin feature/my-feature`
6. Create a Pull Request

## License

Apache License 2.0 - See [LICENSE](LICENSE) file for details

## Support

- Documentation: https://docs.dataforge.ai
- Issues: https://github.com/yourorg/dataforge-platform/issues
- Email: support@dataforge.ai

## Roadmap

- [x] Core Pipeline Automation
- [x] Data Quality Framework
- [x] Knowledge Repository
- [ ] Advanced ML AutoML capabilities
- [ ] Real-time streaming analytics
- [ ] Multi-tenant support
- [ ] Marketplace for data products

---

**Built with ❤️ by the DataForge AI Team**
