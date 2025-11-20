# Snowpark Python Native Pipeline - Snowflake

## Overview
Snowflake-native data pipeline using Snowpark for Python transformations, Dynamic Tables, and Snowflake Cortex for ML.

## Use Case
Organizations fully committed to Snowflake ecosystem wanting native Python processing.

## Key Features
- ✅ Snowpark Python UDFs for complex transformations
- ✅ PII masking using Snowflake's masking policies
- ✅ Dynamic Tables for incremental materialization
- ✅ Snowflake Cortex AI for embeddings and ML
- ✅ Native task orchestration (no external tool)

## Tech Stack
- Platform: Snowflake (all-in-one)
- Language: Snowpark Python
- ML: Snowflake Cortex AI
- Orchestration: Snowflake Tasks

## Estimated Cost
~$200-300/month (Snowflake credits for compute + storage)

## Example Prompt
```
Snowflake-native pipeline using Snowpark Python: read from stage @sales_csvs,
transform with UDFs for PII masking, write to dynamic tables with 5-minute refresh.
```
