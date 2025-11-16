# DataForge Common

Shared utilities and infrastructure for DataForge AI Platform.

## Installation

```bash
pip install -e .
```

## Components

- **logging.py** - Structured JSON logging with correlation IDs
- **monitoring.py** - Metrics collection (counters, gauges, histograms)
- **config.py** - Configuration management (YAML + env vars)
- **database.py** - Database connection pooling and session management

## Usage

```python
from dataforge_common.logging import get_logger
from dataforge_common.monitoring import get_metrics_collector
from dataforge_common.config import get_config
from dataforge_common.database import init_database, get_db_session

# Logging
logger = get_logger(__name__)
logger.info("Application started")

# Metrics
metrics = get_metrics_collector()
metrics.increment_counter("requests_total")
metrics.set_gauge("active_users", 42)

# Configuration
config = get_config()
db_url = config.get("database", "url")

# Database
init_database("postgresql://user:pass@localhost/db")
with get_db_session() as session:
    # Use session...
    pass
```

## License

MIT
