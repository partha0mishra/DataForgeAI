# DataForge Common Library

Core utilities and shared functionality for the DataForge AI Platform.

## Features

- **Authentication & Authorization**: JWT token handling, RBAC, SSO integration
- **Logging**: Structured logging with context propagation
- **Monitoring**: OpenTelemetry instrumentation and Prometheus metrics
- **Configuration**: Environment-based configuration management
- **Utilities**: Retry logic, error handling, helpers

## Installation

```bash
pip install dataforge-common
```

## Usage

### Authentication

```python
from dataforge_common.auth import JWTManager, verify_token

# Create JWT token
jwt_manager = JWTManager(secret_key="your-secret")
token = jwt_manager.create_token(user_id="user123", roles=["admin"])

# Verify token
payload = verify_token(token)
```

### Logging

```python
from dataforge_common.logging import get_logger

logger = get_logger(__name__)
logger.info("Pipeline started", pipeline_id="pipe-123", user_id="user-456")
```

### Monitoring

```python
from dataforge_common.monitoring import track_duration, increment_counter

@track_duration("pipeline_execution")
def run_pipeline():
    increment_counter("pipeline_runs")
    # Your pipeline code
```

### Configuration

```python
from dataforge_common.config import Settings

settings = Settings()
db_url = settings.database_url
log_level = settings.log_level
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/

# Type checking
mypy src/
```
