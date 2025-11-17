# DataForge AI Platform - Deployment Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Options](#deployment-options)
4. [Quick Start Guide](#quick-start-guide)
5. [Individual Accelerator Deployment](#individual-accelerator-deployment)
6. [Multi-Accelerator Deployment](#multi-accelerator-deployment)
7. [Production Deployment](#production-deployment)
8. [Configuration Management](#configuration-management)
9. [Monitoring & Operations](#monitoring--operations)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The DataForge AI Platform consists of 32 independent accelerators, each deployable as a microservice. This guide covers all deployment scenarios from local development to production-grade enterprise deployments.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer / API Gateway             │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
┌─────────────▼──┐  ┌────────▼────┐  ┌──────▼─────────┐
│ Accelerator 1  │  │ Accelerator │  │ Accelerator 32 │
│ (Port 8001)    │  │    ...      │  │ (Port 8032)    │
└────────┬───────┘  └──────┬──────┘  └────────┬───────┘
         │                 │                   │
         └─────────────────┼───────────────────┘
                           │
              ┌────────────▼────────────┐
              │   PostgreSQL Database   │
              │   (or SQLite for dev)   │
              └─────────────────────────┘
```

---

## Prerequisites

### Minimum Requirements

**Hardware:**
- **CPU:** 4 cores minimum, 8+ cores recommended
- **RAM:** 8GB minimum, 16GB+ recommended
- **Storage:** 50GB minimum, 100GB+ recommended for production
- **Network:** Stable internet connection for Docker image pulls

**Software:**
- **Docker:** Version 20.10 or higher
- **Docker Compose:** Version 2.0 or higher
- **Python:** 3.11+ (for local development)
- **Git:** For cloning the repository

### Optional Requirements

- **Kubernetes:** v1.24+ (for K8s deployment)
- **PostgreSQL:** 13+ (for production)
- **Redis:** 7+ (for caching - optional)
- **Nginx/Traefik:** For reverse proxy

### Verification

```bash
# Check Docker
docker --version
# Expected: Docker version 20.10.x or higher

# Check Docker Compose
docker-compose --version
# Expected: Docker Compose version 2.x.x

# Check Python (for local development)
python3 --version
# Expected: Python 3.11.x or higher

# Check available resources
docker system info | grep -E "CPUs|Total Memory"
```

---

## Deployment Options

### Option 1: Local Development (Single Accelerator)
**Best for:** Development, testing, learning
```bash
cd accelerators/01-*
pip install -r requirements.txt
uvicorn src.main:app --reload
```

### Option 2: Docker (Single Accelerator)
**Best for:** Isolated testing, CI/CD, development
```bash
docker build -t accelerator-01 accelerators/01-*/
docker run -p 8001:8001 accelerator-01
```

### Option 3: Docker Compose (Multiple Accelerators)
**Best for:** Integration testing, staging environments
```bash
docker-compose -f docker-compose-accelerators.yml up -d
```

### Option 4: Kubernetes (Production)
**Best for:** Production, high availability, auto-scaling
```bash
kubectl apply -f k8s/accelerators/
```

---

## Quick Start Guide

### 1. Clone Repository

```bash
git clone https://github.com/your-org/DataForgeAI.git
cd DataForgeAI
```

### 2. Choose Your Deployment Method

#### Quick Start: Single Accelerator with Docker

```bash
# Build and run Accelerator 27 (Data Sharing)
docker build -t dataforge-sharing accelerators/27-data-sharing-collaboration/
docker run -d \
  --name sharing-service \
  -p 8027:8027 \
  -e DATABASE_URL=sqlite:///./app.db \
  dataforge-sharing

# Verify it's running
curl http://localhost:8027/health
```

#### Quick Start: All Accelerators with Docker Compose

```bash
# Start all accelerators (27-32)
docker-compose -f docker-compose-accelerators.yml up -d

# View logs
docker-compose -f docker-compose-accelerators.yml logs -f

# Check status
docker-compose -f docker-compose-accelerators.yml ps

# Access any accelerator
curl http://localhost:8027/health  # Accelerator 27
curl http://localhost:8028/health  # Accelerator 28
curl http://localhost:8032/health  # Accelerator 32
```

### 3. Access Documentation

```bash
# Open API documentation for any accelerator
open http://localhost:8027/docs  # Swagger UI
open http://localhost:8027/redoc # ReDoc
```

---

## Individual Accelerator Deployment

### Template for Any Accelerator

Replace `XX` with accelerator number (01-32):

#### Local Development

```bash
# Navigate to accelerator directory
cd accelerators/XX-*/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="sqlite:///./app.db"
export LOG_LEVEL="debug"

# Run the application
uvicorn src.main:app --host 0.0.0.0 --port 80XX --reload

# In another terminal, run tests
pytest tests/ -v --cov=src
```

#### Docker Deployment

```bash
# Build image
docker build -t dataforge-acc-XX accelerators/XX-*/

# Run container
docker run -d \
  --name accelerator-XX \
  -p 80XX:80XX \
  -e DATABASE_URL=sqlite:///./app.db \
  -e LOG_LEVEL=info \
  -v $(pwd)/data:/app/data \
  dataforge-acc-XX

# View logs
docker logs -f accelerator-XX

# Stop container
docker stop accelerator-XX

# Remove container
docker rm accelerator-XX
```

#### Docker with PostgreSQL

```bash
# Start PostgreSQL
docker run -d \
  --name postgres-dataforge \
  -e POSTGRES_PASSWORD=dataforge123 \
  -e POSTGRES_DB=dataforge \
  -p 5432:5432 \
  postgres:15

# Run accelerator with PostgreSQL
docker run -d \
  --name accelerator-XX \
  --link postgres-dataforge:postgres \
  -p 80XX:80XX \
  -e DATABASE_URL="postgresql://postgres:dataforge123@postgres:5432/dataforge" \
  -e LOG_LEVEL=info \
  dataforge-acc-XX
```

---

## Multi-Accelerator Deployment

### Using Docker Compose

#### Start All Accelerators (27-32)

```bash
# Start all services
docker-compose -f docker-compose-accelerators.yml up -d

# Check status
docker-compose -f docker-compose-accelerators.yml ps

# View logs for all services
docker-compose -f docker-compose-accelerators.yml logs -f

# View logs for specific service
docker-compose -f docker-compose-accelerators.yml logs -f accelerator-27-sharing
```

#### Start Specific Accelerators

```bash
# Start only accelerators 27 and 28
docker-compose -f docker-compose-accelerators.yml up -d \
  accelerator-27-sharing \
  accelerator-28-graph

# Scale accelerators (if needed)
docker-compose -f docker-compose-accelerators.yml up -d --scale accelerator-27-sharing=3
```

#### Stop Services

```bash
# Stop all services
docker-compose -f docker-compose-accelerators.yml down

# Stop and remove volumes
docker-compose -f docker-compose-accelerators.yml down -v
```

### Custom Docker Compose Configuration

Create `docker-compose.custom.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD:-dataforge123}
      POSTGRES_DB: dataforge
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Accelerator 27
  accelerator-27:
    build: ./accelerators/27-data-sharing-collaboration
    ports:
      - "8027:8027"
    environment:
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD:-dataforge123}@postgres:5432/dataforge
      LOG_LEVEL: info
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
```

Usage:
```bash
docker-compose -f docker-compose.custom.yml up -d
```

---

## Production Deployment

### Production Checklist

- [ ] Use PostgreSQL (not SQLite)
- [ ] Enable SSL/TLS
- [ ] Set up proper logging
- [ ] Configure monitoring
- [ ] Set up backups
- [ ] Use secrets management
- [ ] Configure load balancing
- [ ] Set up health checks
- [ ] Enable auto-restart
- [ ] Configure resource limits

### Production Docker Deployment

```bash
# Build production image
docker build \
  --build-arg ENV=production \
  -t dataforge-acc-27:1.0.0 \
  accelerators/27-data-sharing-collaboration/

# Run with production settings
docker run -d \
  --name acc-27-prod \
  -p 8027:8027 \
  --restart unless-stopped \
  --memory="2g" \
  --cpus="2" \
  -e DATABASE_URL="postgresql://user:pass@prod-db:5432/dataforge" \
  -e LOG_LEVEL=warning \
  -e WORKERS=4 \
  -e MAX_REQUESTS=1000 \
  -e MAX_REQUESTS_JITTER=100 \
  -v /var/log/dataforge:/app/logs \
  dataforge-acc-27:1.0.0

# Monitor logs
docker logs -f acc-27-prod
```

### Kubernetes Deployment

Create `k8s/accelerator-27-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: accelerator-27
  labels:
    app: dataforge
    accelerator: sharing
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dataforge
      accelerator: sharing
  template:
    metadata:
      labels:
        app: dataforge
        accelerator: sharing
    spec:
      containers:
      - name: sharing-service
        image: dataforge-acc-27:1.0.0
        ports:
        - containerPort: 8027
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dataforge-secrets
              key: database-url
        - name: LOG_LEVEL
          value: "info"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8027
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8027
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: accelerator-27-service
spec:
  selector:
    app: dataforge
    accelerator: sharing
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8027
  type: LoadBalancer
```

Deploy:
```bash
# Apply deployment
kubectl apply -f k8s/accelerator-27-deployment.yaml

# Check status
kubectl get pods -l accelerator=sharing
kubectl get services

# View logs
kubectl logs -f deployment/accelerator-27

# Scale deployment
kubectl scale deployment/accelerator-27 --replicas=5
```

### Using Helm (Recommended for K8s)

```bash
# Install Helm chart
helm install dataforge-acc-27 ./helm/accelerator-27 \
  --set replicaCount=3 \
  --set image.tag=1.0.0 \
  --set database.url="postgresql://..." \
  --namespace dataforge \
  --create-namespace

# Upgrade deployment
helm upgrade dataforge-acc-27 ./helm/accelerator-27

# Rollback
helm rollback dataforge-acc-27

# Uninstall
helm uninstall dataforge-acc-27
```

---

## Configuration Management

### Environment Variables

Common environment variables for all accelerators:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Database connection string | `sqlite:///./app.db` | Yes |
| `LOG_LEVEL` | Logging level (debug, info, warning, error) | `info` | No |
| `WORKERS` | Number of worker processes | `1` | No |
| `HOST` | Host to bind to | `0.0.0.0` | No |
| `PORT` | Port to listen on | `80XX` | No |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | No |
| `API_PREFIX` | API route prefix | `/api/v1` | No |
| `MAX_REQUESTS` | Max requests before worker restart | `1000` | No |

### Database Configuration

#### SQLite (Development)
```bash
export DATABASE_URL="sqlite:///./app.db"
```

#### PostgreSQL (Production)
```bash
export DATABASE_URL="postgresql://user:password@host:5432/database"
```

#### Connection Pool Settings
```bash
export DB_POOL_SIZE=20
export DB_MAX_OVERFLOW=40
export DB_POOL_TIMEOUT=30
export DB_POOL_RECYCLE=3600
```

### Secrets Management

#### Using Docker Secrets

```bash
# Create secrets
echo "postgresql://user:pass@host:5432/db" | docker secret create db_url -

# Use in service
docker service create \
  --name accelerator-27 \
  --secret db_url \
  -e DATABASE_URL_FILE=/run/secrets/db_url \
  dataforge-acc-27:1.0.0
```

#### Using Kubernetes Secrets

```bash
# Create secret
kubectl create secret generic dataforge-secrets \
  --from-literal=database-url='postgresql://...' \
  --from-literal=api-key='your-api-key'

# Reference in deployment (see K8s section above)
```

---

## Monitoring & Operations

### Health Checks

All accelerators expose a health endpoint:

```bash
# Check health
curl http://localhost:8027/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-17T10:30:00Z"
}
```

### Logging

#### View Logs (Docker)

```bash
# View all logs
docker logs accelerator-27

# Follow logs
docker logs -f accelerator-27

# Last 100 lines
docker logs --tail 100 accelerator-27

# Since timestamp
docker logs --since 2025-11-17T10:00:00 accelerator-27
```

#### View Logs (Docker Compose)

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f accelerator-27-sharing

# Timestamps
docker-compose logs -f --timestamps
```

#### Log Aggregation

Configure centralized logging with ELK stack:

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"

  logstash:
    image: logstash:8.11.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

  kibana:
    image: kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

### Metrics & Monitoring

#### Prometheus Integration

Add to accelerator code:
```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
request_count = Counter('http_requests_total', 'Total requests')
request_duration = Histogram('http_request_duration_seconds', 'Request duration')

# Expose metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

#### Grafana Dashboards

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3000
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Problem:** `Error: Port 8027 is already in use`

**Solution:**
```bash
# Find process using port
lsof -i :8027
# or
netstat -tulpn | grep 8027

# Kill process
kill -9 <PID>

# Or use different port
docker run -p 8028:8027 dataforge-acc-27
```

#### 2. Database Connection Failed

**Problem:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solution:**
```bash
# Check database is running
docker ps | grep postgres

# Test connection
psql -h localhost -U postgres -d dataforge

# Verify DATABASE_URL
echo $DATABASE_URL

# Check network connectivity (Docker)
docker network inspect bridge
```

#### 3. Out of Memory

**Problem:** Container killed due to OOM

**Solution:**
```bash
# Increase Docker memory limit
docker run --memory="2g" --memory-swap="4g" ...

# Check memory usage
docker stats

# Reduce workers
docker run -e WORKERS=2 ...
```

#### 4. Image Build Fails

**Problem:** Docker build error

**Solution:**
```bash
# Clean Docker cache
docker builder prune -a

# Build with no cache
docker build --no-cache -t dataforge-acc-27 .

# Check Dockerfile syntax
docker build --check -t dataforge-acc-27 .
```

### Debugging

#### Enable Debug Logging

```bash
# Set debug log level
docker run -e LOG_LEVEL=debug dataforge-acc-27

# View detailed logs
docker logs -f accelerator-27
```

#### Access Container Shell

```bash
# Exec into running container
docker exec -it accelerator-27 /bin/bash

# Check files
ls -la /app

# Check environment
env | grep DATABASE

# Check processes
ps aux
```

#### Test API Directly

```bash
# Health check
curl -v http://localhost:8027/health

# Test endpoint with verbose
curl -v -X POST http://localhost:8027/api/v1/agreements \
  -H "Content-Type: application/json" \
  -d '{"provider_org": "test", "consumer_org": "test2", "data_assets": []}'

# Check API docs
curl http://localhost:8027/openapi.json
```

### Performance Tuning

#### Optimize Workers

```bash
# Calculate optimal workers: (2 x CPU cores) + 1
WORKERS=$((2 * $(nproc) + 1))
docker run -e WORKERS=$WORKERS dataforge-acc-27
```

#### Database Connection Pooling

```bash
docker run \
  -e DB_POOL_SIZE=20 \
  -e DB_MAX_OVERFLOW=40 \
  dataforge-acc-27
```

#### Enable Response Caching

Add Redis:
```bash
docker run -d --name redis redis:7
docker run --link redis:redis \
  -e REDIS_URL=redis://redis:6379/0 \
  dataforge-acc-27
```

---

## Next Steps

1. **Development:** Start with local deployment for development
2. **Testing:** Use Docker Compose for integration testing
3. **Staging:** Deploy to staging environment with PostgreSQL
4. **Production:** Use Kubernetes with proper monitoring
5. **Scale:** Add load balancing and auto-scaling

For specific accelerator deployment details, see:
- Individual accelerator README files in `accelerators/XX-*/`
- API documentation at `http://localhost:80XX/docs`
- HTML documentation in `docs/accelerators/`

---

**Last Updated:** November 2025
**Version:** 1.0.0
**Support:** For issues, refer to individual accelerator documentation
