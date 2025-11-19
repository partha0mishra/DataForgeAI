# Example 06: Snowflake Native (Snowpark Python + Dynamic Tables)

**All-in on Snowflake**

## Overview

Snowflake-native pipeline using Snowpark Python: read from external stage @sales_csvs, transform with UDFs for PII masking, and write to dynamic tables with 5-minute refresh for near-real-time analytics.

## Architecture

```
┌──────────────┐     ┌────────────────┐     ┌──────────────────┐     ┌──────────────┐
│ S3 Stage     │────▶│ Snowpark Python│────▶│ Dynamic Tables   │────▶│ Dashboards   │
│ @sales_csvs  │     │ + PII Masking  │     │ (5-min refresh)  │     │ (Looker/etc) │
└──────────────┘     └────────────────┘     └──────────────────┘     └──────────────┘
```

## Use Case

Clients going all-in on Snowflake want to use native features: Snowpark, dynamic tables, Cortex AI. Shows:
- Snowpark Python DataFrames
- User-defined functions (UDFs) for transformations
- PII masking using UDFs
- Dynamic tables for automated refreshes
- Snowflake native scheduling

## Prerequisites

- **Snowflake Account:** With Snowpark enabled
- **Python 3.11:** Snowpark library installed
- **S3 Bucket:** With CSV data staged

## Quick Start

```bash
# Install Snowpark
pip install snowflake-snowpark-python

# Run Snowpark job
python snowpark/pii_masking_udf.py

# Create dynamic tables
snowsql -f sql/dynamic_tables.sql
```

## Expected Results

- CSV data ingested from S3
- PII fields (email, SSN) masked
- Dynamic tables auto-refresh every 5 minutes
- No external orchestrator needed

## What You'll Learn

- ✅ Snowpark Python DataFrames
- ✅ UDF development and registration
- ✅ Dynamic tables for incremental refresh
- ✅ External stages configuration
- ✅ Snowflake native scheduling
- ✅ Integration with Cortex AI (future)

## File Structure

```
06-snowflake-native/
├── README.md
├── config.yaml
├── snowpark/
│   ├── pii_masking_udf.py              # Snowpark transformations
│   └── dynamic_table_pipeline.py       # Pipeline orchestration
└── sql/
    └── dynamic_tables.sql              # DDL for dynamic tables
```

## Configuration

```yaml
snowflake:
  account: xy12345
  warehouse: COMPUTE_WH
  database: ANALYTICS
  schema: PUBLIC

stage:
  name: sales_csvs
  url: s3://my-bucket/sales/
  file_format: csv

dynamic_tables:
  refresh_mode: INCREMENTAL
  target_lag: 5 MINUTES
```

## Implementation Status

🚧 **Coming Soon** - This example is under development.

**Planned components:**
- [ ] Snowpark Python pipeline
- [ ] PII masking UDFs
- [ ] Dynamic table definitions
- [ ] Cortex AI integration examples
- [ ] Performance benchmarks

## Resources

- [Snowpark Developer Guide](https://docs.snowflake.com/en/developer-guide/snowpark/python/index.html)
- [Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-intro.html)
