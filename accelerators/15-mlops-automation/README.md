# MLOps Automation Accelerator

Production-ready MLOps platform for automated model lifecycle management with MLflow integration, multi-strategy deployments, and statistical drift detection.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 16+ (if running without Docker)

### Option 1: Docker Compose (Recommended)

```bash
# Clone and navigate to the accelerator
cd accelerators/15-mlops-automation

# Start all services (API, PostgreSQL, MLflow, Redis)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f mlops-api
```

**Services will be available at:**
- MLOps API: http://localhost:8015
- API Documentation: http://localhost:8015/docs
- MLflow UI: http://localhost:5000
- Prometheus: http://localhost:9090 (with `--profile monitoring`)
- Grafana: http://localhost:3000 (with `--profile monitoring`)

### Option 2: Local Development

```bash
# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn src.main:app --reload --port 8015
```

## 📚 API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8015/docs
- **ReDoc**: http://localhost:8015/redoc

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    MLOps Automation API                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │  Models    │ │ Deployments│ │ Experiments│              │
│  │ Management │ │ Management │ │  Tracking  │              │
│  └────────────┘ └────────────┘ └────────────┘              │
│  ┌────────────────────────────────────────┐                 │
│  │       Drift Detection Engine           │                 │
│  │  (Statistical Analysis & Auto-Retrain) │                 │
│  └────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
         │              │              │
    ┌────┴────┐    ┌────┴────┐   ┌────┴────┐
    │PostgreSQL│    │ MLflow  │   │  Redis  │
    │    DB    │    │ Server  │   │  Cache  │
    └──────────┘    └──────────┘   └──────────┘
```

### Technology Stack

- **API Framework**: FastAPI 0.109.0
- **Database**: PostgreSQL 16 with SQLAlchemy 2.0
- **ML Tracking**: MLflow 2.9.2
- **Caching**: Redis 7
- **Validation**: Pydantic 2.5
- **Statistics**: SciPy 1.11 (drift detection)
- **Monitoring**: Prometheus + Grafana (optional)

## 🎯 Features

### 1. Model Management (12 endpoints)
- Register models manually or from MLflow runs
- Version management and tracking
- Production promotion with automatic demotion
- Performance metrics tracking
- Multi-model comparison

### 2. Multi-Strategy Deployments (7 endpoints)
- **Blue-Green**: Zero-downtime deployments with instant switch
- **Canary**: Progressive rollouts with 0-100% traffic control
- **Rolling**: Gradual replica updates
- **Shadow**: Production traffic mirroring for validation

### 3. Experiment Tracking (8 endpoints)
- Bi-directional MLflow synchronization
- Run lifecycle management
- Metrics and parameters logging
- Model leaderboards

### 4. Statistical Drift Detection (5 endpoints)
- **Data Drift**: Kolmogorov-Smirnov tests per feature
- **Prediction Drift**: Output distribution analysis
- **Concept Drift**: Performance degradation monitoring
- Auto-retrain triggering on high-severity drift

## 📖 Usage Examples

### Register a Model

```python
import requests

# Register from MLflow run
response = requests.post(
    "http://localhost:8015/api/v1/models/from-mlflow",
    json={
        "mlflow_run_id": "abc123def456",
        "model_name": "fraud_detector",
        "version": "2.0.0"
    }
)
model = response.json()
```

### Create Canary Deployment

```python
# Create canary deployment with 10% traffic
response = requests.post(
    "http://localhost:8015/api/v1/deployments",
    json={
        "model_id": model["model_id"],
        "deployment_name": "fraud-detector-canary",
        "environment": "production",
        "strategy": "canary",
        "replicas": 3,
        "traffic_percentage": 10
    }
)
deployment = response.json()

# Gradually increase traffic
requests.post(
    f"http://localhost:8015/api/v1/deployments/{deployment['deployment_id']}/traffic",
    json={"traffic_percentage": 50}
)
```

### Detect Data Drift

```python
import numpy as np

# Detect drift between training and production data
response = requests.post(
    "http://localhost:8015/api/v1/drift/data-drift",
    json={
        "model_id": model["model_id"],
        "reference_data": reference_data.tolist(),
        "current_data": production_data.tolist(),
        "feature_names": ["age", "amount", "frequency"],
        "threshold": 0.05
    }
)
drift = response.json()

if drift["is_drift_detected"]:
    print(f"Drift detected! Severity: {drift['severity']}")
    print(f"Affected features: {drift['affected_features']}")
    print(f"Recommendations: {drift['recommendations']}")
```

## 🧪 Development

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_model_repository.py -v
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

## 🔧 Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `MLFLOW_TRACKING_URI` | MLflow server URL | `http://localhost:5000` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Secret key for auth | Required |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENVIRONMENT` | Environment name | `development` |

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# Start with monitoring stack
docker-compose --profile monitoring up -d

# Stop all services
docker-compose down

# Remove volumes (clean slate)
docker-compose down -v

# Rebuild after code changes
docker-compose up -d --build

# View logs
docker-compose logs -f mlops-api

# Execute commands in container
docker-compose exec mlops-api alembic upgrade head
```

## 📊 Monitoring

### With Prometheus + Grafana

```bash
# Start with monitoring profile
docker-compose --profile monitoring up -d

# Access Grafana
open http://localhost:3000
# Login: admin / admin

# Access Prometheus
open http://localhost:9090
```

### Health Checks

```bash
# API health
curl http://localhost:8015/health

# MLflow health
curl http://localhost:5000/health

# Database connectivity
docker-compose exec postgres pg_isready -U dataforge
```

## 🚀 Deployment

### Kubernetes

```yaml
# Example deployment (k8s manifest to be created)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlops-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mlops-api
  template:
    metadata:
      labels:
        app: mlops-api
    spec:
      containers:
      - name: mlops-api
        image: dataforge/mlops-api:latest
        ports:
        - containerPort: 8015
```

### Production Considerations

1. **Security**:
   - Change `JWT_SECRET_KEY`
   - Use secure PostgreSQL passwords
   - Enable HTTPS/TLS
   - Implement rate limiting
   - Add authentication/authorization

2. **Scalability**:
   - Horizontal pod autoscaling
   - Database connection pooling
   - Redis for session storage
   - CDN for static assets

3. **Reliability**:
   - Health checks and readiness probes
   - Circuit breakers
   - Retry mechanisms
   - Database backups

4. **Observability**:
   - Structured logging (JSON)
   - Distributed tracing
   - Custom metrics
   - Alerting rules

## 📁 Project Structure

```
accelerators/15-mlops-automation/
├── src/
│   ├── models/          # SQLAlchemy database models
│   ├── repositories/    # Data access layer
│   ├── services/        # Business logic
│   ├── schemas/         # Pydantic schemas
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration
│   └── database.py      # Database connection
├── alembic/             # Database migrations
├── tests/               # Test suite
│   ├── unit/
│   └── integration/
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # Local development stack
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## 📝 License

[Add license information]

## 🆘 Support

- Documentation: http://localhost:8015/docs
- Issues: [GitHub Issues]
- Contact: [Contact information]

## 🔗 Links

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
