# Oracle CDC to Snowflake - Database Migration Pipeline

## Overview
Incremental Change Data Capture (CDC) pipeline migrating Oracle database tables to Snowflake with schema evolution support.

## Use Case
Legacy Oracle database modernization to cloud data warehouse.

## Key Features
- ✅ Incremental CDC using Oracle flashback/triggers
- ✅ Schema evolution handling
- ✅ Type mapping (Oracle → Snowflake)
- ✅ Parallel table loads
- ✅ Automated testing and validation

## Tech Stack
- Source: Oracle 12c+
- Target: Snowflake
- CDC: Debezium or Oracle GoldenGate
- Orchestration: Airflow

## Estimated Cost
~$300-400/month (Oracle connector licensing, Snowflake compute)

## Example Prompt
```
Migrate Oracle tables hr.employees and finance.gl_transactions to Snowflake
using incremental CDC with change tracking, including schema evolution handling.
```
