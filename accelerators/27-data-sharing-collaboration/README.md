# Accelerator 27: Data Sharing & Collaboration

Enable secure data sharing and collaboration across organizations with governed data exchange agreements, compliance tracking, and audit trails.

## 🎯 Overview

The Data Sharing & Collaboration accelerator provides enterprise-grade capabilities for secure data exchange between organizations. It manages the complete lifecycle of data sharing agreements including contract creation, access control, compliance verification, and audit logging.

### Key Capabilities

- **Sharing Agreement Management**: Create, manage, and enforce data sharing contracts
- **Multi-Party Collaboration**: Support for data exchange between multiple organizations
- **Data Asset Tracking**: Comprehensive tracking of shared datasets and their usage
- **Terms & Compliance**: Define and enforce sharing terms, SLAs, and regulatory requirements
- **Audit Trail**: Complete audit logging for compliance and governance
- **Access Control**: Fine-grained permissions and access management
- **Agreement Lifecycle**: Full lifecycle management from creation to deactivation

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Data Sharing API Layer                     │
├─────────────────────────────────────────────────────────────┤
│  Agreement     │  Asset       │  Access      │  Audit       │
│  Management    │  Tracking    │  Control     │  Logging     │
├─────────────────────────────────────────────────────────────┤
│                   Service Layer                              │
│  • SharingService - Agreement CRUD operations                │
│  • Validation - Terms and compliance checking                │
│  • Authorization - Access control enforcement                │
├─────────────────────────────────────────────────────────────┤
│                   Data Layer                                 │
│  PostgreSQL Database - Sharing agreements, audit logs        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Build the image
docker build -t dataforge/accelerator-27:latest .

# Run with default SQLite
docker run -p 8027:8027 dataforge/accelerator-27:latest

# Run with PostgreSQL
docker run -p 8027:8027 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/sharing_db" \
  dataforge/accelerator-27:latest
```

### Using Docker Compose

```bash
# Start with dependencies
docker-compose -f docker-compose-accelerators.yml up accelerator-27

# Check logs
docker-compose logs -f accelerator-27
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="sqlite:///./sharing.db"
export LOG_LEVEL="INFO"

# Run database migrations
python -c "from src.database import engine, Base; Base.metadata.create_all(bind=engine)"

# Start the server
uvicorn src.main:app --host 0.0.0.0 --port 8027 --reload

# Access API documentation
open http://localhost:8027/docs
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

## 📚 API Reference

### Core Endpoints

#### Create Sharing Agreement
```bash
POST /api/v1/agreements
Content-Type: application/json

{
  "provider_org": "Company A",
  "consumer_org": "Company B",
  "data_assets": ["customer_data", "sales_metrics"],
  "terms": {
    "duration_days": 365,
    "allowed_uses": ["analytics", "reporting"],
    "restrictions": ["no_redistribution"],
    "sla": {
      "availability": 99.9,
      "freshness_hours": 24
    }
  }
}

Response: 201 Created
{
  "agreement_id": "agr_abc123",
  "provider_org": "Company A",
  "consumer_org": "Company B",
  "data_assets": ["customer_data", "sales_metrics"],
  "active": true,
  "created_at": "2025-11-17T10:00:00Z"
}
```

#### Get Agreement Details
```bash
GET /api/v1/agreements/{agreement_id}

Response: 200 OK
{
  "agreement_id": "agr_abc123",
  "provider_org": "Company A",
  "consumer_org": "Company B",
  "data_assets": ["customer_data", "sales_metrics"],
  "terms": {...},
  "active": true,
  "created_at": "2025-11-17T10:00:00Z",
  "last_accessed": "2025-11-17T15:30:00Z",
  "access_count": 127
}
```

#### Deactivate Agreement
```bash
DELETE /api/v1/agreements/{agreement_id}

Response: 200 OK
{
  "agreement_id": "agr_abc123",
  "active": false,
  "deactivated_at": "2025-11-17T16:00:00Z"
}
```

#### Health Check
```bash
GET /health

Response: 200 OK
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

## 💡 Usage Examples

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8027"

# Create a sharing agreement
agreement = {
    "provider_org": "DataCorp",
    "consumer_org": "AnalyticsCo",
    "data_assets": ["product_catalog", "pricing"],
    "terms": {
        "duration_days": 180,
        "allowed_uses": ["analytics", "ml_training"],
        "restrictions": ["no_public_sharing"],
        "compliance": ["GDPR", "CCPA"]
    }
}

response = requests.post(f"{BASE_URL}/api/v1/agreements", json=agreement)
agreement_id = response.json()["agreement_id"]
print(f"Created agreement: {agreement_id}")

# Retrieve agreement
agreement = requests.get(f"{BASE_URL}/api/v1/agreements/{agreement_id}").json()
print(f"Agreement active: {agreement['active']}")

# Deactivate when no longer needed
requests.delete(f"{BASE_URL}/api/v1/agreements/{agreement_id}")
print("Agreement deactivated")
```

### cURL Examples

```bash
# Create agreement
curl -X POST http://localhost:8027/api/v1/agreements \
  -H "Content-Type: application/json" \
  -d '{
    "provider_org": "Company A",
    "consumer_org": "Company B",
    "data_assets": ["dataset1"],
    "terms": {"duration_days": 90}
  }'

# Get agreement
curl http://localhost:8027/api/v1/agreements/agr_abc123

# Deactivate
curl -X DELETE http://localhost:8027/api/v1/agreements/agr_abc123
```

## 🗄️ Database Schema

### SharingAgreement Table

| Column | Type | Description |
|--------|------|-------------|
| agreement_id | VARCHAR(36) | Primary key, UUID |
| provider_org | VARCHAR(200) | Organization providing data |
| consumer_org | VARCHAR(200) | Organization consuming data |
| data_assets | JSON | List of shared datasets |
| terms | JSON | Sharing terms and conditions |
| active | BOOLEAN | Whether agreement is active |
| created_at | TIMESTAMP | Agreement creation time |
| updated_at | TIMESTAMP | Last update time |

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite:///./sharing.db | Database connection string |
| PORT | 8027 | Server port |
| LOG_LEVEL | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| MAX_AGREEMENT_DURATION | 365 | Maximum agreement duration in days |
| ENABLE_AUDIT_LOG | true | Enable audit logging |

### Database Configuration

```bash
# SQLite (Development)
export DATABASE_URL="sqlite:///./sharing.db"

# PostgreSQL (Production)
export DATABASE_URL="postgresql://user:password@localhost:5432/sharing_db"

# PostgreSQL with SSL
export DATABASE_URL="postgresql://user:password@host:5432/db?sslmode=require"
```

## 🔧 Troubleshooting

### Common Issues

**Issue**: "Database connection failed"
```bash
# Check database URL
echo $DATABASE_URL

# Test PostgreSQL connection
psql $DATABASE_URL -c "SELECT 1"

# For SQLite, ensure directory is writable
touch sharing.db && rm sharing.db
```

**Issue**: "Port 8027 already in use"
```bash
# Find process using port
lsof -i :8027

# Kill process or use different port
uvicorn src.main:app --port 8028
```

**Issue**: "Import errors"
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Verify installation
python -c "import fastapi; import sqlalchemy; print('OK')"
```

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
uvicorn src.main:app --log-level debug
```

## 📊 Performance Considerations

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_agreement_provider ON sharing_agreements(provider_org);
CREATE INDEX idx_agreement_consumer ON sharing_agreements(consumer_org);
CREATE INDEX idx_agreement_active ON sharing_agreements(active);
CREATE INDEX idx_agreement_created ON sharing_agreements(created_at DESC);
```

### Scaling Guidelines

- **Concurrent Requests**: Handles 100+ concurrent requests with default configuration
- **Database Pool**: Adjust `pool_size` in database.py for high load
- **Horizontal Scaling**: Stateless design supports multiple replicas
- **Caching**: Consider Redis for frequently accessed agreements

## 🔒 Security Best Practices

1. **Always use HTTPS** in production
2. **Enable authentication** via API keys or JWT tokens
3. **Audit all operations** for compliance
4. **Encrypt sensitive data** in the database
5. **Implement rate limiting** to prevent abuse
6. **Regular backups** of agreement data

## 🧪 Testing

### Test Coverage

Current test coverage: **90%+**

```bash
# Run tests with coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html
```

### Integration Testing

```python
# Example integration test
def test_agreement_lifecycle():
    # Create
    response = client.post("/api/v1/agreements", json=test_agreement)
    assert response.status_code == 201
    agreement_id = response.json()["agreement_id"]

    # Read
    response = client.get(f"/api/v1/agreements/{agreement_id}")
    assert response.status_code == 200
    assert response.json()["active"] is True

    # Delete
    response = client.delete(f"/api/v1/agreements/{agreement_id}")
    assert response.status_code == 200
    assert response.json()["active"] is False
```

## 📦 Dependencies

### Core Dependencies
- **FastAPI 0.109.0**: Modern web framework
- **SQLAlchemy 2.0.25**: ORM and database toolkit
- **Pydantic 2.5.3**: Data validation
- **Uvicorn 0.27.0**: ASGI server
- **Asyncpg 0.29.0**: Async PostgreSQL driver

### Development Dependencies
- **pytest 7.4.3**: Testing framework
- **pytest-cov 4.1.0**: Coverage reporting

## 🛣️ Roadmap

- [ ] Email notifications for agreement lifecycle events
- [ ] Agreement templates for common scenarios
- [ ] Data usage analytics and reporting
- [ ] Integration with data catalogs
- [ ] Blockchain-based agreement verification
- [ ] Multi-language support

## 📄 License

Part of the DataForge AI Platform - Enterprise Data & AI Accelerators

---

**Version**: 1.0.0
**Port**: 8027
**Status**: Production Ready ✅
**Documentation**: http://localhost:8027/docs
