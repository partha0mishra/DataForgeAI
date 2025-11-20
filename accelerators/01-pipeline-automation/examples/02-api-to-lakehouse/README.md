# Example 02: REST API → Lakehouse Incremental Load

**Most requested pattern in 2025**

## Overview

Build an incremental pipeline that pulls new orders from Shopify REST API every 15 minutes, merges into a Delta Lake table in Databricks using Delta Live Tables, and handles API rate limits, pagination, and retries automatically.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│ Shopify API  │────▶│ Airflow DAG  │────▶│ Databricks      │────▶│ Delta Lake   │
│ /orders      │     │ (15min)      │     │ Delta Live      │     │ orders_bronze│
│              │     │              │     │ Tables          │     │ orders_silver│
└──────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
     │                      │
     │ Rate Limits          │ Retry Logic
     │ Pagination           │ Incremental State
     └──────────────────────┘
```

## Use Case

Modern SaaS applications expose REST APIs for data extraction. This example shows:
- Incremental extraction using watermarks (modified_since)
- Handling API rate limits (429 responses)
- Automatic pagination for large result sets
- Exponential backoff retries
- Merge/upsert patterns in Delta Lake
- Secret management for API tokens

## Prerequisites

- **Shopify Account:** With API access token (or use mock API)
- **Databricks Workspace:** With Delta Live Tables enabled
- **Airflow:** Running instance
- **Storage:** S3/ADLS/GCS for Delta Lake storage

## Quick Start

### 1. Configure Secrets

```bash
# Store Shopify API credentials
airflow connections add 'shopify_api' \
    --conn-type 'http' \
    --conn-host 'your-store.myshopify.com' \
    --conn-extra '{"api_key": "your-api-key", "api_secret": "your-secret"}'

# Store Databricks token
airflow connections add 'databricks_default' \
    --conn-type 'databricks' \
    --conn-host 'your-workspace.cloud.databricks.com' \
    --conn-extra '{"token": "your-token"}'
```

### 2. Deploy Pipeline

```bash
# Copy DAG to Airflow
cp airflow/shopify_incremental_dag.py $AIRFLOW_HOME/dags/

# Deploy Delta Live Tables notebook
databricks workspace import notebooks/dlt_orders_pipeline.py \
    /Shared/pipelines/shopify_orders
```

### 3. Run Initial Load

```bash
# Trigger backfill for historical data
airflow dags trigger shopify_orders_incremental \
    --conf '{"start_date": "2024-01-01", "backfill": true}'
```

## Expected Results

- **API calls:** Automatic pagination through all orders
- **Rate limiting:** Automatic pause/retry on 429 errors
- **Bronze table:** Raw API responses in JSON format
- **Silver table:** Parsed, deduplicated, type-cast orders
- **Incremental:** Only new/updated orders fetched on subsequent runs

## What You'll Learn

- ✅ REST API integration with authentication
- ✅ Incremental extraction patterns
- ✅ Rate limit handling and exponential backoff
- ✅ Pagination strategies (cursor-based, offset-based)
- ✅ Delta Lake merge/upsert operations
- ✅ Delta Live Tables for CDC
- ✅ Secret management best practices

## File Structure

```
02-api-to-lakehouse/
├── README.md
├── config.yaml
├── airflow/
│   └── shopify_incremental_dag.py   # Orchestration DAG
├── scripts/
│   ├── shopify_extractor.py          # API client with retry logic
│   └── delta_merger.py                # Delta Lake merge logic
└── tests/
    └── test_api_client.py             # Unit tests
```

## Configuration

```yaml
# API settings
api:
  base_url: "https://your-store.myshopify.com"
  endpoint: "/admin/api/2024-01/orders.json"
  rate_limit: 40  # requests per second
  page_size: 250

# Incremental settings
incremental:
  watermark_column: "updated_at"
  state_table: "control.incremental_state"

# Delta Lake
delta:
  bronze_path: "s3://lakehouse/bronze/shopify/orders"
  silver_path: "s3://lakehouse/silver/shopify/orders"
  merge_key: "order_id"
```

## Implementation Status

🚧 **Coming Soon** - This example is under development.

**Planned components:**
- [ ] Shopify API client with OAuth 2.0
- [ ] Rate limiter with token bucket algorithm
- [ ] Cursor-based pagination handler
- [ ] Delta Live Tables pipeline definition
- [ ] Incremental watermark tracking
- [ ] Mock API server for testing

## Customization Guide

### Adapt for Other APIs

This pattern works for:
- **Salesforce:** Use bulk API for large extracts
- **ServiceNow:** Similar REST API pattern
- **Stripe:** Cursor-based pagination
- **HubSpot:** Rate limit handling similar to Shopify

### Change Target Platform

- **Snowflake:** Use MERGE statement instead of Delta
- **BigQuery:** Use MERGE or DML operations
- **PostgreSQL:** Use ON CONFLICT for upserts

## Troubleshooting

### Rate Limit Errors

```python
# Adjust rate limiting in config
api:
  rate_limit: 30  # Reduce if hitting limits
  backoff_multiplier: 2  # Exponential backoff
```

### Missing Records

```bash
# Check watermark state
SELECT * FROM control.incremental_state
WHERE source = 'shopify_orders';

# Reset if needed
UPDATE control.incremental_state
SET last_extracted_at = '2024-01-01'
WHERE source = 'shopify_orders';
```

## Next Steps

- Try **Example 03** for database CDC
- Try **Example 04** for complete medallion architecture
- Add data quality checks from Accelerator 02

## Resources

- [Shopify Admin API](https://shopify.dev/docs/api/admin-rest)
- [Delta Live Tables Guide](https://docs.databricks.com/delta-live-tables/)
- [REST API Best Practices](https://restfulapi.net/)
