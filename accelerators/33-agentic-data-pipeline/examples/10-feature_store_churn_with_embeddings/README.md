# Feature Store + LLM Embeddings - Churn Prediction

## Overview
Advanced ML feature pipeline combining structured data with LLM-generated embeddings for churn prediction.

## Use Case
SaaS companies building predictive models using both behavioral data and text (support tickets, emails).

## Key Features
- ✅ Multi-source feature engineering (17 sources)
- ✅ Text embeddings via Snowflake Cortex AI / OpenAI
- ✅ Feature Store (Feast or Databricks)
- ✅ Point-in-time correct joins
- ✅ Online + offline feature serving
- ✅ MLflow integration for model tracking

## Tech Stack
- Feature Engineering: dbt or Spark
- Embeddings: OpenAI API or Snowflake Cortex
- Feature Store: Feast (open-source) or Databricks
- ML Platform: MLflow
- Serving: Redis for low-latency online features

## Estimated Cost
~$400-600/month (compute + embeddings API + Redis)

## Example Prompt
```
Daily feature pipeline for churn model: join 17 sources (billing + usage + support
tickets), enrich with embeddings from OpenAI text via Snowflake Cortex AI, store
in Feature Store (Feast on Databricks).
```
