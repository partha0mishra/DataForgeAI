# Multi-Source Medallion Architecture - Databricks

## Overview
Enterprise-grade medallion lakehouse combining streaming (Kafka) and batch (PostgreSQL) sources with Delta Live Tables.

## Use Case
Unified data platform for IoT sensor data and operational databases.

## Key Features
- ✅ Bronze: Raw ingestion from Kafka + PostgreSQL
- ✅ Silver: Cleansing, sessionization, and joins
- ✅ Gold: Pre-aggregated business metrics
- ✅ Auto-optimization and compaction
- ✅ Unity Catalog governance

## Tech Stack
- Streaming: Apache Kafka
- Batch: PostgreSQL
- Lakehouse: Databricks + Delta Lake
- Orchestration: Delta Live Tables

## Estimated Cost
~$500-700/month (continuous streaming + batch processing)

## Example Prompt
```
Create a full medallion pipeline in Databricks: bronze from Kafka topic iot_events
+ PostgreSQL sensor_readings → silver with cleansing and sessionization → gold
aggregated dashboard tables, using Delta Live Tables and auto-optimized.
```
