# Google Analytics 4 to BigQuery + Looker

## Overview
Marketing analytics pipeline from GA4 to BigQuery with automatic Looker dashboard refresh.

## Use Case
Marketing teams need real-time visibility into web analytics and ad performance.

## Key Features
- ✅ GA4 BigQuery export (native integration)
- ✅ Scheduled queries for transformations
- ✅ Partitioned tables for cost efficiency
- ✅ Automatic Looker dashboard refresh via API
- ✅ Attribution modeling and funnel analysis

## Tech Stack
- Source: Google Analytics 4
- Warehouse: BigQuery
- BI: Looker
- Orchestration: Cloud Scheduler + Cloud Functions

## Estimated Cost
~$150-250/month (BigQuery scanning + storage, Looker seats)

## Example Prompt
```
Orchestrate BigQuery: scheduled query that pulls from Google Analytics 4 + Ads →
partitioned table → triggers Looker dashboard refresh via API.
```
