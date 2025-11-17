# Accelerator 27: Data Sharing & Collaboration

## Overview
Enable secure data sharing and collaboration across organizations with governed data exchange agreements.

## Features
- **Sharing Agreements**: Create and manage data sharing contracts between organizations
- **Data Asset Management**: Track which datasets are shared
- **Agreement Lifecycle**: Activate/deactivate sharing agreements
- **Terms & Conditions**: Define sharing terms and compliance requirements

## API Endpoints
- `POST /api/v1/agreements` - Create sharing agreement
- `GET /api/v1/agreements/{id}` - Get agreement details
- `DELETE /api/v1/agreements/{id}` - Deactivate agreement
- `GET /health` - Health check

## Quick Start

### Using Docker
```bash
docker build -t accelerator-27 .
docker run -p 8027:8027 accelerator-27
```

### Local Development
```bash
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8027
```

### Running Tests
```bash
pytest tests/ -v --cov=src
```

## Database Models
- **SharingAgreement**: Tracks data sharing agreements between organizations

## Dependencies
- FastAPI 0.109.0
- SQLAlchemy 2.0.25
- Pydantic 2.5.3
