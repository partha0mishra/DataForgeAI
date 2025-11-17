# Production Deployment Guide

This guide covers best practices for deploying the MLOps Accelerator to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Configuration](#database-configuration)
4. [Security Hardening](#security-hardening)
5. [Deployment Strategies](#deployment-strategies)
6. [Monitoring & Observability](#monitoring--observability)
7. [Backup & Disaster Recovery](#backup--disaster-recovery)
8. [Scaling Considerations](#scaling-considerations)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Infrastructure

- **Kubernetes Cluster** (EKS, GKE, AKS, or self-managed)
  - Minimum: 3 nodes, 4 vCPUs, 16GB RAM each
  - Recommended: 5 nodes, 8 vCPUs, 32GB RAM each

- **PostgreSQL Database** (RDS, Cloud SQL, or self-managed)
  - Version: PostgreSQL 14+
  - Storage: 100GB SSD minimum
  - Backup retention: 7 days minimum

- **Redis Cache** (ElastiCache, Memorystore, or self-managed)
  - Version: Redis 7+
  - Memory: 4GB minimum

- **Object Storage** (S3, GCS, Azure Blob)
  - For model artifacts and logs
  - Versioning enabled

- **Container Registry**
  - ECR, GCR, ACR, or DockerHub

### Required Tools

```bash
# Install required CLI tools
kubectl version --client  # 1.27+
helm version             # 3.12+
docker version          # 24.0+
```

## Environment Setup

### 1. Create Production Environment File

```bash
# Create production .env file
cat > .env.production << EOF
# Application Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# Database Configuration
DATABASE_URL=postgresql://mlops_user:CHANGE_ME@postgres.example.com:5432/mlops_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# MLflow Configuration
MLFLOW_TRACKING_URI=https://mlflow.example.com
MLFLOW_ARTIFACT_ROOT=s3://mlops-artifacts/mlflow

# Redis Configuration
REDIS_URL=redis://redis.example.com:6379/0
REDIS_PASSWORD=CHANGE_ME

# Security
JWT_SECRET_KEY=CHANGE_ME_TO_RANDOM_256_BIT_KEY
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# API Configuration
API_HOST=0.0.0.0
API_PORT=8015
API_WORKERS=4

# CORS Settings
CORS_ORIGINS=https://app.example.com,https://dashboard.example.com
ALLOWED_HOSTS=api.example.com

# AWS Configuration (if using S3)
AWS_ACCESS_KEY_ID=CHANGE_ME
AWS_SECRET_ACCESS_KEY=CHANGE_ME
AWS_REGION=us-east-1

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
EOF

# IMPORTANT: Never commit this file to version control!
chmod 600 .env.production
```

### 2. Generate Secure Secrets

```bash
# Generate JWT secret (256-bit)
openssl rand -hex 32

# Generate database password
openssl rand -base64 32

# Generate Redis password
openssl rand -base64 24
```

## Database Configuration

### 1. Initialize PostgreSQL Database

```sql
-- Create database and user
CREATE DATABASE mlops_prod;
CREATE USER mlops_user WITH ENCRYPTED PASSWORD 'your-secure-password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE mlops_prod TO mlops_user;

-- Connect to mlops_prod database
\c mlops_prod

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO mlops_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mlops_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mlops_user;
```

### 2. Run Database Migrations

```bash
# Export DATABASE_URL
export DATABASE_URL="postgresql://mlops_user:password@postgres.example.com:5432/mlops_prod"

# Run migrations
alembic upgrade head

# Verify migrations
alembic current
```

### 3. Database Performance Tuning

```sql
-- Optimize for production workload
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET min_wal_size = '2GB';
ALTER SYSTEM SET max_wal_size = '8GB';
ALTER SYSTEM SET max_worker_processes = 8;
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;

-- Reload configuration
SELECT pg_reload_conf();
```

## Security Hardening

### 1. Network Security

```yaml
# Kubernetes NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mlops-api-network-policy
  namespace: mlops
spec:
  podSelector:
    matchLabels:
      app: mlops-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8015
  egress:
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 5432  # PostgreSQL
        - protocol: TCP
          port: 6379  # Redis
        - protocol: TCP
          port: 5000  # MLflow
        - protocol: TCP
          port: 443   # HTTPS
```

### 2. Pod Security Standards

```yaml
# PodSecurityPolicy
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: mlops-api-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: true
```

### 3. Secrets Management

```bash
# Use Kubernetes Secrets (encrypted at rest)
kubectl create secret generic mlops-secrets \
  --from-literal=database-url="${DATABASE_URL}" \
  --from-literal=jwt-secret="${JWT_SECRET_KEY}" \
  --from-literal=redis-password="${REDIS_PASSWORD}" \
  --namespace=mlops

# Or use external secrets manager (recommended)
# - AWS Secrets Manager
# - Azure Key Vault
# - HashiCorp Vault
# - Google Secret Manager
```

### 4. Enable RBAC

```yaml
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mlops-api
  namespace: mlops

---
# Role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: mlops-api-role
  namespace: mlops
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]

---
# RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: mlops-api-rolebinding
  namespace: mlops
subjects:
  - kind: ServiceAccount
    name: mlops-api
roleRef:
  kind: Role
  name: mlops-api-role
  apiGroup: rbac.authorization.k8s.io
```

## Deployment Strategies

### Option 1: Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlops-api
  namespace: mlops
  labels:
    app: mlops-api
    version: v1.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: mlops-api
  template:
    metadata:
      labels:
        app: mlops-api
        version: v1.0.0
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8015"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: mlops-api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: mlops-api
          image: your-registry/mlops-accelerator:v1.0.0
          imagePullPolicy: Always
          ports:
            - containerPort: 8015
              name: http
              protocol: TCP
          env:
            - name: ENVIRONMENT
              value: "production"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: mlops-secrets
                  key: database-url
            - name: JWT_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: mlops-secrets
                  key: jwt-secret
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mlops-secrets
                  key: redis-password
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
              port: 8015
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8015
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: cache
              mountPath: /app/.cache
      volumes:
        - name: tmp
          emptyDir: {}
        - name: cache
          emptyDir: {}
---
# Service
apiVersion: v1
kind: Service
metadata:
  name: mlops-api
  namespace: mlops
  labels:
    app: mlops-api
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8015
      protocol: TCP
      name: http
  selector:
    app: mlops-api
---
# HorizontalPodAutoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mlops-api-hpa
  namespace: mlops
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mlops-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 2
          periodSeconds: 15
      selectPolicy: Max
```

### Option 2: Helm Chart Deployment

```bash
# Deploy using Helm
helm install mlops-accelerator ./helm-chart \
  --namespace mlops \
  --create-namespace \
  --set image.tag=v1.0.0 \
  --set replicaCount=3 \
  --set ingress.enabled=true \
  --set ingress.host=api.example.com \
  --values values.production.yaml
```

### Option 3: Docker Compose (Small Scale)

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  mlops-api:
    image: your-registry/mlops-accelerator:v1.0.0
    restart: always
    ports:
      - "8015:8015"
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
      - mlflow
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8015/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: mlops_prod
      POSTGRES_USER: mlops_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mlops_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.9.2
    restart: always
    command: |
      mlflow server \
        --backend-store-uri postgresql://mlops_user:${POSTGRES_PASSWORD}@postgres:5432/mlops_prod \
        --default-artifact-root s3://mlops-artifacts/mlflow \
        --host 0.0.0.0 \
        --port 5000
    ports:
      - "5000:5000"
    depends_on:
      - postgres
    environment:
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}

  prometheus:
    image: prom/prometheus:latest
    restart: always
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:latest
    restart: always
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
      GF_INSTALL_PLUGINS: grafana-piechart-panel

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

## Monitoring & Observability

### 1. Prometheus Metrics

The application exposes metrics at `/metrics` endpoint:

```yaml
# Key metrics to monitor
- mlops_models_total{status}
- mlops_deployments_total{environment,strategy}
- mlops_drift_detections_total{type,severity}
- mlops_api_request_duration_seconds{method,endpoint}
- mlops_api_request_total{method,endpoint,status}
- mlops_db_connections{state}
```

### 2. Logging Configuration

```python
# Production logging configuration
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": "/var/log/mlops-api/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}
```

### 3. Health Check Endpoints

```python
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check with dependencies."""
    try:
        # Check database connection
        db.execute("SELECT 1")

        # Check Redis connection
        redis_client.ping()

        return {"status": "ready", "dependencies": {"database": "ok", "redis": "ok"}}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Not ready: {str(e)}")
```

## Backup & Disaster Recovery

### 1. Database Backups

```bash
# Automated backup script
#!/bin/bash

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/mlops_backup_${TIMESTAMP}.sql.gz"

# Create backup
pg_dump -h postgres.example.com \
  -U mlops_user \
  -d mlops_prod \
  --format=custom \
  --compress=9 \
  | gzip > ${BACKUP_FILE}

# Upload to S3
aws s3 cp ${BACKUP_FILE} s3://mlops-backups/database/

# Cleanup old backups (keep last 30 days)
find ${BACKUP_DIR} -name "mlops_backup_*.sql.gz" -mtime +30 -delete

# Verify backup integrity
pg_restore --list ${BACKUP_FILE} > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "Backup successful: ${BACKUP_FILE}"
else
  echo "Backup verification failed!"
  exit 1
fi
```

### 2. Restore Procedure

```bash
# Restore from backup
gunzip -c mlops_backup_20250117_120000.sql.gz | \
  pg_restore -h postgres.example.com \
    -U mlops_user \
    -d mlops_prod \
    --clean \
    --if-exists
```

## Scaling Considerations

### Horizontal Scaling

1. **API Layer**: Use HPA (shown above) to auto-scale based on CPU/memory
2. **Database**: Use read replicas for read-heavy workloads
3. **Redis**: Use Redis Cluster for horizontal scaling
4. **MLflow**: Deploy multiple MLflow servers behind load balancer

### Vertical Scaling

- Monitor resource utilization
- Adjust resource requests/limits based on actual usage
- Use PodDisruptionBudget to ensure availability during updates

### Caching Strategy

```python
# Implement caching for frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_model_from_cache(model_id: str):
    # Cache model metadata
    return model_repo.get_by_id(model_id)
```

## Troubleshooting

### Common Issues

1. **Database Connection Timeouts**
   ```bash
   # Check connection pool settings
   DATABASE_POOL_SIZE=20
   DATABASE_MAX_OVERFLOW=40
   ```

2. **High Memory Usage**
   ```bash
   # Adjust worker count
   API_WORKERS=4  # Should be 2-4 x CPU cores
   ```

3. **Slow API Responses**
   - Enable query logging to identify slow queries
   - Add database indexes on frequently queried columns
   - Implement caching for read-heavy endpoints

### Debug Mode (Non-Production)

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true

# Check application logs
kubectl logs -f deployment/mlops-api -n mlops

# Access pod shell
kubectl exec -it deployment/mlops-api -n mlops -- /bin/sh
```

### Performance Profiling

```python
# Add profiling middleware
from pyinstrument import Profiler

@app.middleware("http")
async def profile_request(request: Request, call_next):
    profiler = Profiler()
    profiler.start()
    response = await call_next(request)
    profiler.stop()
    return response
```

## Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations completed
- [ ] Secrets stored securely
- [ ] Network policies applied
- [ ] Resource limits configured
- [ ] Health checks enabled
- [ ] Monitoring & alerting setup
- [ ] Backup automation configured
- [ ] SSL/TLS certificates installed
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Load testing completed
- [ ] Disaster recovery plan documented
- [ ] On-call rotation established
- [ ] Incident response procedures defined

## Support

For production support:
- Email: support@example.com
- Slack: #mlops-support
- On-call: PagerDuty rotation
