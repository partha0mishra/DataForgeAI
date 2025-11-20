# Shopify API to Databricks Delta Live Tables - Real-Time Pipeline

## Overview

A near-real-time incremental pipeline that pulls order data from Shopify's REST API every 15 minutes and streams it into Databricks Delta Lake using Delta Live Tables (DLT) with automatic quality checks and medallion architecture.

**Business Use Case:** E-commerce companies need real-time visibility into orders, inventory, and customer behavior for operational dashboards and ML models.

## Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌────────────────────┐
│  Shopify API │────▶│  Delta Live     │────▶│   Delta Lake       │
│  (15min poll)│     │  Tables (DLT)   │     │  Bronze/Silver/Gold│
│  + Pagination│     │  + Quality Checks│    │   Unity Catalog    │
└──────────────┘     └─────────────────┘     └────────────────────┘
```

## Key Features

- ✅ **Near Real-Time**: 15-minute incremental sync with automatic checkpointing
- ✅ **Intelligent Rate Limiting**: Respects Shopify's API limits with exponential backoff
- ✅ **Auto-Pagination**: Handles large datasets with cursor-based pagination
- ✅ **Quality Checks**: DLT expectations enforce data quality rules
- ✅ **Exactly-Once**: Automatic deduplication and idempotency
- ✅ **Cost Optimized**: Uses Databricks serverless with spot instances

## Generated Prompt

```
Build an incremental pipeline that pulls new orders from Shopify API every 15 minutes,
merges into Delta Lake table in Databricks using Delta Live Tables, and handles rate
limits and pagination.
```

## Technology Stack

- **Source**: Shopify REST API (Admin API)
- **Lakehouse**: Databricks + Delta Lake + Unity Catalog
- **Orchestration**: Delta Live Tables (continuous mode)
- **Language**: Python + PySpark
- **Secret Management**: Databricks Secrets

## Estimated Costs

- **Databricks Serverless**: ~$200-250/month (for 10k orders/day, continuous processing)
  - DBU consumption: ~300 DBUs/month × $0.70
- **Delta Lake Storage**: ~$20/month (1TB data)
- **API Calls**: Free (Shopify Admin API)

**Total**: ~$220-270/month

## Prerequisites

1. Databricks workspace (AWS, Azure, or GCP)
2. Shopify store with Admin API access
3. Unity Catalog enabled (recommended for governance)
4. Databricks CLI installed: `pip install databricks-cli`

## Quick Start

### 1. Create Shopify Private App

1. Go to your Shopify Admin → Settings → Apps and sales channels
2. Click "Develop apps" → "Create an app"
3. Configure API scopes:
   - `read_orders`
   - `read_customers`
4. Install app and copy the **Admin API access token**

### 2. Configure Databricks Secrets

```bash
# Create secret scope
databricks secrets create-scope --scope shopify

# Add Shopify access token
databricks secrets put --scope shopify --key access_token
# Paste your token when prompted
```

### 3. Upload Notebook to Databricks

```bash
# Upload the DLT notebook
databricks workspace import \
    notebooks/shopify_dlt_pipeline.py \
    /Repos/Production/shopify_orders/shopify_dlt_pipeline \
    --language PYTHON
```

### 4. Update Pipeline Configuration

Edit `config/pipeline_config.json` and update:

```json
{
  "configuration": {
    "shopify.shop_url": "YOUR_STORE.myshopify.com"
  }
}
```

### 5. Create DLT Pipeline

```bash
# Create pipeline using Databricks CLI
databricks pipelines create --settings config/pipeline_config.json

# Get the pipeline ID from output
export PIPELINE_ID="<your-pipeline-id>"
```

### 6. Start the Pipeline

```bash
# Start continuous run
databricks pipelines start --pipeline-id $PIPELINE_ID

# Or use the UI:
# Go to Workflows → Delta Live Tables → Your Pipeline → Start
```

## Pipeline Details

### Data Flow

1. **Bronze Layer** (`shopify_orders_bronze`):
   - Raw API responses stored as JSON strings
   - Full auditability and reprocessing capability
   - Includes ingestion timestamp and source metadata

2. **Silver Layer** (`shopify_orders_silver`):
   - Parsed and flattened order data
   - Schema enforcement and data type conversions
   - DLT expectations for quality:
     - `valid_order_id`: Order ID must not be null
     - `valid_created_at`: Created timestamp must not be null
     - `reasonable_total`: Order total between $0 and $1M

3. **Gold Layer** (`shopify_orders_gold`):
   - Daily aggregated metrics:
     - Order count
     - Total revenue
     - Average order value
     - Unique customers
   - Partitioned by date and currency

### Rate Limiting Strategy

The pipeline implements intelligent rate limiting:

```python
# Check rate limit headers
call_limit = response.headers.get("X-Shopify-Shop-Api-Call-Limit")
current, max_calls = map(int, call_limit.split("/"))

# Back off at 80% capacity
if current / max_calls > 0.8:
    time.sleep(1.0)
```

### Error Handling

- **429 Rate Limited**: Automatic retry with `Retry-After` header
- **Network Errors**: Exponential backoff (5 retries max)
- **Malformed Data**: Records dropped with logging to DLT error log
- **API Changes**: Schema evolution handled automatically by Delta

## Monitoring

### Check Pipeline Health

```sql
-- View pipeline metrics
SELECT * FROM event_log('<pipeline-id>')
WHERE event_type = 'flow_progress'
ORDER BY timestamp DESC
LIMIT 10;

-- Check data quality
SELECT
  expectation,
  SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
  SUM(CASE WHEN status = 'dropped' THEN 1 ELSE 0 END) as dropped
FROM event_log('<pipeline-id>')
WHERE event_type = 'data_quality'
GROUP BY expectation;
```

### Query the Data

```sql
-- Latest orders
SELECT * FROM shopify_orders.shopify_orders_silver
ORDER BY created_at DESC
LIMIT 100;

-- Daily revenue trend
SELECT
  order_date,
  currency,
  order_count,
  total_revenue,
  avg_order_value
FROM shopify_orders.shopify_orders_gold
WHERE order_date >= CURRENT_DATE - INTERVAL 30 DAYS
ORDER BY order_date DESC;

-- Top customers by spend
SELECT
  customer_id,
  customer_email,
  COUNT(*) as order_count,
  SUM(total_price) as lifetime_value
FROM shopify_orders.shopify_orders_silver
GROUP BY customer_id, customer_email
ORDER BY lifetime_value DESC
LIMIT 100;
```

## Customization

### Add More Shopify Endpoints

Extend the pipeline to include products, inventory, or customers:

```python
@dlt.table(name="shopify_products_bronze")
def shopify_products_bronze():
    client = ShopifyClient(...)
    products = list(client.get_products())
    # ... similar pattern
```

### Integrate with Feature Store

Connect to Databricks Feature Store for ML:

```python
from databricks.feature_store import FeatureStoreClient

fs = FeatureStoreClient()

# Create feature table
fs.create_table(
    name="shopify_orders.customer_features",
    primary_keys=["customer_id"],
    df=customer_features_df,
    description="Customer behavioral features from Shopify orders"
)
```

### Add Real-Time Alerts

Use Databricks SQL Alerts for anomaly detection:

```sql
-- Alert on order volume drop
SELECT
  COUNT(*) as order_count_last_hour
FROM shopify_orders.shopify_orders_silver
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
HAVING order_count_last_hour < 10  -- Threshold
```

## Troubleshooting

### Issue: Pipeline stuck in "Waiting for resources"

**Solution**: Check cluster configuration. Ensure auto-scaling is enabled:
```json
{
  "autoscale": {
    "min_workers": 1,
    "max_workers": 5
  }
}
```

### Issue: "Invalid API credentials" error

**Solution**: Verify secret scope:
```bash
databricks secrets list --scope shopify
databricks secrets get --scope shopify --key access_token
```

### Issue: Data quality expectations failing

**Solution**: Adjust expectations or investigate data:
```sql
-- Find failing records
SELECT * FROM shopify_orders.shopify_orders_bronze
WHERE total_price > 1000000 OR total_price < 0;
```

## Best Practices

1. **Watermarking**: Pipeline uses `updated_at` for incremental processing
2. **Idempotency**: Upsert operations ensure safe re-runs
3. **Partitioning**: Gold tables partitioned by date for query performance
4. **Spot Instances**: Use `SPOT_WITH_FALLBACK` for 60-80% cost savings
5. **Photon**: Enable for 2-3× faster SQL queries on Delta tables

## Next Steps

- Add CDC tracking for order status changes
- Implement customer churn prediction model
- Connect to Tableau/Power BI for real-time dashboards
- Set up Unity Catalog for fine-grained access control
- Add Shopify webhook support for true real-time updates

## Resources

- [Shopify Admin API Docs](https://shopify.dev/docs/api/admin-rest)
- [Delta Live Tables Guide](https://docs.databricks.com/workflows/delta-live-tables/index.html)
- [Databricks Secrets](https://docs.databricks.com/security/secrets/index.html)
