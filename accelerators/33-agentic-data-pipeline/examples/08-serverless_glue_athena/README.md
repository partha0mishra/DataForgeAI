# Serverless AWS Glue + Athena Pipeline

## Overview
Cost-optimized serverless pipeline using AWS Glue auto-scaling and Athena for querying.

## Use Case
Startups and cost-conscious teams processing moderate data volumes (< 10TB/month).

## Key Features
- ✅ Event-driven (S3 PUT trigger)
- ✅ Glue 4.0+ with auto-scaling
- ✅ Partitioned Parquet output
- ✅ Athena for SQL queries (no warehouse)
- ✅ S3 lifecycle policies for cost optimization

## Tech Stack
- Processing: AWS Glue (Spark)
- Storage: S3 (Parquet)
- Query: Amazon Athena
- Orchestration: Step Functions

## Estimated Cost
~$50-100/month (for 5TB processed, serverless pricing)

## Example Prompt
```
Build a serverless pipeline using only AWS Glue + Athena + Step Functions:
trigger on S3 put, auto-scale Spark jobs, shut down after completion, cost
under $50/month for 10TB processed.
```
