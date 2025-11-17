# DataForge AI - Comprehensive Usage Guide

## 📚 Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Phase 1: Core Infrastructure (Accelerators 1-10)](#phase-1-core-infrastructure)
- [Phase 2: Advanced Analytics (Accelerators 11-20)](#phase-2-advanced-analytics)
- [Phase 3: Enterprise Features (Accelerators 21-32)](#phase-3-enterprise-features)
- [Common Patterns](#common-patterns)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

---

## Getting Started

All accelerators expose REST APIs via FastAPI. Each accelerator runs on its own port (8001-8032).

### Prerequisites

```bash
# Ensure accelerator is running
curl http://localhost:8001/health

# View interactive API documentation
# Open in browser: http://localhost:8001/docs
```

### Base URLs

Each accelerator has its own base URL:
- Accelerator 01: `http://localhost:8001`
- Accelerator 02: `http://localhost:8002`
- ...
- Accelerator 32: `http://localhost:8032`

---

## Authentication

Most endpoints require authentication via API key or JWT token.

### Using API Keys

```bash
# Set API key in environment
export DATAFORGE_API_KEY="your-api-key-here"

# Use in requests
curl -H "X-API-Key: $DATAFORGE_API_KEY" http://localhost:8001/api/v1/catalogs
```

### Using JWT Tokens

```python
import requests

# Login to get token
response = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "username": "admin",
    "password": "secure-password"
})
token = response.json()["access_token"]

# Use token in subsequent requests
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8001/api/v1/catalogs", headers=headers)
```

---

## Phase 1: Core Infrastructure

### Accelerator 01: Automated Data Discovery

**Purpose**: Discover and catalog data sources automatically

#### Create a Data Catalog

```bash
curl -X POST http://localhost:8001/api/v1/catalogs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Database",
    "description": "Main production PostgreSQL database",
    "connection_type": "postgresql",
    "connection_string": "postgresql://user:pass@localhost:5432/prod"
  }'
```

**Python Example:**

```python
import requests

catalog = {
    "name": "S3 Data Lake",
    "description": "AWS S3 data lake",
    "connection_type": "s3",
    "connection_string": "s3://my-bucket/data/"
}

response = requests.post(
    "http://localhost:8001/api/v1/catalogs",
    json=catalog
)
print(response.json())
# Output: {"catalog_id": "uuid", "name": "S3 Data Lake", ...}
```

#### Discover Data Sources

```python
# Trigger discovery scan
response = requests.post(
    f"http://localhost:8001/api/v1/catalogs/{catalog_id}/discover"
)

# Get discovered datasets
datasets = requests.get(
    f"http://localhost:8001/api/v1/catalogs/{catalog_id}/datasets"
).json()

for dataset in datasets:
    print(f"Found: {dataset['name']} ({dataset['row_count']} rows)")
```

---

### Accelerator 02: Intelligent Schema Inference

**Purpose**: Automatically infer and manage database schemas

#### Infer Schema from Data

```python
import requests

# Upload sample data
files = {"file": open("sample_data.csv", "rb")}
response = requests.post(
    "http://localhost:8002/api/v1/schemas/infer",
    files=files
)

schema = response.json()
print(schema)
# Output:
# {
#   "columns": [
#     {"name": "id", "type": "integer", "nullable": false},
#     {"name": "email", "type": "string", "nullable": false},
#     {"name": "age", "type": "integer", "nullable": true}
#   ],
#   "primary_key": ["id"],
#   "indexes": ["email"]
# }
```

#### Apply Schema to Database

```python
# Create table from inferred schema
response = requests.post(
    "http://localhost:8002/api/v1/schemas/apply",
    json={
        "schema_id": schema["schema_id"],
        "table_name": "users",
        "database": "production"
    }
)
```

---

### Accelerator 03: Smart Data Profiling

**Purpose**: Generate comprehensive data quality profiles

#### Profile a Dataset

```bash
curl -X POST http://localhost:8003/api/v1/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "dataset-uuid",
    "columns": ["*"],
    "include_statistics": true,
    "include_distributions": true
  }'
```

**Python Example:**

```python
# Create profiling job
profile_job = requests.post(
    "http://localhost:8003/api/v1/profiles",
    json={
        "dataset_id": "dataset-123",
        "columns": ["*"],
        "sample_size": 10000
    }
).json()

# Wait for completion and get results
import time
while True:
    status = requests.get(
        f"http://localhost:8003/api/v1/profiles/{profile_job['job_id']}"
    ).json()

    if status["status"] == "completed":
        break
    time.sleep(2)

# View profile results
profile = status["results"]
for col in profile["column_profiles"]:
    print(f"{col['name']}:")
    print(f"  Type: {col['data_type']}")
    print(f"  Nulls: {col['null_percentage']}%")
    print(f"  Distinct: {col['distinct_count']}")
    print(f"  Min: {col['min']}, Max: {col['max']}")
```

---

### Accelerator 04: Automated Quality Rules

**Purpose**: Define and enforce data quality rules

#### Create Quality Rules

```python
# Define a quality rule
rule = {
    "name": "Email Validation",
    "description": "Ensure all emails are valid",
    "rule_type": "regex",
    "column": "email",
    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "severity": "error"
}

response = requests.post(
    "http://localhost:8004/api/v1/rules",
    json=rule
)
```

#### Execute Quality Checks

```python
# Run quality checks on dataset
response = requests.post(
    "http://localhost:8004/api/v1/rules/execute",
    json={
        "dataset_id": "dataset-123",
        "rule_ids": ["rule-1", "rule-2", "rule-3"]
    }
)

results = response.json()
print(f"Total rows checked: {results['total_rows']}")
print(f"Passed: {results['passed_count']}")
print(f"Failed: {results['failed_count']}")

# View failures
for failure in results['failures']:
    print(f"Row {failure['row_id']}: {failure['reason']}")
```

---

### Accelerator 05: Data Lineage Tracking

**Purpose**: Track data flow and transformations

#### Register Data Lineage

```python
# Record a data transformation
lineage = {
    "source_dataset_id": "customers_raw",
    "target_dataset_id": "customers_cleaned",
    "transformation": "data_cleaning",
    "description": "Remove duplicates and standardize formats",
    "transformations": [
        {"step": 1, "operation": "deduplicate", "column": "email"},
        {"step": 2, "operation": "standardize", "column": "phone"}
    ]
}

response = requests.post(
    "http://localhost:8005/api/v1/lineage",
    json=lineage
)
```

#### Query Lineage

```python
# Get upstream dependencies
upstream = requests.get(
    f"http://localhost:8005/api/v1/lineage/{dataset_id}/upstream"
).json()

print("Upstream datasets:")
for ds in upstream:
    print(f"  - {ds['name']} (via {ds['transformation']})")

# Get downstream consumers
downstream = requests.get(
    f"http://localhost:8005/api/v1/lineage/{dataset_id}/downstream"
).json()

print("Downstream datasets:")
for ds in downstream:
    print(f"  - {ds['name']}")
```

---

### Accelerator 06: PII Detection & Masking

**Purpose**: Detect and mask sensitive personal information

#### Scan for PII

```python
# Scan dataset for PII
response = requests.post(
    "http://localhost:8006/api/v1/pii/scan",
    json={
        "dataset_id": "customer_data",
        "detection_types": ["email", "ssn", "credit_card", "phone", "address"]
    }
)

pii_findings = response.json()
for finding in pii_findings['detections']:
    print(f"Column '{finding['column']}' contains {finding['pii_type']}")
    print(f"  Confidence: {finding['confidence']}%")
    print(f"  Occurrences: {finding['count']}")
```

#### Mask PII Data

```python
# Apply masking to PII columns
response = requests.post(
    "http://localhost:8006/api/v1/pii/mask",
    json={
        "dataset_id": "customer_data",
        "masking_rules": [
            {"column": "email", "method": "partial", "preserve_domain": true},
            {"column": "ssn", "method": "hash"},
            {"column": "credit_card", "method": "tokenize"}
        ]
    }
)

# Original: john.doe@example.com
# Masked:   j***.d**@example.com
```

---

### Accelerator 07: Intelligent Data Classification

**Purpose**: Automatically classify and tag data

#### Classify Dataset

```python
# Auto-classify dataset columns
response = requests.post(
    "http://localhost:8007/api/v1/classify",
    json={
        "dataset_id": "sales_data",
        "classification_levels": ["public", "internal", "confidential", "restricted"]
    }
)

classifications = response.json()
for col in classifications['columns']:
    print(f"{col['name']}: {col['classification']} ({col['confidence']}%)")
    print(f"  Tags: {', '.join(col['tags'])}")
```

#### Apply Custom Tags

```python
# Add custom tags
requests.post(
    "http://localhost:8007/api/v1/tags",
    json={
        "dataset_id": "sales_data",
        "column": "revenue",
        "tags": ["financial", "quarterly-report", "sensitive"]
    }
)
```

---

### Accelerator 08: Incremental Processing Engine

**Purpose**: Efficiently process only changed data

#### Set Up Incremental Processing

```python
# Configure incremental processing
config = {
    "source_dataset_id": "transactions",
    "target_dataset_id": "transactions_aggregated",
    "watermark_column": "updated_at",
    "checkpoint_interval": 300  # seconds
}

response = requests.post(
    "http://localhost:8008/api/v1/incremental/configure",
    json=config
)
```

#### Process Incremental Data

```python
# Trigger incremental processing
response = requests.post(
    "http://localhost:8008/api/v1/incremental/process",
    json={
        "config_id": config_id,
        "since": "2025-11-17T00:00:00Z"
    }
)

result = response.json()
print(f"Processed {result['rows_processed']} new/changed rows")
print(f"Duration: {result['duration_seconds']}s")
```

---

### Accelerator 09: Multi-Source Data Integration

**Purpose**: Integrate data from 50+ sources

#### Connect to Data Source

```python
# Connect to Salesforce
salesforce_conn = {
    "source_type": "salesforce",
    "credentials": {
        "username": "user@company.com",
        "password": "password",
        "security_token": "token",
        "domain": "login.salesforce.com"
    }
}

response = requests.post(
    "http://localhost:8009/api/v1/connections",
    json=salesforce_conn
)
```

#### Extract and Load Data

```python
# Extract data from source
extraction = {
    "connection_id": conn_id,
    "object": "Account",
    "fields": ["Id", "Name", "Industry", "AnnualRevenue"],
    "filter": "CreatedDate > LAST_N_DAYS:7"
}

response = requests.post(
    "http://localhost:8009/api/v1/extract",
    json=extraction
)

# Load to target
loading = {
    "extraction_id": extraction_id,
    "target_type": "postgresql",
    "target_table": "salesforce_accounts",
    "mode": "upsert",
    "match_column": "Id"
}

requests.post(
    "http://localhost:8009/api/v1/load",
    json=loading
)
```

---

### Accelerator 10: Automated Data Transformations

**Purpose**: Apply SQL and custom transformations at scale

#### Create Transformation

```python
# Define SQL transformation
transformation = {
    "name": "Customer Aggregation",
    "description": "Aggregate customer metrics",
    "transformation_type": "sql",
    "source_datasets": ["orders", "customers"],
    "sql": """
        SELECT
            c.customer_id,
            c.name,
            COUNT(o.order_id) as total_orders,
            SUM(o.amount) as total_revenue,
            AVG(o.amount) as avg_order_value
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.name
    """,
    "target_dataset": "customer_metrics"
}

response = requests.post(
    "http://localhost:8010/api/v1/transformations",
    json=transformation
)
```

#### Execute Transformation

```python
# Run transformation
response = requests.post(
    f"http://localhost:8010/api/v1/transformations/{transform_id}/execute",
    json={"async": True}
)

job_id = response.json()["job_id"]

# Monitor progress
status = requests.get(
    f"http://localhost:8010/api/v1/jobs/{job_id}"
).json()

print(f"Status: {status['status']}")
print(f"Progress: {status['progress']}%")
```

---

## Phase 2: Advanced Analytics

### Accelerator 11: Real-Time Stream Processing

**Purpose**: Process streaming data in real-time

#### Create Stream

```python
# Define streaming source
stream = {
    "name": "Clickstream Events",
    "source_type": "kafka",
    "config": {
        "bootstrap_servers": "kafka:9092",
        "topic": "clickstream",
        "consumer_group": "analytics"
    },
    "schema": {
        "user_id": "string",
        "event_type": "string",
        "timestamp": "timestamp",
        "properties": "json"
    }
}

response = requests.post(
    "http://localhost:8011/api/v1/streams",
    json=stream
)
```

#### Process Stream with Window Functions

```python
# Define windowed aggregation
window_query = {
    "stream_id": stream_id,
    "window_type": "tumbling",
    "window_size": "5 minutes",
    "aggregations": [
        {"field": "event_type", "function": "count"},
        {"field": "user_id", "function": "count_distinct"}
    ],
    "group_by": ["event_type"]
}

requests.post(
    "http://localhost:8011/api/v1/streams/windows",
    json=window_query
)
```

---

### Accelerator 12: Advanced Feature Engineering

**Purpose**: Create ML features automatically

#### Auto-Generate Features

```python
# Generate features from dataset
features = {
    "dataset_id": "customer_data",
    "target_column": "churn",
    "feature_types": [
        "numerical_aggregations",
        "categorical_encoding",
        "temporal_features",
        "interaction_features"
    ],
    "max_features": 100
}

response = requests.post(
    "http://localhost:8012/api/v1/features/generate",
    json=features
)

generated = response.json()
print(f"Generated {len(generated['features'])} features")
for feat in generated['features'][:5]:
    print(f"  - {feat['name']}: {feat['importance']}")
```

---

### Accelerator 13: AutoML Model Selection

**Purpose**: Automatically select and train best ML models

#### Train AutoML Model

```python
# Configure AutoML experiment
experiment = {
    "name": "Churn Prediction",
    "dataset_id": "customer_features",
    "target_column": "churn",
    "problem_type": "binary_classification",
    "metric": "auc_roc",
    "algorithms": ["logistic_regression", "random_forest", "xgboost", "neural_network"],
    "time_budget_minutes": 60
}

response = requests.post(
    "http://localhost:8013/api/v1/automl/experiments",
    json=experiment
)

experiment_id = response.json()["experiment_id"]

# Monitor training
import time
while True:
    status = requests.get(
        f"http://localhost:8013/api/v1/automl/experiments/{experiment_id}"
    ).json()

    print(f"Progress: {status['progress']}% - Best AUC: {status['best_score']}")

    if status['status'] == 'completed':
        break
    time.sleep(10)

# Get best model
best_model = status['best_model']
print(f"Best algorithm: {best_model['algorithm']}")
print(f"AUC: {best_model['metrics']['auc_roc']}")
print(f"Accuracy: {best_model['metrics']['accuracy']}")
```

---

### Accelerator 14: Model Deployment & Serving

**Purpose**: Deploy ML models to production

#### Deploy Model

```python
# Deploy model to production
deployment = {
    "model_id": best_model_id,
    "deployment_name": "churn-prediction-v1",
    "scaling": {
        "min_replicas": 2,
        "max_replicas": 10,
        "target_cpu_percent": 70
    },
    "environment": "production"
}

response = requests.post(
    "http://localhost:8014/api/v1/deployments",
    json=deployment
)

endpoint_url = response.json()["endpoint_url"]
```

#### Make Predictions

```python
# Predict using deployed model
prediction_request = {
    "instances": [
        {
            "age": 35,
            "tenure_months": 24,
            "monthly_charges": 79.99,
            "total_charges": 1919.76,
            "contract_type": "month-to-month"
        }
    ]
}

response = requests.post(
    f"{endpoint_url}/predict",
    json=prediction_request
)

predictions = response.json()
for pred in predictions['predictions']:
    print(f"Churn probability: {pred['probability']:.2%}")
    print(f"Prediction: {pred['class']}")
```

---

### Accelerator 15: MLOps Pipeline Automation

**Purpose**: Complete ML lifecycle automation

#### Create ML Pipeline

```python
# Define end-to-end ML pipeline
pipeline = {
    "name": "Customer Churn Pipeline",
    "stages": [
        {
            "name": "data_ingestion",
            "type": "data_source",
            "config": {"dataset_id": "customers"}
        },
        {
            "name": "feature_engineering",
            "type": "transformation",
            "config": {"accelerator_id": "12"}
        },
        {
            "name": "model_training",
            "type": "automl",
            "config": {"accelerator_id": "13", "time_budget": 30}
        },
        {
            "name": "model_evaluation",
            "type": "evaluation",
            "config": {"metrics": ["auc", "precision", "recall"]}
        },
        {
            "name": "deployment",
            "type": "deployment",
            "config": {"environment": "production", "approval_required": true}
        }
    ],
    "triggers": [
        {"type": "schedule", "cron": "0 2 * * *"},  # Daily at 2 AM
        {"type": "data_change", "threshold": 0.1}   # When 10% data changes
    ]
}

response = requests.post(
    "http://localhost:8015/api/v1/pipelines",
    json=pipeline
)
```

#### Monitor Pipeline

```python
# Get pipeline runs
runs = requests.get(
    f"http://localhost:8015/api/v1/pipelines/{pipeline_id}/runs"
).json()

for run in runs[:5]:
    print(f"Run {run['run_id']}: {run['status']}")
    print(f"  Started: {run['start_time']}")
    print(f"  Duration: {run['duration_seconds']}s")
    for stage in run['stages']:
        print(f"    - {stage['name']}: {stage['status']}")
```

---

### Accelerator 16: Data Versioning & Rollback

**Purpose**: Version control for data and models

#### Create Data Version

```python
# Version a dataset
version = {
    "dataset_id": "customer_features",
    "version": "v1.2.0",
    "description": "Added behavioral features",
    "tags": ["production", "validated"],
    "metadata": {
        "rows": 150000,
        "features": 47,
        "data_date": "2025-11-17"
    }
}

response = requests.post(
    "http://localhost:8016/api/v1/datasets/versions",
    json=version
)
```

#### Rollback to Previous Version

```python
# List versions
versions = requests.get(
    f"http://localhost:8016/api/v1/datasets/{dataset_id}/versions"
).json()

for v in versions:
    print(f"{v['version']} - {v['created_at']} - {v['description']}")

# Rollback to specific version
requests.post(
    f"http://localhost:8016/api/v1/datasets/{dataset_id}/rollback",
    json={"target_version": "v1.1.0"}
)
```

---

### Accelerator 17: A/B Testing Framework

**Purpose**: Run experiments and compare model performance

#### Create A/B Test

```python
# Set up A/B test
ab_test = {
    "name": "Churn Model Comparison",
    "description": "Compare XGBoost vs Neural Network",
    "variants": [
        {
            "name": "control",
            "model_id": "xgboost-model-v1",
            "traffic_percentage": 50
        },
        {
            "name": "treatment",
            "model_id": "neural-net-v2",
            "traffic_percentage": 50
        }
    ],
    "metrics": ["prediction_accuracy", "latency", "business_impact"],
    "duration_days": 14,
    "success_criteria": {
        "metric": "business_impact",
        "threshold": 0.05,  # 5% improvement
        "confidence": 0.95
    }
}

response = requests.post(
    "http://localhost:8017/api/v1/experiments",
    json=ab_test
)
```

#### Analyze Results

```python
# Get experiment results
results = requests.get(
    f"http://localhost:8017/api/v1/experiments/{experiment_id}/results"
).json()

print("A/B Test Results:")
for variant in results['variants']:
    print(f"\n{variant['name']}:")
    print(f"  Traffic: {variant['traffic_percentage']}%")
    print(f"  Samples: {variant['sample_count']}")
    for metric, value in variant['metrics'].items():
        print(f"  {metric}: {value}")

print(f"\nWinner: {results['winner']}")
print(f"Confidence: {results['confidence']:.1%}")
print(f"Recommendation: {results['recommendation']}")
```

---

### Accelerator 18: Recommendation Engine

**Purpose**: Build personalized recommendation systems

#### Train Recommendation Model

```python
# Train collaborative filtering model
model_config = {
    "algorithm": "matrix_factorization",
    "user_item_interactions": "user_product_interactions",
    "user_features": ["age", "location", "preferences"],
    "item_features": ["category", "price", "brand"],
    "embedding_dim": 50,
    "epochs": 20
}

response = requests.post(
    "http://localhost:8018/api/v1/models/train",
    json=model_config
)
```

#### Get Recommendations

```python
# Get personalized recommendations
recommendations = {
    "user_id": "user-12345",
    "num_recommendations": 10,
    "filters": {
        "category": "electronics",
        "min_price": 50,
        "max_price": 500
    },
    "diversify": true
}

response = requests.post(
    "http://localhost:8018/api/v1/recommend",
    json=recommendations
)

for item in response.json()['recommendations']:
    print(f"{item['item_id']}: {item['name']}")
    print(f"  Score: {item['score']:.3f}")
    print(f"  Reason: {item['explanation']}")
```

---

### Accelerator 19: NLP & Text Analytics

**Purpose**: Advanced natural language processing

#### Analyze Text

```python
# Comprehensive text analysis
text_analysis = {
    "text": "The customer service was excellent! Very helpful and responsive.",
    "analyses": [
        "sentiment",
        "entities",
        "keywords",
        "language_detection",
        "topics"
    ]
}

response = requests.post(
    "http://localhost:8019/api/v1/analyze",
    json=text_analysis
)

results = response.json()
print(f"Sentiment: {results['sentiment']['label']} ({results['sentiment']['score']:.2f})")
print(f"Language: {results['language']}")
print(f"Entities: {', '.join([e['text'] for e in results['entities']])}")
print(f"Keywords: {', '.join(results['keywords'])}")
```

#### Batch Document Processing

```python
# Process multiple documents
documents = {
    "documents": [
        {"id": "doc1", "text": "First document..."},
        {"id": "doc2", "text": "Second document..."},
    ],
    "operations": ["summarization", "key_phrase_extraction", "classification"]
}

response = requests.post(
    "http://localhost:8019/api/v1/batch",
    json=documents
)

for doc in response.json()['results']:
    print(f"\nDocument {doc['id']}:")
    print(f"  Summary: {doc['summary']}")
    print(f"  Key phrases: {', '.join(doc['key_phrases'])}")
    print(f"  Category: {doc['category']}")
```

---

### Accelerator 20: Computer Vision Processing

**Purpose**: Image and video analysis

#### Analyze Image

```python
# Upload and analyze image
files = {"image": open("product_image.jpg", "rb")}
response = requests.post(
    "http://localhost:8020/api/v1/vision/analyze",
    files=files,
    data={
        "analyses": "object_detection,ocr,quality_assessment"
    }
)

results = response.json()
print(f"Objects detected: {len(results['objects'])}")
for obj in results['objects']:
    print(f"  - {obj['label']}: {obj['confidence']:.2%}")

print(f"Text found: {results['ocr']['text']}")
print(f"Image quality score: {results['quality_score']}")
```

---

## Phase 3: Enterprise Features

### Accelerator 21: Data Governance & Compliance

**Purpose**: Ensure regulatory compliance and governance

#### Create Compliance Policy

```python
# Define GDPR compliance policy
policy = {
    "name": "GDPR Data Protection",
    "regulation": "GDPR",
    "rules": [
        {
            "rule": "data_retention",
            "max_retention_days": 730,
            "applicable_to": ["personal_data"]
        },
        {
            "rule": "right_to_erasure",
            "enabled": true,
            "response_time_days": 30
        },
        {
            "rule": "consent_tracking",
            "required": true
        }
    ]
}

response = requests.post(
    "http://localhost:8021/api/v1/policies",
    json=policy
)
```

#### Check Compliance

```python
# Run compliance check
compliance_check = {
    "dataset_id": "customer_data",
    "policies": ["GDPR", "CCPA", "HIPAA"]
}

response = requests.post(
    "http://localhost:8021/api/v1/compliance/check",
    json=compliance_check
)

results = response.json()
print(f"Compliance status: {results['overall_status']}")
for policy in results['policies']:
    print(f"\n{policy['name']}: {policy['status']}")
    if policy['violations']:
        for violation in policy['violations']:
            print(f"  ❌ {violation['rule']}: {violation['description']}")
```

---

### Accelerator 22: Cost Optimization Engine

**Purpose**: Optimize cloud and infrastructure costs

#### Analyze Current Costs

```python
# Get cost analysis
response = requests.get(
    "http://localhost:8022/api/v1/costs/analyze",
    params={
        "start_date": "2025-11-01",
        "end_date": "2025-11-17",
        "group_by": "service"
    }
)

costs = response.json()
print(f"Total cost: ${costs['total_cost']:.2f}")
for service in costs['breakdown']:
    print(f"  {service['name']}: ${service['cost']:.2f}")
```

#### Get Optimization Recommendations

```python
# Get cost savings recommendations
recommendations = requests.get(
    "http://localhost:8022/api/v1/recommendations"
).json()

total_savings = 0
for rec in recommendations:
    print(f"\n{rec['title']}")
    print(f"  Potential savings: ${rec['estimated_savings']}/month")
    print(f"  Action: {rec['action']}")
    print(f"  Effort: {rec['effort']}")
    total_savings += rec['estimated_savings']

print(f"\nTotal potential savings: ${total_savings:.2f}/month")
```

---

### Accelerator 23: AI Explainability & Trust

**Purpose**: Explain ML model predictions with SHAP/LIME

#### Explain Prediction

```python
# Get explanation for prediction
explanation_request = {
    "model_id": "churn-model-v1",
    "instance": {
        "age": 45,
        "tenure": 36,
        "monthly_charges": 89.99,
        "contract_type": "two-year"
    },
    "explainer": "shap"
}

response = requests.post(
    "http://localhost:8023/api/v1/explain",
    json=explanation_request
)

explanation = response.json()
print(f"Prediction: {explanation['prediction']}")
print(f"Probability: {explanation['probability']:.2%}")
print("\nFeature contributions:")
for feature in explanation['feature_importance']:
    print(f"  {feature['name']}: {feature['contribution']:+.3f}")
```

#### Detect Model Bias

```python
# Check for bias
bias_check = {
    "model_id": "hiring-model-v1",
    "dataset_id": "applicants",
    "protected_attributes": ["gender", "race", "age_group"],
    "fairness_metrics": ["demographic_parity", "equal_opportunity"]
}

response = requests.post(
    "http://localhost:8023/api/v1/bias/detect",
    json=bias_check
)

results = response.json()
for attr in results['protected_attributes']:
    print(f"\n{attr['name']}:")
    for metric in attr['metrics']:
        status = "✓" if metric['passed'] else "✗"
        print(f"  {status} {metric['name']}: {metric['value']:.3f}")
```

---

### Accelerator 24: Cross-Platform Portability

**Purpose**: Convert models and SQL across platforms

#### Convert Model Format

```python
# Convert PyTorch model to ONNX
conversion = {
    "source_format": "pytorch",
    "target_format": "onnx",
    "model_path": "models/pytorch_model.pth",
    "input_shape": [1, 3, 224, 224],
    "opset_version": 13
}

response = requests.post(
    "http://localhost:8024/api/v1/models/convert",
    json=conversion
)

print(f"Converted model: {response.json()['output_path']}")
```

#### Translate SQL

```python
# Translate SQL between dialects
sql_translation = {
    "source_dialect": "postgresql",
    "target_dialect": "snowflake",
    "sql": """
        SELECT
            DATE_TRUNC('month', order_date) as month,
            COUNT(*) as order_count,
            SUM(amount) as total_revenue
        FROM orders
        WHERE order_date >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY 1
        ORDER BY 1 DESC
    """
}

response = requests.post(
    "http://localhost:8024/api/v1/sql/translate",
    json=sql_translation
)

print("Translated SQL:")
print(response.json()['translated_sql'])
```

---

### Accelerator 25: Data Mesh Enablement

**Purpose**: Enable data mesh architecture

#### Create Data Product

```python
# Register data product
data_product = {
    "name": "Customer 360",
    "description": "Unified customer view",
    "domain": "customer_analytics",
    "owner": "analytics-team",
    "datasets": ["customers", "orders", "interactions"],
    "sla": {
        "freshness_minutes": 60,
        "availability": 99.9,
        "quality_score": 95
    },
    "contracts": {
        "schema": "customer_360_v1.json",
        "guarantees": ["no_pii_exposure", "gdpr_compliant"]
    }
}

response = requests.post(
    "http://localhost:8025/api/v1/products",
    json=data_product
)
```

---

### Accelerator 26: Advanced Security & Zero Trust

**Purpose**: Implement zero-trust security

#### Create Security Policy

```python
# Define access policy
policy = {
    "name": "Sensitive Data Access",
    "resources": ["customer_data", "financial_data"],
    "rules": [
        {
            "principal": "role:data_scientist",
            "actions": ["read"],
            "conditions": {
                "ip_range": "10.0.0.0/8",
                "time_range": "09:00-17:00",
                "require_mfa": true
            }
        }
    ]
}

requests.post(
    "http://localhost:8026/api/v1/policies",
    json=policy
)
```

---

### Accelerator 27: Data Sharing & Collaboration

**Purpose**: Securely share data between organizations

#### Create Sharing Agreement

```python
# Set up data sharing
agreement = {
    "provider_org": "Company A",
    "consumer_org": "Company B",
    "data_assets": ["product_catalog", "pricing"],
    "terms": {
        "duration_days": 365,
        "allowed_uses": ["analytics", "reporting"],
        "restrictions": ["no_redistribution", "no_derivative_works"]
    }
}

response = requests.post(
    "http://localhost:8027/api/v1/agreements",
    json=agreement
)

agreement_id = response.json()["agreement_id"]
```

---

### Accelerator 28: Graph Analytics & Knowledge Graphs

**Purpose**: Build and query knowledge graphs

#### Create Knowledge Graph

```python
# Add entities and relationships
entities = [
    {"id": "person_1", "type": "Person", "properties": {"name": "Alice"}},
    {"id": "company_1", "type": "Company", "properties": {"name": "TechCorp"}},
]

relationships = [
    {
        "source": "person_1",
        "target": "company_1",
        "type": "WORKS_FOR",
        "properties": {"since": "2020-01-01", "role": "Engineer"}
    }
]

requests.post("http://localhost:8028/api/v1/graph/nodes", json={"nodes": entities})
requests.post("http://localhost:8028/api/v1/graph/edges", json={"edges": relationships})
```

#### Query Graph

```python
# Cypher query
query = {
    "query": """
        MATCH (p:Person)-[r:WORKS_FOR]->(c:Company)
        WHERE c.name = 'TechCorp'
        RETURN p.name, r.role, r.since
    """
}

response = requests.post(
    "http://localhost:8028/api/v1/graph/query",
    json=query
)

for row in response.json()['results']:
    print(f"{row['p.name']} - {row['r.role']} since {row['r.since']}")
```

---

### Accelerator 29: Geospatial & Time-Series Analytics

**Purpose**: Advanced spatial and temporal analysis

#### Geocode Address

```python
# Geocode addresses
geocode = {
    "addresses": [
        "1600 Amphitheatre Parkway, Mountain View, CA",
        "1 Microsoft Way, Redmond, WA"
    ]
}

response = requests.post(
    "http://localhost:8029/api/v1/geocode",
    json=geocode
)

for result in response.json()['results']:
    print(f"{result['address']}: ({result['lat']}, {result['lon']})")
```

#### Time-Series Forecasting

```python
# Forecast future values
forecast = {
    "series_id": "daily_sales",
    "horizon": 30,  # days
    "model": "prophet",
    "seasonality": {
        "yearly": true,
        "weekly": true,
        "daily": false
    }
}

response = requests.post(
    "http://localhost:8029/api/v1/forecast",
    json=forecast
)

predictions = response.json()['predictions']
for pred in predictions[:5]:
    print(f"{pred['date']}: {pred['forecast']:.2f} (±{pred['uncertainty']:.2f})")
```

---

### Accelerator 30: Synthetic Data Generation

**Purpose**: Generate privacy-preserving synthetic data

#### Generate Synthetic Dataset

```python
# Create synthetic data
synthesis = {
    "source_dataset_id": "customer_data",
    "method": "ctgan",
    "num_rows": 10000,
    "privacy": {
        "differential_privacy": true,
        "epsilon": 1.0
    },
    "preserve_distributions": true
}

response = requests.post(
    "http://localhost:8030/api/v1/generate",
    json=synthesis
)

synthetic_dataset_id = response.json()["dataset_id"]
```

#### Validate Synthetic Data

```python
# Validate quality
validation = requests.post(
    "http://localhost:8030/api/v1/validate",
    json={
        "original_dataset_id": "customer_data",
        "synthetic_dataset_id": synthetic_dataset_id
    }
).json()

print(f"Statistical similarity: {validation['similarity_score']:.2%}")
print(f"Privacy score: {validation['privacy_score']:.2%}")
print(f"Utility score: {validation['utility_score']:.2%}")
```

---

### Accelerator 31: AIOps & Intelligent Observability

**Purpose**: AI-powered operations and incident management

#### Create Incident

```python
# Report incident
incident = {
    "title": "High API latency detected",
    "severity": "high",
    "service": "payment-api",
    "metrics": {
        "avg_latency_ms": 2500,
        "error_rate": 0.15
    },
    "auto_remediate": true
}

response = requests.post(
    "http://localhost:8031/api/v1/incidents",
    json=incident
)

incident_id = response.json()["incident_id"]
```

#### Get Root Cause Analysis

```python
# Analyze incident
analysis = requests.get(
    f"http://localhost:8031/api/v1/incidents/{incident_id}/analyze"
).json()

print(f"Root cause: {analysis['root_cause']}")
print(f"Confidence: {analysis['confidence']:.1%}")
print("\nRecommended actions:")
for action in analysis['remediation_actions']:
    print(f"  {action['priority']}: {action['description']}")
```

---

### Accelerator 32: Disaster Recovery & Multi-Region

**Purpose**: Ensure business continuity and disaster recovery

#### Create Backup

```python
# Backup dataset
backup = {
    "resource_type": "dataset",
    "resource_id": "customer_data",
    "backup_type": "full",
    "encryption": true,
    "retention_days": 30,
    "immutable": true  # WORM
}

response = requests.post(
    "http://localhost:8032/api/v1/backups",
    json=backup
)

backup_id = response.json()["backup_id"]
```

#### Configure Multi-Region Replication

```python
# Set up replication
replication = {
    "primary_region": "us-east-1",
    "replica_regions": ["us-west-2", "eu-west-1"],
    "resources": ["customer_data", "orders"],
    "replication_mode": "async",
    "rpo_minutes": 15,
    "rto_minutes": 60
}

requests.post(
    "http://localhost:8032/api/v1/replication",
    json=replication
)
```

#### Test Failover

```python
# Run DR drill
drill = {
    "drill_type": "failover",
    "target_region": "us-west-2",
    "resources": ["customer_data"],
    "validation_tests": true
}

response = requests.post(
    "http://localhost:8032/api/v1/drills",
    json=drill
)

print(f"Drill status: {response.json()['status']}")
print(f"RTO achieved: {response.json()['actual_rto_minutes']} minutes")
print(f"RPO achieved: {response.json()['actual_rpo_minutes']} minutes")
```

---

## Common Patterns

### Pagination

```python
# Paginated requests
page = 1
page_size = 100

while True:
    response = requests.get(
        f"http://localhost:8001/api/v1/datasets",
        params={"page": page, "page_size": page_size}
    ).json()

    for dataset in response['items']:
        process(dataset)

    if not response['has_more']:
        break
    page += 1
```

### Async Job Polling

```python
def wait_for_job(job_id, url, timeout=300):
    import time
    start = time.time()

    while time.time() - start < timeout:
        status = requests.get(f"{url}/jobs/{job_id}").json()

        if status['status'] == 'completed':
            return status['result']
        elif status['status'] == 'failed':
            raise Exception(f"Job failed: {status['error']}")

        time.sleep(5)

    raise TimeoutError("Job timed out")
```

### Batch Operations

```python
# Process in batches
def batch_process(items, batch_size=100):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        response = requests.post(
            "http://localhost:8001/api/v1/batch",
            json={"items": batch}
        )
        yield response.json()
```

---

## Error Handling

### Standard Error Response

All accelerators return consistent error formats:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid dataset_id provided",
    "details": {
      "field": "dataset_id",
      "reason": "Dataset not found"
    },
    "request_id": "req_12345"
  }
}
```

### Python Error Handling

```python
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
    result = response.json()
except requests.exceptions.HTTPError as e:
    error = e.response.json()['error']
    print(f"Error {error['code']}: {error['message']}")
    if 'details' in error:
        print(f"Details: {error['details']}")
except requests.exceptions.Timeout:
    print("Request timed out")
except requests.exceptions.ConnectionError:
    print("Failed to connect to service")
```

---

## Best Practices

### 1. Use Connection Pooling

```python
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Use session for all requests
response = session.get("http://localhost:8001/api/v1/datasets")
```

### 2. Implement Rate Limiting

```python
import time
from functools import wraps

def rate_limit(calls_per_second=10):
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

@rate_limit(calls_per_second=5)
def api_call(url):
    return requests.get(url)
```

### 3. Use Environment Variables

```python
import os

# Store credentials securely
API_KEY = os.getenv("DATAFORGE_API_KEY")
BASE_URL = os.getenv("DATAFORGE_BASE_URL", "http://localhost:8001")

headers = {"X-API-Key": API_KEY}
response = requests.get(f"{BASE_URL}/api/v1/datasets", headers=headers)
```

### 4. Log All API Calls

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def api_request(method, url, **kwargs):
    logger.info(f"{method} {url}")
    response = requests.request(method, url, **kwargs)
    logger.info(f"Response: {response.status_code}")
    return response
```

### 5. Validate Input Data

```python
from pydantic import BaseModel, validator

class DatasetCreate(BaseModel):
    name: str
    description: str
    connection_type: str

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('name cannot be empty')
        return v

# Use for validation
try:
    dataset = DatasetCreate(**user_input)
    response = requests.post(url, json=dataset.dict())
except ValidationError as e:
    print(f"Invalid input: {e}")
```

---

## Additional Resources

- **API Documentation**: http://localhost:PORT/docs (Swagger UI)
- **Health Checks**: http://localhost:PORT/health
- **Metrics**: http://localhost:PORT/metrics
- **OpenAPI Spec**: http://localhost:PORT/openapi.json

---

*Last Updated: November 17, 2025*
*DataForge AI Platform - Enterprise Data & AI Accelerators*
