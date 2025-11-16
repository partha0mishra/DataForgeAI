# DataForge AI Platform - Load Testing

Load and performance testing suite using Locust.

## Overview

This directory contains load tests for:
- Authentication endpoints
- Data Governance API
- Streaming Analytics
- Database operations
- Caching performance

## Installation

```bash
pip install locust
```

## Quick Start

### 1. Start API Services

```bash
# Terminal 1: Start Data Governance API
cd accelerators/12-data-governance/src
python -m api.main

# Terminal 2: Start Streaming Analytics API
cd accelerators/13-streaming-analytics/src
python -m api.main
```

### 2. Run Load Tests

```bash
# Web UI mode (recommended for visualization)
cd load-tests
locust -f locustfile.py

# Then open http://localhost:8089 in your browser
```

## Test Scenarios

### 1. Full Platform Load Test

Test all components with mixed workload:

```bash
locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m --headless
```

**Metrics:**
- 100 concurrent users
- 10 users spawned per second
- 5 minute test duration
- No web UI (headless mode)

### 2. Authentication Load Test

Stress test authentication system:

```bash
locust -f locustfile.py AuthenticationLoadTest \
    --users 50 \
    --spawn-rate 5 \
    --run-time 3m \
    --headless
```

**What it tests:**
- Login endpoint performance
- Token generation under load
- Failed login handling
- Token refresh flow

### 3. Streaming Analytics Load Test

High-throughput streaming ingestion:

```bash
locust -f locustfile.py StreamingLoadTest \
    --users 200 \
    --spawn-rate 20 \
    --run-time 5m \
    --headless
```

**What it tests:**
- Event ingestion rate
- Window aggregation performance
- Recent events retrieval
- High-frequency requests

### 4. Data Governance Load Test

File processing and PII detection:

```bash
locust -f locustfile.py DataForgeUser \
    --users 30 \
    --spawn-rate 5 \
    --run-time 10m \
    --headless
```

**What it tests:**
- PII scanning with authentication
- File upload performance
- Data classification
- PII masking operations

## Understanding Results

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| RPS | Requests per second | >100 RPS |
| Response Time (p50) | Median response time | <100ms |
| Response Time (p95) | 95th percentile | <500ms |
| Response Time (p99) | 99th percentile | <1000ms |
| Failure Rate | % of failed requests | <1% |

### Example Output

```
Type     Name                  # reqs   # fails   Avg   Min   Max  Med  req/s failures/s
------------------------------------------------------------------------
POST     /auth/login           1000     0         45    12    234   38   50.0   0.00
POST     /pii/scan             500      2         156   45    892   120  25.0   0.10
GET      /health               2000     0         15    5     87    12   100.0  0.00
------------------------------------------------------------------------
Aggregated                     3500     2         52    5     892   28   175.0  0.10
```

### Interpreting Results

**Good Performance:**
- ✅ Failure rate < 1%
- ✅ p95 response time < 500ms
- ✅ Consistent RPS with increasing users
- ✅ No timeouts

**Performance Issues:**
- ⚠️ Failure rate > 1%
- ⚠️ p95 response time > 500ms
- ⚠️ RPS decreases with more users
- ⚠️ Frequent timeouts

## Advanced Usage

### Custom Test Duration

```bash
# Run for specific duration
locust -f locustfile.py --run-time 10m  # 10 minutes
locust -f locustfile.py --run-time 1h   # 1 hour
locust -f locustfile.py --run-time 30s  # 30 seconds
```

### Specific User Count

```bash
# Ramp up to 500 users
locust -f locustfile.py --users 500 --spawn-rate 50
```

### Output to CSV

```bash
locust -f locustfile.py \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --csv results \
    --html results.html
```

Generates:
- `results_stats.csv` - Request statistics
- `results_stats_history.csv` - Time-series data
- `results_failures.csv` - Failure details
- `results.html` - HTML report

### Distributed Load Testing

For very high load, run Locust in distributed mode:

```bash
# Terminal 1: Start master
locust -f locustfile.py --master

# Terminal 2-N: Start workers
locust -f locustfile.py --worker --master-host=localhost

# Access web UI at http://localhost:8089
```

## Custom Test Scenarios

### Create Custom User Class

```python
from locust import HttpUser, task, between

class MyCustomUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8012"

    @task(3)
    def my_task(self):
        """Custom task with weight 3."""
        self.client.get("/my/endpoint")

    @task(1)
    def my_other_task(self):
        """Custom task with weight 1."""
        self.client.post("/my/other/endpoint", json={...})
```

### Run Custom Test

```bash
locust -f custom_test.py MyCustomUser
```

## Performance Benchmarks

### Target Performance Goals

| Component | Target RPS | p95 Response Time |
|-----------|-----------|-------------------|
| Authentication | 100 RPS | <100ms |
| PII Scanning | 50 RPS | <200ms |
| Data Classification | 75 RPS | <150ms |
| Stream Ingestion | 1000 RPS | <50ms |
| Health Checks | 500 RPS | <10ms |

### System Requirements for Targets

**Recommended:**
- CPU: 4+ cores
- RAM: 8+ GB
- Database: PostgreSQL with connection pooling
- Cache: Redis (optional but recommended)

## Troubleshooting

### High Failure Rate

**Possible causes:**
1. Services not running
2. Database connection limits reached
3. Memory exhaustion
4. Network timeouts

**Solutions:**
```bash
# Check service status
curl http://localhost:8012/health

# Increase database connections
export DATABASE_POOL_SIZE=50

# Increase timeout
locust -f locustfile.py --timeout 30
```

### Slow Response Times

**Possible causes:**
1. Database not indexed
2. No caching enabled
3. Insufficient resources
4. Cold start (first requests slow)

**Solutions:**
- Enable Redis caching
- Add database indexes
- Warm up with smaller load first
- Scale horizontally

### Connection Errors

```
ConnectionError: HTTPConnectionPool: Max retries exceeded
```

**Solutions:**
```bash
# Increase connection pool
export LOCUST_POOL_SIZE=100

# Reduce spawn rate
locust -f locustfile.py --spawn-rate 1

# Add delays between requests
# Edit wait_time in locustfile.py
```

## Best Practices

1. **Start Small**: Begin with 10-20 users, then scale up
2. **Warm Up**: Run a small test first to warm up caches
3. **Monitor Resources**: Watch CPU, memory, and database connections
4. **Realistic Scenarios**: Match production traffic patterns
5. **Steady State**: Let tests run long enough to reach steady state
6. **Multiple Runs**: Run tests multiple times for consistency
7. **Baseline**: Establish baseline performance before changes

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Load Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  load-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install locust
          pip install -e shared-libraries/dataforge-common

      - name: Start services
        run: |
          # Start services in background
          python accelerators/12-data-governance/src/api/main.py &
          sleep 10

      - name: Run load tests
        run: |
          cd load-tests
          locust -f locustfile.py \
            --headless \
            --users 50 \
            --spawn-rate 5 \
            --run-time 3m \
            --csv results

      - name: Check performance
        run: |
          # Fail if p95 > 500ms or failure rate > 1%
          python scripts/check_performance.py results_stats.csv
```

## Next Steps

- [ ] Add more test scenarios
- [ ] Create custom performance assertions
- [ ] Add database load tests
- [ ] Test with Redis vs in-memory cache
- [ ] Test Kafka throughput
- [ ] Add chaos engineering tests
- [ ] Profile slow endpoints
- [ ] Create performance regression tests

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [Load Testing Best Practices](https://locust.io/best-practices)
- [Performance Testing Guide](https://locust.io/performance-testing-guide)
