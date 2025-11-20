# Example 03: Legacy RDBMS → Modern Warehouse Migration

**The lift-and-shift migration blueprint**

## Overview

Migrate Oracle tables (hr.employees, finance.gl_transactions) to Snowflake using incremental CDC with change tracking, including automatic schema evolution handling. This is the pattern for getting off legacy systems like Oracle, Teradata, or Netezza.

## Architecture

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Oracle Database  │────▶│ Airflow DAG     │────▶│ Snowflake        │
│ hr.employees     │     │ - CDC Capture   │     │ hr.employees     │
│ finance.gl_*     │     │ - Schema Diff   │     │ finance.gl_*     │
│ (SCN tracking)   │     │ - Parallel Load │     │ (Auto-evolve)    │
└──────────────────┘     └─────────────────┘     └──────────────────┘
         │                                                │
         │ Change Data Capture                           │
         └───────────────────────────────────────────────┘
                   Incremental Only
```

## Use Case

60% of data modernization projects start with "migrate from legacy database." This example shows:
- Initial full load of existing tables
- Incremental CDC using Oracle SCN or timestamps
- Automatic schema drift detection and handling
- Parallel table migration
- Data type mapping (Oracle → Snowflake)
- Validation and reconciliation

## Prerequisites

- **Oracle Database:** With SELECT privileges on source tables
- **Snowflake Account:** Target warehouse
- **Airflow:** With Oracle provider installed
- **Network Access:** From Airflow to Oracle (VPN/private link)

## Quick Start

### 1. Configure Source and Target

```bash
# Oracle connection
airflow connections add 'oracle_source' \
    --conn-type 'oracle' \
    --conn-host 'oracle-host' \
    --conn-schema 'HR' \
    --conn-login 'readonly_user' \
    --conn-password 'password' \
    --conn-port 1521 \
    --conn-extra '{"service_name": "ORCL"}'

# Snowflake connection
airflow connections add 'snowflake_target' \
    --conn-type 'snowflake' \
    --conn-login 'migration_user' \
    --conn-password 'password' \
    --conn-extra '{"account": "xy12345", "warehouse": "MIGRATION_WH", "database": "MIGRATED", "role": "SYSADMIN"}'
```

### 2. Define Migration Manifest

```yaml
# migration_manifest.yaml
tables:
  - source_schema: HR
    source_table: EMPLOYEES
    target_schema: hr
    target_table: employees
    primary_key: [employee_id]
    incremental_column: last_updated
    parallel_degree: 4

  - source_schema: FINANCE
    source_table: GL_TRANSACTIONS
    target_schema: finance
    target_table: gl_transactions
    primary_key: [transaction_id]
    incremental_column: created_date
    partition_column: fiscal_year
```

### 3. Run Migration

```bash
# Discovery phase - analyze source schemas
./scripts/schema_discovery.py --connection oracle_source

# Initial full load
airflow dags trigger oracle_migration --conf '{"mode": "full"}'

# Switch to incremental
airflow dags trigger oracle_migration --conf '{"mode": "incremental"}'
```

## Expected Results

After successful migration:
- All tables replicated to Snowflake
- Ongoing CDC captures changes every 15 minutes
- Schema changes automatically detected and applied
- Row count reconciliation reports
- Performance metrics tracked

## What You'll Learn

- ✅ CDC patterns for RDBMS systems
- ✅ Schema discovery and DDL generation
- ✅ Data type mapping between systems
- ✅ Parallel data loading for performance
- ✅ Incremental extraction strategies
- ✅ Validation and reconciliation
- ✅ Schema evolution handling

## File Structure

```
03-oracle-to-snowflake/
├── README.md
├── config.yaml
├── migration_manifest.yaml          # Tables to migrate
├── airflow/
│   └── oracle_cdc_dag.py           # Orchestration
├── scripts/
│   ├── schema_discovery.py          # Auto-discover schemas
│   └── cdc_processor.py             # Change data capture
└── sql/
    ├── oracle_cdc_setup.sql         # Enable CDC on Oracle
    └── snowflake_target_ddl.sql     # Target DDL
```

## Configuration

```yaml
migration:
  mode: incremental  # full | incremental
  batch_size: 50000
  parallel_workers: 4

source:
  database: ORCL
  schemas: [HR, FINANCE]
  cdc_method: scn  # scn | timestamp

target:
  database: MIGRATED
  warehouse: MIGRATION_WH
  file_format: parquet
  stage: @migration_stage

validation:
  row_count_check: true
  sample_validation: 1000  # rows
  reconciliation_table: control.migration_status
```

## Implementation Status

🚧 **Coming Soon** - This example is under development.

**Planned components:**
- [ ] Oracle SCN-based CDC extraction
- [ ] Schema discovery and mapping
- [ ] DDL generator (Oracle → Snowflake)
- [ ] Parallel bulk loader
- [ ] Reconciliation framework
- [ ] Migration dashboard

## Data Type Mapping

| Oracle Type | Snowflake Type | Notes |
|-------------|----------------|-------|
| NUMBER(p,s) | NUMBER(p,s) | Direct mapping |
| VARCHAR2 | VARCHAR | Snowflake max 16MB |
| DATE | DATE | Same precision |
| TIMESTAMP | TIMESTAMP_NTZ | No timezone in Oracle |
| CLOB | VARCHAR | Convert to string |
| BLOB | BINARY | Large objects |
| RAW | BINARY | Binary data |

## Troubleshooting

### Oracle Connection Timeout

```bash
# Test connectivity
sqlplus readonly_user/password@oracle-host:1521/ORCL

# Check Airflow can reach Oracle
airflow connections test oracle_source
```

### CDC Missing Changes

```sql
-- Verify SCN tracking
SELECT current_scn FROM v$database;

-- Check flashback privileges
GRANT SELECT ANY TRANSACTION TO readonly_user;
GRANT FLASHBACK ANY TABLE TO readonly_user;
```

### Snowflake Load Failures

```sql
-- Check staging files
LIST @migration_stage;

-- Review COPY errors
SELECT * FROM TABLE(VALIDATE(migration_stage, FILE_FORMAT => 'csv_format'));
```

## Performance Tuning

### For Large Tables (> 100M rows)

```yaml
# Use partitioned extraction
extraction:
  partition_column: created_date
  partition_size: 1_month
  parallel_partitions: 8
```

### For Wide Tables (> 100 columns)

```yaml
# Column subsetting
columns:
  include_pattern: "^(?!internal_).*"  # Exclude internal_* columns
  max_column_width: 16000  # Truncate large text
```

## Next Steps

- Try **Example 04** for medallion transformation post-migration
- Add **Data Quality** checks from Accelerator 02
- Set up **Data Catalog** with Accelerator 04

## Resources

- [Oracle Flashback Query](https://docs.oracle.com/en/database/oracle/oracle-database/19/adfns/flashback.html)
- [Snowflake Bulk Loading](https://docs.snowflake.com/en/user-guide/data-load-bulk.html)
- [CDC Design Patterns](https://www.confluent.io/blog/event-sourcing-cqrs-stream-processing-apache-kafka-whats-connection/)
