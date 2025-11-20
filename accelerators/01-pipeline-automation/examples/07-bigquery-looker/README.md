# Example 07: BigQuery + Looker Refresh Orchestration

**The marketing analytics stack**

## Overview

Orchestrate BigQuery: scheduled query that pulls from Google Analytics 4 + Google Ads → partitioned table → triggers Looker dashboard refresh via API for marketing teams.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ GA4 Export  │────▶│             │     │              │     │              │
└─────────────┘     │  BigQuery   │────▶│ Materialized │────▶│ Looker API   │
┌─────────────┐     │  Scheduled  │     │ Views        │     │ Refresh      │
│ Google Ads  │────▶│  Query      │     │ (Partitioned)│     │ Dashboards   │
└─────────────┘     └─────────────┘     └──────────────┘     └──────────────┘
```

## Use Case

Marketing/analytics teams live in GA4 → BigQuery → Looker. Shows:
- BigQuery scheduled queries
- GA4 export integration
- Google Ads API data pull
- Partitioned table optimization
- Looker dashboard refresh automation

## Prerequisites

- **BigQuery:** Project with GA4 export enabled
- **Google Ads Account:** API access
- **Looker Instance:** API credentials
- **Airflow:** For orchestration

## Quick Start

```bash
# Set up BigQuery scheduled query
bq query --use_legacy_sql=false --destination_table=analytics.ga4_sessions \
  --schedule='every 1 hours' < bigquery/scheduled_queries.sql

# Deploy Airflow DAG
cp airflow/ga4_to_looker_dag.py $AIRFLOW_HOME/dags/

# Trigger dashboard refresh
python looker/refresh_dashboard.py --dashboard-id 123
```

## Expected Results

- GA4 data + Google Ads merged hourly
- Partitioned tables for cost optimization
- Looker dashboards auto-refresh
- Marketing teams see fresh data

## What You'll Learn

- ✅ BigQuery scheduled queries
- ✅ GA4 export schema navigation
- ✅ Google Ads API integration
- ✅ Table partitioning strategies
- ✅ Looker API automation
- ✅ Cost optimization techniques

## File Structure

```
07-bigquery-looker/
├── README.md
├── config.yaml
├── airflow/
│   └── ga4_to_looker_dag.py           # Orchestration
├── bigquery/
│   ├── scheduled_queries.sql          # BigQuery scheduled queries
│   └── partitioning_setup.sql         # Table optimizations
└── looker/
    └── refresh_dashboard.py           # Looker API client
```

## Configuration

```yaml
bigquery:
  project_id: my-analytics-project
  dataset: analytics
  ga4_table: events_*  # Sharded by date
  ads_table: google_ads_raw

looker:
  base_url: https://mycompany.looker.com
  client_id: ${LOOKER_CLIENT_ID}
  client_secret: ${LOOKER_CLIENT_SECRET}
  dashboard_ids: [123, 456, 789]

schedule:
  interval: hourly
  lookback_hours: 2  # Reprocess last 2 hours for late data
```

## Implementation Status

🚧 **Coming Soon** - This example is under development.

**Planned components:**
- [ ] BigQuery scheduled query templates
- [ ] GA4 event parsing SQL
- [ ] Google Ads API connector
- [ ] Looker API refresh script
- [ ] Cost optimization guide

## Resources

- [GA4 BigQuery Export Schema](https://support.google.com/analytics/answer/9358801)
- [Looker API Documentation](https://developers.looker.com/api/overview)
- [BigQuery Cost Optimization](https://cloud.google.com/bigquery/docs/best-practices-costs)
