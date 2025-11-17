# DataForge AI - Operations & Troubleshooting Guide

## 📋 Table of Contents

- [Overview](#overview)
- [System Monitoring](#system-monitoring)
- [Health Checks](#health-checks)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Backup & Recovery](#backup--recovery)
- [Security Operations](#security-operations)
- [Maintenance Procedures](#maintenance-procedures)
- [Incident Response](#incident-response)
- [Common Issues & Solutions](#common-issues--solutions)

---

## Overview

This guide provides operational procedures, troubleshooting steps, and best practices for running DataForge AI accelerators in production environments.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Load Balancer / API Gateway                   │
├─────────────────────────────────────────────────────────────────┤
│  Accelerator 01  │  Accelerator 02  │  ...  │  Accelerator 32   │
│    Port 8001     │    Port 8002     │       │    Port 8032      │
├─────────────────────────────────────────────────────────────────┤
│                    Shared Infrastructure                         │
│  PostgreSQL  │  Redis  │  Kafka  │  Prometheus  │  Grafana      │
└─────────────────────────────────────────────────────────────────┘
```

### Service Inventory

| Accelerator | Port | Purpose | Critical |
|-------------|------|---------|----------|
| 01 | 8001 | Data Discovery | High |
| 02 | 8002 | Schema Inference | High |
| 03 | 8003 | Data Profiling | Medium |
| 04 | 8004 | Quality Rules | High |
| 05 | 8005 | Lineage Tracking | Medium |
| 06 | 8006 | PII Detection | Critical |
| 07 | 8007 | Classification | Medium |
| 08 | 8008 | Incremental Processing | High |
| 09 | 8009 | Data Integration | High |
| 10 | 8010 | Transformations | High |
| 11 | 8011 | Stream Processing | High |
| 12 | 8012 | Feature Engineering | Medium |
| 13 | 8013 | AutoML | Medium |
| 14 | 8014 | Model Deployment | Critical |
| 15 | 8015 | MLOps Pipeline | Critical |
| 16 | 8016 | Data Versioning | High |
| 17 | 8017 | A/B Testing | Medium |
| 18 | 8018 | Recommendations | Medium |
| 19 | 8019 | NLP Analytics | Medium |
| 20 | 8020 | Computer Vision | Medium |
| 21 | 8021 | Governance | Critical |
| 22 | 8022 | Cost Optimization | High |
| 23 | 8023 | AI Explainability | High |
| 24 | 8024 | Cross-Platform | Medium |
| 25 | 8025 | Data Mesh | Medium |
| 26 | 8026 | Security | Critical |
| 27 | 8027 | Data Sharing | High |
| 28 | 8028 | Graph Analytics | Medium |
| 29 | 8029 | Geospatial | Medium |
| 30 | 8030 | Synthetic Data | Medium |
| 31 | 8031 | AIOps | High |
| 32 | 8032 | Disaster Recovery | Critical |

---

## System Monitoring

### Prometheus Metrics

All accelerators expose Prometheus metrics at `/metrics`:

```bash
# Check metrics endpoint
curl http://localhost:8001/metrics

# Sample metrics:
# http_requests_total{method="GET",endpoint="/health",status="200"} 1547
# http_request_duration_seconds_bucket{le="0.1"} 1234
# database_connections_active 5
# database_connections_idle 15
```

### Grafana Dashboards

#### Import Pre-built Dashboard

```bash
# Download dashboard JSON
curl -o dataforge-dashboard.json https://grafana.com/api/dashboards/12345/revisions/1/download

# Import via Grafana UI or API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @dataforge-dashboard.json
```

#### Key Metrics to Monitor

**Service Health**:
- Service uptime percentage
- Request rate (requests/second)
- Error rate (%)
- P50, P95, P99 latency

**Resource Utilization**:
- CPU usage (%)
- Memory usage (MB)
- Disk I/O (MB/s)
- Network I/O (MB/s)

**Database**:
- Connection pool utilization
- Query duration
- Slow query count
- Deadlock count

**Business Metrics**:
- Datasets processed
- Models trained
- Predictions served
- Data quality score

### Setting Up Alerts

```yaml
# prometheus-alerts.yml
groups:
  - name: dataforge_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "{{ $labels.accelerator }} has error rate above 5%"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s"

      - alert: ServiceDown
        expr: up{job="dataforge"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.instance }} is unreachable"

      - alert: DatabaseConnectionPoolExhausted
        expr: database_connections_active / database_connections_max > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool nearly exhausted"

      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes / 1024 / 1024 / 1024 > 8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}GB"
```

---

## Health Checks

### Individual Service Health

```bash
# Check single accelerator
curl http://localhost:8001/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0",
  "uptime_seconds": 86400
}
```

### Bulk Health Check Script

```bash
#!/bin/bash
# health-check-all.sh

echo "DataForge AI - Health Check Report"
echo "==================================="
date
echo ""

for port in {8001..8032}; do
    accelerator=$(printf "%02d" $((port - 8000)))

    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health --max-time 2)

    if [ "$response" = "200" ]; then
        echo "✓ Accelerator $accelerator (port $port): HEALTHY"
    else
        echo "✗ Accelerator $accelerator (port $port): UNHEALTHY (HTTP $response)"
    fi
done
```

### Kubernetes Liveness & Readiness Probes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: accelerator-01
spec:
  containers:
  - name: accelerator
    image: dataforge/accelerator-01:latest
    livenessProbe:
      httpGet:
        path: /health
        port: 8001
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /health
        port: 8001
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 2
```

---

## Logging

### Log Levels

All accelerators support configurable log levels:

```bash
# Set log level via environment variable
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Start service
uvicorn src.main:app --port 8001
```

### Centralized Logging with ELK Stack

#### Filebeat Configuration

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/dataforge/*.log
  fields:
    service: dataforge
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "dataforge-%{+yyyy.MM.dd}"

setup.kibana:
  host: "kibana:5601"
```

### Log Format

Standard JSON log format:

```json
{
  "timestamp": "2025-11-17T10:30:45.123Z",
  "level": "INFO",
  "logger": "accelerator-01",
  "message": "Request processed successfully",
  "request_id": "req_abc123",
  "method": "POST",
  "path": "/api/v1/catalogs",
  "status_code": 201,
  "duration_ms": 45.3,
  "user_id": "user_xyz",
  "trace_id": "trace_123"
}
```

### Useful Log Queries

```bash
# View last 100 errors
docker logs accelerator-01 2>&1 | grep "ERROR" | tail -n 100

# Follow logs in real-time
docker logs -f accelerator-01

# Filter by request ID
docker logs accelerator-01 2>&1 | grep "req_abc123"

# Count errors in last hour
docker logs --since 1h accelerator-01 2>&1 | grep -c "ERROR"
```

### Log Rotation

```bash
# /etc/logrotate.d/dataforge
/var/log/dataforge/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 dataforge dataforge
    sharedscripts
    postrotate
        systemctl reload dataforge-*
    endscript
}
```

---

## Troubleshooting

### Diagnostic Commands

```bash
# System resources
top -p $(pgrep -f "uvicorn")
df -h
free -m

# Network connectivity
netstat -tulpn | grep :80[0-9][0-9]
ss -tlnp | grep :80[0-9][0-9]

# Process information
ps aux | grep uvicorn
systemctl status dataforge-accelerator-01

# Database connectivity
psql $DATABASE_URL -c "SELECT version();"
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Docker diagnostics
docker ps
docker stats
docker inspect accelerator-01
```

### Performance Profiling

#### Python Profiling

```bash
# Install profiling tools
pip install py-spy

# Profile running process
py-spy top --pid $(pgrep -f "accelerator-01")

# Generate flame graph
py-spy record -o profile.svg --pid $(pgrep -f "accelerator-01") --duration 60
```

#### Database Query Analysis

```sql
-- Find slow queries
SELECT
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 1000  -- > 1 second
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Current running queries
SELECT
    pid,
    now() - query_start as duration,
    state,
    query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Kill long-running query
SELECT pg_terminate_backend(pid);
```

---

## Performance Tuning

### Application-Level Tuning

#### Uvicorn Workers

```bash
# Single worker (development)
uvicorn src.main:app --port 8001

# Multiple workers (production)
uvicorn src.main:app --port 8001 --workers 4

# With auto-reload disabled
uvicorn src.main:app --port 8001 --workers 4 --no-reload

# Recommended: (CPU cores * 2) + 1
WORKERS=$(($(nproc) * 2 + 1))
uvicorn src.main:app --workers $WORKERS
```

#### Database Connection Pooling

```python
# src/database.py
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Base pool size
    max_overflow=10,       # Additional connections when pool exhausted
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo=False             # Disable SQL logging in production
)
```

### Database Tuning

#### PostgreSQL Configuration

```ini
# postgresql.conf

# Memory Settings
shared_buffers = 4GB                # 25% of RAM
effective_cache_size = 12GB         # 75% of RAM
work_mem = 64MB                     # Per operation
maintenance_work_mem = 512MB

# Connection Settings
max_connections = 200
idle_in_transaction_session_timeout = 300000  # 5 minutes

# Query Tuning
random_page_cost = 1.1              # For SSD
effective_io_concurrency = 200      # For SSD

# Write-Ahead Log
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB
checkpoint_completion_target = 0.9

# Query Planning
default_statistics_target = 100
```

#### Indexing Best Practices

```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_datasets_created
ON datasets(created_at DESC);

CREATE INDEX CONCURRENTLY idx_models_status
ON models(status) WHERE status = 'active';

CREATE INDEX CONCURRENTLY idx_predictions_timestamp
ON predictions(timestamp) WHERE timestamp > now() - interval '30 days';

-- Partial index for recent data
CREATE INDEX CONCURRENTLY idx_events_recent
ON events(event_time)
WHERE event_time > now() - interval '7 days';

-- Composite index for multi-column queries
CREATE INDEX CONCURRENTLY idx_user_dataset
ON permissions(user_id, dataset_id);

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

-- Find unused indexes
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND indexname NOT LIKE '%_pkey';
```

### Caching Strategies

#### Redis Caching

```python
import redis
from functools import wraps
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(ttl=300):
    """Cache function results in Redis"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{args}:{kwargs}"

            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )

            return result
        return wrapper
    return decorator

# Usage
@cache_result(ttl=600)
def get_dataset_stats(dataset_id):
    # Expensive operation
    return calculate_stats(dataset_id)
```

---

## Backup & Recovery

### Database Backups

#### Automated Backup Script

```bash
#!/bin/bash
# backup-databases.sh

BACKUP_DIR="/backups/dataforge"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup each database
for db in dataforge_01 dataforge_02 dataforge_03; do
    echo "Backing up $db..."

    pg_dump $db | gzip > "$BACKUP_DIR/${db}_${DATE}.sql.gz"

    if [ $? -eq 0 ]; then
        echo "✓ $db backed up successfully"
    else
        echo "✗ $db backup failed"
        exit 1
    fi
done

# Clean old backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

#### Backup Verification

```bash
# Test backup restoration
gunzip -c backup.sql.gz | psql test_db

# Verify backup integrity
gunzip -t backup.sql.gz && echo "Backup file is valid"
```

### Point-in-Time Recovery

```bash
# Enable continuous archiving in PostgreSQL
# postgresql.conf:
# wal_level = replica
# archive_mode = on
# archive_command = 'cp %p /archive/%f'

# Create base backup
pg_basebackup -D /backups/base -F tar -z -P

# Restore to specific point in time
# recovery.conf:
# restore_command = 'cp /archive/%f %p'
# recovery_target_time = '2025-11-17 10:30:00'
```

### Application State Backup

```bash
# Backup configuration files
tar -czf config_backup.tar.gz \
    /etc/dataforge/*.conf \
    /opt/dataforge/.env \
    /opt/dataforge/docker-compose.yml

# Backup data volumes
docker run --rm \
    -v dataforge_data:/data \
    -v $(pwd):/backup \
    alpine tar -czf /backup/volumes_backup.tar.gz /data
```

---

## Security Operations

### Certificate Management

```bash
# Generate self-signed certificate (development)
openssl req -x509 -newkey rsa:4096 \
    -keyout key.pem -out cert.pem \
    -days 365 -nodes

# Use Let's Encrypt (production)
certbot certonly --standalone \
    -d dataforge.example.com \
    --email admin@example.com

# Auto-renewal
echo "0 0 * * * certbot renew --quiet" | crontab -
```

### Access Control Audit

```bash
# List all API keys
psql -c "SELECT user_id, key_hash, created_at, last_used FROM api_keys;"

# Revoke inactive keys
psql -c "DELETE FROM api_keys WHERE last_used < now() - interval '90 days';"

# List user permissions
psql -c "SELECT u.username, r.role_name, p.resource, p.action
         FROM users u
         JOIN roles r ON u.role_id = r.id
         JOIN permissions p ON r.id = p.role_id;"
```

### Vulnerability Scanning

```bash
# Scan dependencies
pip install safety
safety check --json

# Scan Docker images
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image dataforge/accelerator-01:latest

# Scan for secrets
pip install detect-secrets
detect-secrets scan --all-files > .secrets.baseline
```

---

## Maintenance Procedures

### Database Maintenance

```sql
-- Vacuum and analyze
VACUUM ANALYZE;

-- Reindex
REINDEX DATABASE dataforge;

-- Update statistics
ANALYZE;

-- Check for bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    n_dead_tup,
    n_live_tup,
    round(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_ratio
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

### Log Cleanup

```bash
# Clean old logs
find /var/log/dataforge -name "*.log" -mtime +30 -delete

# Clean Docker logs
truncate -s 0 $(docker inspect --format='{{.LogPath}}' accelerator-01)

# Clean application cache
find /tmp/dataforge -type f -mtime +7 -delete
```

### Dependency Updates

```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade fastapi

# Update all (with caution)
pip install --upgrade -r requirements.txt

# Security updates only
pip install --upgrade $(pip list --outdated | grep -i security | awk '{print $1}')
```

---

## Incident Response

### Incident Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| P0 | Critical - Complete outage | 15 minutes | All services down |
| P1 | High - Major functionality impaired | 1 hour | Database unavailable |
| P2 | Medium - Limited impact | 4 hours | Single accelerator down |
| P3 | Low - Minor issue | 1 business day | UI bug |

### Incident Response Playbook

#### 1. Detection & Triage

```bash
# Check overall system health
./health-check-all.sh

# Check recent errors
for port in {8001..8032}; do
    docker logs --since 10m accelerator-$(printf "%02d" $((port-8000))) 2>&1 | grep ERROR
done

# Check system resources
htop
df -h
free -m
```

#### 2. Immediate Actions

```bash
# Restart failed service
docker restart accelerator-01

# Scale up if needed
docker-compose up --scale accelerator-01=3

# Enable maintenance mode
curl -X POST http://localhost:8001/admin/maintenance \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d '{"enabled": true, "message": "Under maintenance"}'
```

#### 3. Investigation

```bash
# Collect logs
for i in {01..32}; do
    docker logs accelerator-$i > /tmp/logs/accelerator-$i.log 2>&1
done

# Database diagnostics
psql -c "SELECT * FROM pg_stat_activity WHERE state != 'idle';"
psql -c "SELECT * FROM pg_stat_database;"

# Network diagnostics
tcpdump -i any port 8001 -w /tmp/capture.pcap
```

#### 4. Communication Template

```
INCIDENT ALERT - P1
===================
Time: 2025-11-17 10:30 UTC
Severity: P1 - High
Status: Investigating

Issue: Accelerator 14 (Model Deployment) returning 500 errors

Impact:
- Unable to deploy new models
- Existing deployments functioning normally
- Estimated 500 users affected

Actions Taken:
- Service restarted at 10:32 UTC
- Database connections verified
- Investigating error logs

Next Update: 11:00 UTC
```

---

## Common Issues & Solutions

### Issue: High Memory Usage

**Symptoms**:
```
ERROR: Cannot allocate memory
OOMKilled
```

**Diagnosis**:
```bash
# Check memory usage
docker stats

# Check for memory leaks
py-spy dump --pid $(pgrep -f accelerator-01)
```

**Solutions**:
```bash
# Increase Docker memory limit
docker update --memory 4g accelerator-01

# Add swap space
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Restart with memory limit
docker run -m 2g -p 8001:8001 accelerator-01
```

---

### Issue: Database Connection Pool Exhausted

**Symptoms**:
```
sqlalchemy.exc.TimeoutError: QueuePool limit exceeded
```

**Diagnosis**:
```sql
SELECT count(*) FROM pg_stat_activity;
SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction';
```

**Solutions**:
```python
# Increase pool size in database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=50,      # Increased from 20
    max_overflow=20,   # Increased from 10
)
```

```sql
-- Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
AND state_change < now() - interval '10 minutes';
```

---

### Issue: Slow API Responses

**Symptoms**:
```
Response time > 2 seconds
Timeout errors
```

**Diagnosis**:
```bash
# Check endpoint performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8001/api/v1/datasets

# curl-format.txt:
#     time_total:  %{time_total}
#     time_connect:  %{time_connect}
#     time_starttransfer:  %{time_starttransfer}
```

**Solutions**:
```python
# Add caching
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_startup
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="cache")

# Add database indexes
CREATE INDEX CONCURRENTLY idx_datasets_user ON datasets(user_id);

# Enable query result caching
@cache(expire=300)
async def get_datasets():
    return await db.query(Dataset).all()
```

---

### Issue: SSL Certificate Errors

**Symptoms**:
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions**:
```bash
# Update certificates
update-ca-certificates

# Force certificate refresh
rm -rf ~/.local/share/ca-certificates/
update-ca-certificates --fresh

# Use custom CA bundle
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
export SSL_CERT_FILE=/path/to/ca-bundle.crt
```

---

### Issue: Docker Container Keeps Restarting

**Diagnosis**:
```bash
# Check container logs
docker logs accelerator-01

# Check container status
docker inspect accelerator-01 | grep -A 10 State

# Check exit code
docker inspect accelerator-01 --format='{{.State.ExitCode}}'
```

**Common Exit Codes**:
- 137: OOMKilled (out of memory)
- 139: Segmentation fault
- 1: Application error

**Solutions**:
```bash
# Increase memory
docker run -m 4g accelerator-01

# Add health check grace period
docker run --health-start-period=60s accelerator-01

# Check application logs for startup errors
docker logs accelerator-01 2>&1 | grep -A 5 "ERROR"
```

---

### Issue: Kafka Connection Failures

**Symptoms**:
```
kafka.errors.NoBrokersAvailable
Connection refused to kafka:9092
```

**Solutions**:
```bash
# Verify Kafka is running
docker ps | grep kafka

# Check Kafka logs
docker logs kafka

# Test connection
telnet kafka 9092

# Update broker list
export KAFKA_BOOTSTRAP_SERVERS="kafka-1:9092,kafka-2:9092,kafka-3:9092"
```

---

## Emergency Procedures

### Complete System Shutdown

```bash
# Stop all accelerators
docker-compose down

# Or stop individually
for i in {01..32}; do
    docker stop accelerator-$i
done

# Stop databases
docker stop postgres redis kafka
```

### Complete System Startup

```bash
# Start infrastructure
docker-compose up -d postgres redis kafka

# Wait for databases to be ready
sleep 30

# Start accelerators in order
docker-compose up -d
```

### Disaster Recovery Activation

```bash
# Switch to backup region
./scripts/failover-to-backup.sh

# Verify all services
./scripts/health-check-all.sh

# Update DNS
aws route53 change-resource-record-sets \
    --hosted-zone-id Z123456 \
    --change-batch file://dns-change.json
```

---

## Monitoring Checklist

### Daily Checks
- [ ] Review error logs
- [ ] Check service health status
- [ ] Verify backup completion
- [ ] Review performance metrics
- [ ] Check disk space usage

### Weekly Checks
- [ ] Review slow query logs
- [ ] Analyze performance trends
- [ ] Update dependencies
- [ ] Review security alerts
- [ ] Test backup restoration

### Monthly Checks
- [ ] Capacity planning review
- [ ] Security audit
- [ ] Disaster recovery drill
- [ ] Documentation review
- [ ] Cost optimization review

---

## Support Contacts

### Escalation Path

1. **L1 Support**: ops-team@example.com (24/7)
2. **L2 Engineering**: engineering@example.com (Business hours)
3. **L3 On-Call**: +1-555-0123 (Critical issues)

### Vendor Support

- PostgreSQL Support: support@postgresql.org
- Redis Support: support@redis.io
- AWS Support: https://console.aws.amazon.com/support/

---

**Last Updated**: November 17, 2025
**Version**: 1.0.0
**Owner**: Platform Operations Team
