/*
 * BigQuery Table Partitioning and Clustering Setup
 *
 * This script demonstrates production-ready BigQuery table design with:
 * - Date partitioning for cost optimization
 * - Clustering for query performance
 * - Materialized views for pre-aggregated data
 * - Table expiration policies
 * - Cost-saving best practices
 *
 * Prerequisites:
 * - BigQuery project with billing enabled
 * - Appropriate permissions (BigQuery Data Editor)
 *
 * Cost Optimization Benefits:
 * - Partitioning: Query only relevant date ranges (reduces scanned data)
 * - Clustering: Skip irrelevant data blocks (improves performance)
 * - Materialized views: Pre-compute aggregations (faster queries)
 * - Expiration: Automatic cleanup of old data (reduces storage costs)
 *
 * Usage:
 *   bq query --use_legacy_sql=false < partitioning_setup.sql
 */

-- ============================================================================
-- DATASET CREATION
-- ============================================================================

-- Create analytics dataset if it doesn't exist
CREATE SCHEMA IF NOT EXISTS `my-analytics-project.analytics`
OPTIONS(
  description="Analytics dataset for GA4 and marketing data",
  location="US"  -- or "EU", "asia-northeast1", etc.
);

-- ============================================================================
-- PARTITIONED TABLES: GA4 Events
-- ============================================================================

/*
 * Partitioned table for GA4 events
 * - Partitioned by event_date (YYYY-MM-DD)
 * - Clustered by user_pseudo_id and event_name for common query patterns
 * - 90-day partition expiration (adjust based on retention requirements)
 */

CREATE TABLE IF NOT EXISTS `analytics.ga4_events_raw`
(
  -- Event identification
  event_date STRING NOT NULL,
  event_timestamp INTEGER,
  event_name STRING,
  event_previous_timestamp INTEGER,
  event_value_in_usd FLOAT64,
  event_bundle_sequence_id INTEGER,
  event_server_timestamp_offset INTEGER,

  -- User identification
  user_pseudo_id STRING,
  user_id STRING,

  -- Event parameters (nested)
  event_params ARRAY<STRUCT<
    key STRING,
    value STRUCT<
      string_value STRING,
      int_value INTEGER,
      float_value FLOAT64,
      double_value FLOAT64
    >
  >>,

  -- User properties (nested)
  user_properties ARRAY<STRUCT<
    key STRING,
    value STRUCT<
      string_value STRING,
      int_value INTEGER,
      float_value FLOAT64,
      double_value FLOAT64,
      set_timestamp_micros INTEGER
    >
  >>,

  -- User first touch timestamp
  user_first_touch_timestamp INTEGER,

  -- User LTV
  user_ltv STRUCT<
    revenue FLOAT64,
    currency STRING
  >,

  -- Device
  device STRUCT<
    category STRING,
    mobile_brand_name STRING,
    mobile_model_name STRING,
    mobile_marketing_name STRING,
    mobile_os_hardware_model STRING,
    operating_system STRING,
    operating_system_version STRING,
    vendor_id STRING,
    advertising_id STRING,
    language STRING,
    is_limited_ad_tracking STRING,
    time_zone_offset_seconds INTEGER,
    browser STRING,
    browser_version STRING,
    web_info STRUCT<
      browser STRING,
      browser_version STRING,
      hostname STRING
    >
  >,

  -- Geography
  geo STRUCT<
    continent STRING,
    country STRING,
    region STRING,
    city STRING,
    sub_continent STRING,
    metro STRING
  >,

  -- App info
  app_info STRUCT<
    id STRING,
    version STRING,
    install_store STRING,
    firebase_app_id STRING,
    install_source STRING
  >,

  -- Traffic source
  traffic_source STRUCT<
    name STRING,
    medium STRING,
    source STRING
  >,

  -- Stream and platform
  stream_id STRING,
  platform STRING,

  -- Ecommerce
  ecommerce STRUCT<
    transaction_id STRING,
    value FLOAT64,
    tax FLOAT64,
    shipping FLOAT64,
    currency STRING,
    unique_items INTEGER,
    purchase_revenue_in_usd FLOAT64,
    purchase_revenue FLOAT64,
    refund_value_in_usd FLOAT64,
    refund_value FLOAT64,
    shipping_value_in_usd FLOAT64,
    shipping_value FLOAT64,
    tax_value_in_usd FLOAT64,
    tax_value FLOAT64,
    total_item_quantity INTEGER
  >,

  -- Items (nested)
  items ARRAY<STRUCT<
    item_id STRING,
    item_name STRING,
    item_brand STRING,
    item_variant STRING,
    item_category STRING,
    item_category2 STRING,
    item_category3 STRING,
    item_category4 STRING,
    item_category5 STRING,
    price_in_usd FLOAT64,
    price FLOAT64,
    quantity INTEGER,
    item_revenue_in_usd FLOAT64,
    item_revenue FLOAT64,
    item_refund_in_usd FLOAT64,
    item_refund FLOAT64,
    coupon STRING,
    affiliation STRING,
    location_id STRING,
    item_list_id STRING,
    item_list_name STRING,
    item_list_index STRING,
    promotion_id STRING,
    promotion_name STRING,
    creative_name STRING,
    creative_slot STRING
  >>,

  -- Privacy info
  privacy_info STRUCT<
    analytics_storage STRING,
    ads_storage STRING,
    uses_transient_token STRING
  >,

  -- Collected traffic source
  collected_traffic_source STRUCT<
    manual_campaign_id STRING,
    manual_campaign_name STRING,
    manual_source STRING,
    manual_medium STRING,
    manual_term STRING,
    manual_content STRING,
    gclid STRING,
    dclid STRING,
    srsltid STRING
  >>,

  -- Is active user
  is_active_user BOOLEAN
)
PARTITION BY DATE(PARSE_DATE('%Y%m%d', event_date))
CLUSTER BY user_pseudo_id, event_name
OPTIONS(
  description="Raw GA4 events from BigQuery export",
  partition_expiration_days=90,
  require_partition_filter=true  -- Enforce partition filters in queries
);

-- ============================================================================
-- PARTITIONED TABLES: Processed Sessions
-- ============================================================================

/*
 * Partitioned table for processed sessions
 * - Partitioned by session_date
 * - Clustered by user_pseudo_id, traffic_source, device_category
 * - 365-day partition expiration (1 year retention)
 */

CREATE TABLE IF NOT EXISTS `analytics.ga4_sessions_partitioned`
(
  -- Session identification
  user_pseudo_id STRING NOT NULL,
  session_id INTEGER NOT NULL,
  session_date DATE NOT NULL,
  session_start TIMESTAMP,
  session_end TIMESTAMP,
  session_duration_seconds INTEGER,

  -- Session metrics
  total_events INTEGER,
  page_views INTEGER,
  engagement_events INTEGER,
  scroll_events INTEGER,
  click_events INTEGER,
  is_engaged_session INTEGER,
  is_quality_session BOOLEAN,
  is_conversion_session BOOLEAN,

  -- Pages
  landing_page STRING,
  landing_page_title STRING,
  exit_page STRING,

  -- Attribution
  traffic_source STRING,
  traffic_medium STRING,
  campaign_name STRING,
  campaign_id STRING,

  -- Device
  device_category STRING,
  device_os STRING,
  device_browser STRING,

  -- Geography
  geo_country STRING,
  geo_region STRING,
  geo_city STRING,

  -- Conversions
  purchase_events INTEGER,
  revenue_usd FLOAT64,
  items_purchased INTEGER,
  sign_up_events INTEGER,
  add_to_cart_events INTEGER,
  begin_checkout_events INTEGER,

  -- User info
  user_id STRING,
  session_number INTEGER,
  user_type STRING,

  -- Platform
  platform STRING,
  stream_id STRING,

  -- Calculated metrics
  revenue_per_page_view FLOAT64,

  -- Metadata
  processed_at TIMESTAMP
)
PARTITION BY session_date
CLUSTER BY user_pseudo_id, traffic_source, device_category
OPTIONS(
  description="Processed GA4 sessions with aggregated metrics",
  partition_expiration_days=365,
  require_partition_filter=false  -- Allow queries without partition filter for flexibility
);

-- ============================================================================
-- PARTITIONED TABLES: Marketing Performance
-- ============================================================================

/*
 * Partitioned table for combined marketing data
 * - Partitioned by report_date
 * - Clustered by campaign_id, traffic_source
 */

CREATE TABLE IF NOT EXISTS `analytics.marketing_performance_partitioned`
(
  -- Date and campaign
  report_date DATE NOT NULL,
  campaign_id STRING,
  campaign_name STRING,
  ad_group_id STRING,
  ad_group_name STRING,

  -- Traffic source
  traffic_source STRING,
  traffic_medium STRING,
  device_category STRING,

  -- Google Ads metrics
  impressions INTEGER,
  clicks INTEGER,
  cost_usd FLOAT64,
  ads_conversions FLOAT64,
  ads_conversion_value FLOAT64,

  -- GA4 metrics
  users INTEGER,
  sessions INTEGER,
  engaged_sessions INTEGER,
  page_views INTEGER,
  total_session_duration_seconds INTEGER,
  purchases INTEGER,
  revenue_usd FLOAT64,
  items_purchased INTEGER,
  sign_ups INTEGER,
  quality_sessions INTEGER,

  -- Calculated metrics
  ctr FLOAT64,  -- Click-through rate
  cpc FLOAT64,  -- Cost per click
  engagement_rate FLOAT64,
  conversion_rate FLOAT64,
  revenue_per_session FLOAT64,
  roas FLOAT64,  -- Return on ad spend
  cpa FLOAT64,   -- Cost per acquisition
  avg_session_duration FLOAT64,

  -- Metadata
  processed_at TIMESTAMP
)
PARTITION BY report_date
CLUSTER BY campaign_id, traffic_source
OPTIONS(
  description="Combined GA4 and Google Ads performance metrics",
  partition_expiration_days=730  -- 2 years
);

-- ============================================================================
-- MATERIALIZED VIEWS: Pre-aggregated Analytics
-- ============================================================================

/*
 * Materialized view for daily marketing summary
 * - Automatically refreshes when source table changes
 * - Pre-computes aggregations for faster dashboard queries
 * - Cost-effective for frequently accessed aggregations
 */

CREATE MATERIALIZED VIEW IF NOT EXISTS `analytics.marketing_daily_summary_mv`
PARTITION BY report_date
CLUSTER BY traffic_source, device_category
OPTIONS(
  description="Materialized view for daily marketing summary",
  enable_refresh=true,
  refresh_interval_minutes=60  -- Refresh every hour
) AS
SELECT
  report_date,
  traffic_source,
  traffic_medium,
  device_category,

  -- Aggregated metrics
  SUM(impressions) AS total_impressions,
  SUM(clicks) AS total_clicks,
  SUM(cost_usd) AS total_cost_usd,
  SUM(users) AS total_users,
  SUM(sessions) AS total_sessions,
  SUM(engaged_sessions) AS total_engaged_sessions,
  SUM(page_views) AS total_page_views,
  SUM(purchases) AS total_purchases,
  SUM(revenue_usd) AS total_revenue_usd,
  SUM(sign_ups) AS total_sign_ups,

  -- Calculated averages
  SAFE_DIVIDE(SUM(clicks), SUM(impressions)) AS avg_ctr,
  SAFE_DIVIDE(SUM(cost_usd), SUM(clicks)) AS avg_cpc,
  SAFE_DIVIDE(SUM(engaged_sessions), SUM(sessions)) AS avg_engagement_rate,
  SAFE_DIVIDE(SUM(purchases), SUM(sessions)) AS avg_conversion_rate,
  SAFE_DIVIDE(SUM(revenue_usd), SUM(sessions)) AS avg_revenue_per_session,
  SAFE_DIVIDE(SUM(revenue_usd), SUM(cost_usd)) AS avg_roas,
  SAFE_DIVIDE(SUM(cost_usd), SUM(purchases)) AS avg_cpa,

  -- Metadata
  COUNT(*) AS campaign_count,
  CURRENT_TIMESTAMP() AS last_updated

FROM `analytics.marketing_performance_partitioned`
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY
  report_date,
  traffic_source,
  traffic_medium,
  device_category;

-- ============================================================================
-- MATERIALIZED VIEWS: Top Campaigns
-- ============================================================================

/*
 * Materialized view for top performing campaigns (last 30 days)
 */

CREATE MATERIALIZED VIEW IF NOT EXISTS `analytics.top_campaigns_mv`
OPTIONS(
  description="Top performing campaigns in last 30 days",
  enable_refresh=true,
  refresh_interval_minutes=60
) AS
SELECT
  campaign_id,
  campaign_name,
  traffic_source,

  -- Performance metrics
  SUM(sessions) AS total_sessions,
  SUM(revenue_usd) AS total_revenue,
  SUM(cost_usd) AS total_cost,
  SUM(purchases) AS total_purchases,

  -- Efficiency metrics
  SAFE_DIVIDE(SUM(revenue_usd), SUM(cost_usd)) AS roas,
  SAFE_DIVIDE(SUM(cost_usd), SUM(purchases)) AS cpa,
  SAFE_DIVIDE(SUM(purchases), SUM(sessions)) AS conversion_rate,

  -- Rankings
  RANK() OVER (ORDER BY SUM(revenue_usd) DESC) AS revenue_rank,
  RANK() OVER (ORDER BY SAFE_DIVIDE(SUM(revenue_usd), SUM(cost_usd)) DESC) AS roas_rank,

  CURRENT_TIMESTAMP() AS last_updated

FROM `analytics.marketing_performance_partitioned`
WHERE
  report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND campaign_id IS NOT NULL
GROUP BY
  campaign_id,
  campaign_name,
  traffic_source
HAVING SUM(cost_usd) > 0;  -- Only campaigns with spend

-- ============================================================================
-- VIEWS: Current Month Performance
-- ============================================================================

/*
 * Regular view for current month performance
 * (not materialized - always fresh data)
 */

CREATE OR REPLACE VIEW `analytics.current_month_performance`
OPTIONS(
  description="Current month marketing performance"
) AS
SELECT
  report_date,
  campaign_name,
  traffic_source,
  traffic_medium,
  device_category,

  -- Metrics
  SUM(sessions) AS sessions,
  SUM(revenue_usd) AS revenue_usd,
  SUM(cost_usd) AS cost_usd,
  SUM(purchases) AS purchases,

  -- Efficiency
  SAFE_DIVIDE(SUM(revenue_usd), SUM(cost_usd)) AS roas,
  SAFE_DIVIDE(SUM(purchases), SUM(sessions)) AS conversion_rate

FROM `analytics.marketing_performance_partitioned`
WHERE
  report_date >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY
  report_date,
  campaign_name,
  traffic_source,
  traffic_medium,
  device_category;

-- ============================================================================
-- COST OPTIMIZATION: Table Clustering
-- ============================================================================

/*
 * Note on clustering:
 * - BigQuery automatically maintains clustering
 * - Clustering columns should be frequently filtered/grouped
 * - Order matters: most selective columns first
 * - Maximum 4 clustering columns
 *
 * Common clustering patterns:
 * - Time-series: date, user_id
 * - Marketing: campaign_id, traffic_source, device_category
 * - User analysis: user_id, session_id
 */

-- ============================================================================
-- COST OPTIMIZATION: Partition Expiration
-- ============================================================================

/*
 * Set partition expiration on existing tables
 */

-- Set 90-day expiration on raw events
ALTER TABLE `analytics.ga4_events_raw`
SET OPTIONS (
  partition_expiration_days=90
);

-- Set 1-year expiration on sessions
ALTER TABLE `analytics.ga4_sessions_partitioned`
SET OPTIONS (
  partition_expiration_days=365
);

-- Set 2-year expiration on marketing performance
ALTER TABLE `analytics.marketing_performance_partitioned`
SET OPTIONS (
  partition_expiration_days=730
);

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

/*
-- Check table sizes and costs
SELECT
  table_schema,
  table_name,
  ROUND(size_bytes / POW(10, 9), 2) AS size_gb,
  ROUND(size_bytes / POW(10, 9) * 0.02, 2) AS monthly_storage_cost_usd,
  row_count,
  creation_time,
  TIMESTAMP_MILLIS(last_modified_time) AS last_modified
FROM `analytics.INFORMATION_SCHEMA.TABLE_STORAGE`
WHERE table_schema = 'analytics'
ORDER BY size_bytes DESC;

-- Check partition information
SELECT
  table_name,
  partition_id,
  total_rows,
  ROUND(total_logical_bytes / POW(10, 9), 2) AS size_gb,
  last_modified_time
FROM `analytics.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_schema = 'analytics'
  AND partition_id IS NOT NULL
ORDER BY table_name, partition_id DESC
LIMIT 100;

-- Check materialized view freshness
SELECT
  table_schema,
  table_name,
  TIMESTAMP_MILLIS(last_refresh_time) AS last_refresh,
  refresh_interval_minutes,
  enable_refresh,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), TIMESTAMP_MILLIS(last_refresh_time), MINUTE) AS minutes_since_refresh
FROM `analytics.INFORMATION_SCHEMA.MATERIALIZED_VIEWS`
WHERE table_schema = 'analytics'
ORDER BY last_refresh_time DESC;

-- Estimate query costs
-- Run this before expensive queries to estimate costs
SELECT
  COUNT(*) AS row_count,
  ROUND(SUM(
    CASE
      WHEN _PARTITIONTIME >= TIMESTAMP('2024-01-01')
        AND _PARTITIONTIME < TIMESTAMP('2024-02-01')
      THEN 1
      ELSE 0
    END
  )) AS rows_in_partition
FROM `analytics.ga4_events_raw`;
*/

-- ============================================================================
-- BEST PRACTICES SUMMARY
-- ============================================================================

/*
Cost Optimization Best Practices:

1. PARTITIONING
   ✓ Partition by date for time-series data
   ✓ Set partition expiration based on retention needs
   ✓ Use require_partition_filter=true for large tables
   ✓ Always include partition filter in queries

2. CLUSTERING
   ✓ Cluster by frequently filtered columns
   ✓ Order clustering columns by cardinality (high to low)
   ✓ Maximum 4 clustering columns
   ✓ Combine with partitioning for best results

3. MATERIALIZED VIEWS
   ✓ Use for frequently accessed aggregations
   ✓ Set appropriate refresh intervals
   ✓ Monitor refresh costs vs. query cost savings
   ✓ Consider regular views for infrequently accessed data

4. TABLE DESIGN
   ✓ Use appropriate data types (INT64 vs. STRING)
   ✓ Avoid SELECT * - specify needed columns
   ✓ Use STRUCT for related fields
   ✓ Use ARRAY for repeated data

5. QUERY OPTIMIZATION
   ✓ Filter early in the query
   ✓ Use approximate aggregation functions (APPROX_COUNT_DISTINCT)
   ✓ Limit result set size
   ✓ Use cached results when possible

6. MONITORING
   ✓ Set up billing alerts
   ✓ Monitor query costs in INFORMATION_SCHEMA.JOBS
   ✓ Track table growth over time
   ✓ Review and optimize expensive queries
*/
