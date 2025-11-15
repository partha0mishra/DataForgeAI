# DataForge Data Contracts

Shared schemas and models for cross-service communication.

## Purpose

This package provides:
- JSON schemas for API contracts
- Pydantic models for type-safe Python code
- Protocol Buffer definitions for gRPC

## Contents

- `schemas/` - JSON Schema definitions
- `python/` - Pydantic models
- `protobuf/` - Protocol Buffer definitions (future)

## Usage

### JSON Schemas

```python
import json
from jsonschema import validate

# Load schema
with open("schemas/pipeline_metadata.json") as f:
    schema = json.load(f)

# Validate data
data = {
    "pipeline_id": "pipe-123",
    "run_id": "run-456",
    "name": "ETL Pipeline",
    "status": "success",
    "start_time": "2025-11-15T10:00:00Z"
}

validate(instance=data, schema=schema)
```

### Pydantic Models

```python
from dataforge_contracts import PipelineMetadata, PipelineStatus
from datetime import datetime

# Create metadata
metadata = PipelineMetadata(
    pipeline_id="pipe-123",
    run_id="run-456",
    name="ETL Pipeline",
    status=PipelineStatus.SUCCESS,
    start_time=datetime.utcnow(),
    records_processed=10000
)

# Serialize to JSON
json_data = metadata.model_dump_json()

# Deserialize from JSON
metadata = PipelineMetadata.model_validate_json(json_data)
```

## Development

Add new schemas and models as needed. Ensure:
- JSON schemas in `schemas/` directory
- Corresponding Pydantic models in `python/models.py`
- Update `__init__.py` to export new models
