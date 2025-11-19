# Example 04: Multi-source Medallion Architecture

**Lakehouse gold standard implementation**

## Overview

Create a complete medallion pipeline in Databricks: bronze layer from Kafka topic (iot_events) + PostgreSQL (sensor_readings) → silver layer with cleansing and sessionization → gold layer with aggregated dashboard tables, all using Delta Live Tables with auto-optimization.

## Architecture

```
┌────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ Kafka Topic    │────▶│                  │────▶│                   │
│ iot_events     │     │  BRONZE LAYER    │     │   SILVER LAYER    │
└────────────────┘     │  - Raw ingestion │     │   - Cleansed      │
                       │  - Schema on read│     │   - Sessionized   │
┌────────────────┐     │  - Append-only   │     │   - Deduplicated  │
│ PostgreSQL     │────▶│                  │     │   - Type-safe     │
│ sensor_readings│     └──────────────────┘     └───────────────────┘
└────────────────┘              │                         │
                                └─────────┬───────────────┘
                                          ▼
                                ┌───────────────────┐
                                │   GOLD LAYER      │
                                │   - Aggregated    │
                                │   - Business KPIs │
                                │   - BI-ready      │
                                └───────────────────┘
```

## Use Case

The medallion architecture is the standard for modern data lakehouses. This example shows:
- **Bronze:** Raw data preservation from multiple sources
- **Silver:** Cleaned, conformed, deduplicated data
- **Gold:** Business-level aggregates for analytics
- Multi-source integration (streaming + batch)
- Delta Live Tables for declarative pipelines
- Auto-optimization and vacuuming

## Prerequisites

- **Databricks Workspace:** With Delta Live Tables enabled
- **Kafka Cluster:** Or use Confluent Cloud
- **PostgreSQL:** Source database
- **S3/ADLS/GCS:** Delta Lake storage

## Quick Start

### 1. Set Up Sources

```bash
# Configure Kafka connection
databricks secrets create-scope --scope kafka
databricks secrets put --scope kafka --key bootstrap-servers
databricks secrets put --scope kafka --key api-key

# Configure PostgreSQL connection
databricks secrets create-scope --scope postgres
databricks secrets put --scope postgres --key jdbc-url
databricks secrets put --scope postgres --key password
```

### 2. Deploy DLT Pipeline

```bash
# Create DLT pipeline
databricks pipelines create --settings databricks/dlt_pipeline_config.json

# Start the pipeline
databricks pipelines start --pipeline-id <pipeline-id>
```

### 3. Generate Test Data

```bash
# Start Kafka producer (mock IoT events)
python kafka/mock_producer.py --events 10000

# Load sensor readings to PostgreSQL
psql -h localhost -U postgres -f scripts/load_sensor_data.sql
```

## Expected Results

- **Bronze tables:**
  - `iot_events_raw` - Streaming Kafka messages
  - `sensor_readings_raw` - Batch PostgreSQL snapshots

- **Silver tables:**
  - `iot_events_clean` - Parsed JSON, validated
  - `sensor_readings_enriched` - Joined with metadata
  - `user_sessions` - Sessionized event sequences

- **Gold tables:**
  - `hourly_metrics` - Aggregated by hour
  - `device_health` - Current device status
  - `kpi_dashboard` - Executive metrics

## What You'll Learn

- ✅ Medallion architecture implementation
- ✅ Delta Live Tables declarative syntax
- ✅ Streaming + batch integration
- ✅ Schema evolution handling
- ✅ Data quality expectations
- ✅ Auto-optimization features
- ✅ Multi-hop transformations

## File Structure

```
04-medallion-architecture/
├── README.md
├── config.yaml
├── databricks/
│   ├── dlt_pipeline.py                  # Delta Live Tables definition
│   └── notebook_bronze_silver_gold.py   # Alternative: notebook-based
├── kafka/
│   └── mock_producer.py                 # IoT event simulator
└── monitoring/
    └── data_quality_checks.py           # Quality metrics
```

## Configuration

```yaml
bronze:
  iot_events:
    source_type: kafka
    topic: iot_events
    format: json
    checkpoint_location: s3://lakehouse/checkpoints/iot

  sensor_readings:
    source_type: jdbc
    table: public.sensor_readings
    mode: incremental
    watermark_column: updated_at

silver:
  quality_checks:
    - expect_not_null: [device_id, timestamp]
    - expect_range: {temperature: [-50, 150]}

gold:
  aggregation_windows:
    - hourly
    - daily
  materialization: incremental
```

## Implementation Status

🚧 **Coming Soon** - This example is under development.

**Planned components:**
- [ ] Complete DLT pipeline definition
- [ ] Streaming source configuration
- [ ] Quality expectation framework
- [ ] Gold layer aggregation logic
- [ ] Performance monitoring dashboard

## Customization Guide

### Add New Bronze Source

```python
@dlt.table(comment="New source ingestion")
def new_source_bronze():
    return spark.readStream.format("delta") \
        .option("path", "s3://bucket/new-source") \
        .load()
```

### Add Quality Expectations

```python
@dlt.expect_or_drop("valid_timestamp", "timestamp IS NOT NULL")
@dlt.expect_or_fail("valid_id", "id > 0")
```

### Custom Gold Metrics

```python
@dlt.table
def custom_kpi():
    return dlt.read("silver_events") \
        .groupBy(window("timestamp", "1 hour")) \
        .agg(count("*").alias("event_count"))
```

## Troubleshooting

### DLT Pipeline Failed

```bash
# Check pipeline logs
databricks pipelines get --pipeline-id <id>

# Review expectation violations
SELECT * FROM event_log
WHERE details:flow_progress.metrics.num_output_rows = 0
```

### Streaming Lag

```python
# Monitor lag in DLT
spark.sql("""
  SELECT
    name,
    flow_name,
    metrics.backlog_bytes
  FROM event_log
  WHERE event_type = 'flow_progress'
""")
```

## Performance Optimization

```yaml
# DLT optimizations
compute:
  cluster_mode: enhanced  # Photon enabled
  min_workers: 2
  max_workers: 8
  auto_scale: true

storage:
  optimize_write: true
  auto_compact: true
  deletion_vectors: true  # For CDC
```

## Next Steps

- Try **Example 05** for real-time alerting
- Add **Data Catalog** from Accelerator 04
- Implement **Cost Optimization** patterns from Example 08

## Resources

- [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
- [Delta Live Tables](https://docs.databricks.com/delta-live-tables/)
- [Streaming Best Practices](https://docs.databricks.com/structured-streaming/)
