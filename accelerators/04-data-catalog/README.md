# Data Catalog with Semantic Search

Enterprise data catalog for dataset discovery, lineage tracking, and schema management with AI-powered semantic search.

## Features

- **Dataset Discovery**: Comprehensive metadata catalog for all data assets
- **Semantic Search**: AI-powered search using embeddings for intelligent discovery
- **Schema Registry**: Version-controlled schema management with compatibility validation
- **Data Lineage**: Track data transformations and dependencies with graph visualization
- **Impact Analysis**: Understand downstream effects of data changes
- **Column-level Metadata**: Track detailed column information and statistics
- **Tagging & Classification**: Organize datasets with tags and sensitivity levels
- **Usage Tracking**: Monitor dataset access patterns and popularity
- **REST API**: Complete API for programmatic access

## Quick Start

### 1. Install Dependencies

```bash
cd accelerators/04-data-catalog
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export DATAFORGE_ENV="development"
export LOG_LEVEL="INFO"
# Optional: Neo4j for production lineage tracking
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"
```

### 3. Run Example

```bash
python examples/catalog_example.py
```

This demonstrates:
- Dataset registration
- Schema versioning
- Semantic search
- Lineage tracking
- Impact analysis

### 4. Start API Server

```bash
cd backend
uvicorn src.api.main:app --reload --port 8003
```

API will be available at: http://localhost:8003

## Architecture

### Components

```
Data Catalog
├── Metadata Catalog        # Dataset metadata storage
├── Schema Registry         # Schema versioning and validation
├── Lineage Tracker        # Graph-based lineage tracking
└── Semantic Search Engine # Vector-based search
```

### Data Flow

```
Dataset Registration → Metadata Storage → Index for Search
                    ↓
              Lineage Tracking → Graph Database
                    ↓
           Schema Validation → Schema Registry
```

## Core Components

### 1. Data Catalog (`metadata/catalog.py`)

Manages dataset metadata and discovery:

```python
from metadata.catalog import DataCatalog, DatasetType, ColumnMetadata

catalog = DataCatalog()

# Register dataset
dataset_id = catalog.register_dataset(
    name="customer_profiles",
    description="Customer demographics and contact info",
    dataset_type=DatasetType.TABLE,
    source="postgres://crm/customers",
    owner="data_team",
    database="crm",
    schema="public",
    table="customers",
    tags=["customer", "pii"],
    columns=[
        ColumnMetadata(
            name="customer_id",
            data_type="integer",
            description="Unique ID",
            primary_key=True
        ),
        ColumnMetadata(
            name="email",
            data_type="string",
            tags=["pii"]
        )
    ]
)

# Search datasets
results = catalog.search_datasets("customer contact")

# List by tags
customer_datasets = catalog.list_datasets(tags=["customer"])
```

### 2. Schema Registry (`schema/schema_registry.py`)

Version-controlled schema management:

```python
from schema.schema_registry import SchemaRegistry, SchemaType, CompatibilityMode

registry = SchemaRegistry()

# Register schema
schema = {
    "type": "object",
    "properties": {
        "customer_id": {"type": "integer"},
        "email": {"type": "string"}
    },
    "required": ["customer_id"]
}

schema_id = registry.register_schema(
    name="customer",
    namespace="com.dataforge.crm",
    schema=schema,
    schema_type=SchemaType.JSON_SCHEMA,
    compatibility_mode=CompatibilityMode.BACKWARD
)

# Validate compatibility
is_compatible = registry.validate_compatibility(schema_id, new_schema)

# Get specific version
schema_v2 = registry.get_schema(schema_id, version=2)
```

### 3. Lineage Tracker (`lineage/lineage_tracker.py`)

Graph-based data lineage:

```python
from lineage.lineage_tracker import LineageTracker

tracker = LineageTracker()

# Track transformation
tracker.track_transformation(
    source_datasets=["raw.customers", "raw.orders"],
    target_dataset="analytics.customer_ltv",
    transformation="JOIN and aggregate by customer",
    metadata={"pipeline": "daily_etl"}
)

# Get upstream lineage
upstream = tracker.get_upstream_lineage("analytics.customer_ltv")

# Analyze impact
impact = tracker.analyze_impact("raw.customers")
print(f"Changes affect {impact['total_affected']} datasets")
```

### 4. Semantic Search (`search/semantic_search.py`)

AI-powered dataset discovery:

```python
from search.semantic_search import SemanticSearchEngine

search = SemanticSearchEngine()

# Index dataset
search.index_dataset(
    dataset_id="customers",
    name="Customer Profiles",
    description="Customer demographics and contact information",
    metadata={"tags": ["customer", "pii"]},
    columns=["customer_id", "email", "phone"]
)

# Search (hybrid: semantic + keyword)
results = search.search(
    query="customer contact details",
    top_k=10,
    hybrid_alpha=0.7  # 70% semantic, 30% keyword
)

for result in results:
    print(f"{result.name}: {result.score:.2f}")
    print(f"  Matched: {', '.join(result.matched_fields)}")
```

## API Endpoints

### Dataset Management

**Register Dataset**
```bash
curl -X POST "http://localhost:8003/datasets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_profiles",
    "description": "Customer data from CRM",
    "dataset_type": "table",
    "source": "postgres://crm/customers",
    "owner": "data_team",
    "tags": ["customer", "pii"]
  }'
```

**Get Dataset**
```bash
curl "http://localhost:8003/datasets/{dataset_id}"
```

**List Datasets**
```bash
curl "http://localhost:8003/datasets?owner=data_team&tags=customer"
```

**Add Tags**
```bash
curl -X POST "http://localhost:8003/datasets/{dataset_id}/tags" \
  -H "Content-Type: application/json" \
  -d '["analytics", "high_quality"]'
```

### Semantic Search

**Search Datasets**
```bash
curl -X POST "http://localhost:8003/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "customer transaction history",
    "top_k": 10,
    "hybrid_alpha": 0.7
  }'
```

Response:
```json
{
  "query": "customer transaction history",
  "results": [
    {
      "dataset_id": "sales.orders",
      "name": "Order History",
      "description": "Complete order transaction history",
      "score": 0.89,
      "matched_fields": ["name", "description"],
      "metadata": {
        "tags": ["order", "transaction"],
        "owner": "sales_team"
      }
    }
  ],
  "count": 5
}
```

### Schema Management

**Register Schema**
```bash
curl -X POST "http://localhost:8003/schemas" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer",
    "namespace": "com.dataforge.crm",
    "schema": {"type": "object", "properties": {...}},
    "schema_type": "json_schema",
    "compatibility_mode": "backward"
  }'
```

**Get Schema**
```bash
curl "http://localhost:8003/schemas/{schema_id}?version=2"
```

### Lineage Tracking

**Track Transformation**
```bash
curl -X POST "http://localhost:8003/lineage/track" \
  -H "Content-Type: application/json" \
  -d '{
    "source_datasets": ["raw.customers", "raw.orders"],
    "target_dataset": "analytics.customer_orders",
    "transformation": "JOIN customers ON orders.customer_id",
    "metadata": {"pipeline": "daily_etl"}
  }'
```

**Get Upstream Lineage**
```bash
curl "http://localhost:8003/lineage/{dataset_id}/upstream?max_depth=5"
```

**Get Downstream Lineage**
```bash
curl "http://localhost:8003/lineage/{dataset_id}/downstream?max_depth=5"
```

**Analyze Impact**
```bash
curl "http://localhost:8003/lineage/{dataset_id}/impact"
```

Response:
```json
{
  "source_dataset": "raw.customers",
  "total_affected": 5,
  "affected_datasets": ["stg.customers", "analytics.customer_ltv", ...],
  "max_depth": 3,
  "by_depth": {
    "0": ["raw.customers"],
    "1": ["stg.customers"],
    "2": ["analytics.customer_ltv", "analytics.customer_orders"]
  }
}
```

## Configuration

### Environment Variables

```bash
# Application
DATAFORGE_ENV=production
LOG_LEVEL=INFO
API_PORT=8003

# Database (for metadata storage)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=catalog
POSTGRES_USER=catalog_user
POSTGRES_PASSWORD=your_password

# Neo4j (for lineage graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Elasticsearch (optional, for search)
ELASTICSEARCH_HOST=localhost:9200

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Use Cases

### 1. Data Discovery

Find datasets across your organization:

```python
# Search by business terms
results = search.search("customer lifetime value")

# Find PII datasets
pii_datasets = catalog.list_datasets(tags=["pii"])

# Discover by owner
team_datasets = catalog.list_datasets(owner="analytics_team")
```

### 2. Impact Analysis

Understand change impact before modifications:

```python
# Before modifying raw.customers
impact = tracker.analyze_impact("raw.customers")

print(f"This change will affect {impact['total_affected']} downstream datasets:")
for dataset in impact['affected_datasets']:
    print(f"  - {dataset}")
```

### 3. Schema Evolution

Manage schema changes safely:

```python
# Validate new schema version
is_compatible = registry.validate_compatibility(schema_id, new_schema)

if is_compatible:
    registry.register_schema(name, namespace, new_schema)
else:
    print("Breaking change detected!")
```

### 4. Data Governance

Track sensitive data and ownership:

```python
# Find all PII datasets
pii_datasets = catalog.search_datasets("", filters={"tags": ["pii"]})

# Audit dataset access
metadata = catalog.get_dataset(dataset_id)
print(f"Accessed {metadata.access_count} times")
print(f"Last accessed: {metadata.last_accessed}")
```

## Integration with Other Accelerators

### With Pipeline Automation (Accelerator 1)

Automatically track lineage in DAGs:

```python
# In Airflow DAG
from lineage.lineage_tracker import LineageTracker

tracker = LineageTracker()

def transform_data(**context):
    # Your transformation
    ...

    # Track lineage
    tracker.track_transformation(
        source_datasets=["raw.customers"],
        target_dataset="analytics.customers",
        transformation="dbt run",
        metadata={"dag_id": context["dag"].dag_id}
    )
```

### With Data Quality (Accelerator 2)

Link quality metrics to catalog:

```python
# Update dataset with quality score
catalog.update_dataset(
    dataset_id="analytics.customers",
    quality_score=0.95
)
```

## Deployment

### Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/secrets.yaml
```

### Docker

```bash
docker build -t data-catalog:latest .
docker run -p 8003:8003 \
  -e POSTGRES_HOST=postgres \
  -e NEO4J_URI=bolt://neo4j:7687 \
  data-catalog:latest
```

## Monitoring

Access Prometheus metrics at `/metrics`:

- `datasets_registered_total`: Total datasets registered
- `schemas_registered_total`: Total schemas registered
- `searches_total`: Total search queries
- `lineage_tracked_total`: Total lineage relationships

## Testing

```bash
pytest tests/ -v
```

## Limitations

1. **In-Memory Storage**: Current implementation uses in-memory storage. For production, integrate with PostgreSQL, Elasticsearch, and Neo4j.
2. **Simple Compatibility Checks**: Schema compatibility uses basic field comparison. Consider using libraries like `jsonschema` for robust validation.
3. **No Authentication**: API has no authentication. Add authentication before production deployment.

## Roadmap

- [ ] PostgreSQL integration for metadata storage
- [ ] Neo4j integration for production lineage tracking
- [ ] Elasticsearch for advanced search
- [ ] Column-level lineage tracking
- [ ] Data quality integration
- [ ] Web UI for catalog browsing
- [ ] API authentication and authorization
- [ ] Automated schema inference
- [ ] Business glossary integration

## Troubleshooting

### Issue: Search returns no results

Check if datasets are indexed:
```python
stats = search_engine.get_statistics()
print(f"Indexed: {stats['total_indexed']}")
```

### Issue: Lineage tracking slow

Consider using Neo4j for large lineage graphs:
```python
tracker = LineageTracker(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password"
)
```

## License

Part of DataForge AI Platform - MIT License
