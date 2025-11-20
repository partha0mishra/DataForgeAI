/*
 * BigQuery Scheduled Queries for GA4 and Google Ads Analytics
 *
 * This script demonstrates production-ready BigQuery scheduled queries that:
 * - Parse GA4 (Google Analytics 4) BigQuery export data
 * - Join with Google Ads data
 * - Create partitioned result tables
 * - Perform daily aggregations
 * - Calculate session metrics, conversions, and revenue
 *
 * GA4 Export Schema Reference:
 * https://support.google.com/analytics/answer/9358801
 *
 * Prerequisites:
 * - GA4 BigQuery export enabled
 * - Google Ads data in BigQuery
 * - Appropriate BigQuery permissions
 *
 * Usage:
 *   1. Update project_id and dataset names
 *   2. Create scheduled query in BigQuery console or via bq CLI
 *   3. Schedule: hourly, daily, or custom interval
 *
 * bq query --use_legacy_sql=false --destination_table=analytics.ga4_sessions \
 *   --schedule='every 1 hours' --display_name='GA4 Sessions Aggregation' \
 *   < scheduled_queries.sql
 */

-- ============================================================================
-- CONFIGURATION
-- ============================================================================

-- Set project and dataset (update these values)
DECLARE project_id STRING DEFAULT 'my-analytics-project';
DECLARE dataset_id STRING DEFAULT 'analytics';
DECLARE ga4_dataset STRING DEFAULT 'analytics_123456789'; -- Your GA4 property ID
DECLARE lookback_hours INT64 DEFAULT 2; -- Reprocess last 2 hours for late data

-- ============================================================================
-- QUERY 1: GA4 Events Processing
-- ============================================================================

/*
 * Parse GA4 events and extract key metrics
 * This query demonstrates proper handling of GA4's nested structure
 */

CREATE OR REPLACE TABLE `analytics.ga4_events_processed`
PARTITION BY event_date
CLUSTER BY user_pseudo_id, event_name
OPTIONS(
  description="Processed GA4 events with unnested parameters",
  partition_expiration_days=90
) AS

WITH ga4_events AS (
  SELECT
    -- Event identification
    event_date,
    event_timestamp,
    event_name,
    event_previous_timestamp,
    event_value_in_usd,
    event_bundle_sequence_id,
    event_server_timestamp_offset,

    -- User identification
    user_pseudo_id,
    user_id,

    -- Session information
    COALESCE(
      (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id'),
      0
    ) AS session_id,

    COALESCE(
      (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_number'),
      0
    ) AS session_number,

    COALESCE(
      (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'session_engaged'),
      '0'
    ) AS session_engaged,

    -- Page information
    COALESCE(
      (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location'),
      ''
    ) AS page_location,

    COALESCE(
      (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title'),
      ''
    ) AS page_title,

    COALESCE(
      (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_referrer'),
      ''
    ) AS page_referrer,

    -- Campaign parameters
    traffic_source.source AS traffic_source,
    traffic_source.medium AS traffic_medium,
    traffic_source.name AS campaign_name,

    COALESCE(
      (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'campaign_id'),
      ''
    ) AS campaign_id,

    -- Device information
    device.category AS device_category,
    device.mobile_brand_name AS device_brand,
    device.mobile_model_name AS device_model,
    device.operating_system AS device_os,
    device.browser AS device_browser,
    device.language AS device_language,

    -- Geographic information
    geo.continent AS geo_continent,
    geo.country AS geo_country,
    geo.region AS geo_region,
    geo.city AS geo_city,

    -- Ecommerce information (if applicable)
    ecommerce.transaction_id,
    ecommerce.purchase_revenue_in_usd,
    ecommerce.total_item_quantity,

    -- User properties
    (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'user_type') AS user_type,
    (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'user_ltv') AS user_ltv,

    -- Privacy info
    privacy_info.analytics_storage,
    privacy_info.ads_storage,

    -- App info (if applicable)
    app_info.id AS app_id,
    app_info.version AS app_version,

    -- Platform
    platform,
    stream_id,

    -- Timestamp
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp_utc,
    PARSE_DATE('%Y%m%d', event_date) AS event_date_parsed

  FROM
    `{project_id}.{ga4_dataset}.events_*`
  WHERE
    -- Process events from the last lookback period
    _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL lookback_hours HOUR))
    AND _TABLE_SUFFIX <= FORMAT_DATE('%Y%m%d', CURRENT_DATE())
)

SELECT * FROM ga4_events;

-- ============================================================================
-- QUERY 2: Session Aggregation
-- ============================================================================

/*
 * Aggregate GA4 events into sessions with key metrics
 */

CREATE OR REPLACE TABLE `analytics.ga4_sessions`
PARTITION BY session_date
CLUSTER BY user_pseudo_id, traffic_source, traffic_medium
OPTIONS(
  description="GA4 sessions with aggregated metrics",
  partition_expiration_days=365
) AS

WITH session_events AS (
  SELECT
    user_pseudo_id,
    session_id,
    event_date_parsed AS session_date,

    -- Session timing
    MIN(event_timestamp_utc) AS session_start,
    MAX(event_timestamp_utc) AS session_end,
    TIMESTAMP_DIFF(MAX(event_timestamp_utc), MIN(event_timestamp_utc), SECOND) AS session_duration_seconds,

    -- Event counts
    COUNT(*) AS total_events,
    COUNTIF(event_name = 'page_view') AS page_views,
    COUNTIF(event_name = 'user_engagement') AS engagement_events,
    COUNTIF(event_name = 'scroll') AS scroll_events,
    COUNTIF(event_name = 'click') AS click_events,

    -- Engagement
    MAX(CASE WHEN session_engaged = '1' THEN 1 ELSE 0 END) AS is_engaged_session,

    -- Landing page
    ARRAY_AGG(page_location ORDER BY event_timestamp_utc LIMIT 1)[OFFSET(0)] AS landing_page,
    ARRAY_AGG(page_title ORDER BY event_timestamp_utc LIMIT 1)[OFFSET(0)] AS landing_page_title,

    -- Exit page
    ARRAY_AGG(page_location ORDER BY event_timestamp_utc DESC LIMIT 1)[OFFSET(0)] AS exit_page,

    -- Attribution
    ANY_VALUE(traffic_source) AS traffic_source,
    ANY_VALUE(traffic_medium) AS traffic_medium,
    ANY_VALUE(campaign_name) AS campaign_name,
    ANY_VALUE(campaign_id) AS campaign_id,

    -- Device
    ANY_VALUE(device_category) AS device_category,
    ANY_VALUE(device_os) AS device_os,
    ANY_VALUE(device_browser) AS device_browser,

    -- Geography
    ANY_VALUE(geo_country) AS geo_country,
    ANY_VALUE(geo_region) AS geo_region,
    ANY_VALUE(geo_city) AS geo_city,

    -- Conversions
    COUNTIF(event_name = 'purchase') AS purchase_events,
    SUM(CASE WHEN event_name = 'purchase' THEN ecommerce.purchase_revenue_in_usd ELSE 0 END) AS revenue_usd,
    SUM(CASE WHEN event_name = 'purchase' THEN ecommerce.total_item_quantity ELSE 0 END) AS items_purchased,

    -- Other conversions (customize based on your events)
    COUNTIF(event_name = 'sign_up') AS sign_up_events,
    COUNTIF(event_name = 'add_to_cart') AS add_to_cart_events,
    COUNTIF(event_name = 'begin_checkout') AS begin_checkout_events,

    -- User info
    ANY_VALUE(user_id) AS user_id,
    ANY_VALUE(session_number) AS session_number,
    ANY_VALUE(user_type) AS user_type,

    -- Platform
    ANY_VALUE(platform) AS platform,
    ANY_VALUE(stream_id) AS stream_id

  FROM `analytics.ga4_events_processed`
  GROUP BY
    user_pseudo_id,
    session_id,
    session_date
)

SELECT
  *,
  -- Derived metrics
  CASE
    WHEN page_views >= 3 AND session_duration_seconds >= 30 THEN TRUE
    ELSE FALSE
  END AS is_quality_session,

  CASE
    WHEN revenue_usd > 0 THEN TRUE
    ELSE FALSE
  END AS is_conversion_session,

  ROUND(SAFE_DIVIDE(revenue_usd, page_views), 2) AS revenue_per_page_view,

  CURRENT_TIMESTAMP() AS processed_at

FROM session_events;

-- ============================================================================
-- QUERY 3: Google Ads Integration
-- ============================================================================

/*
 * Join GA4 sessions with Google Ads data
 * Note: Assumes Google Ads data is available in BigQuery
 */

CREATE OR REPLACE TABLE `analytics.marketing_performance`
PARTITION BY report_date
CLUSTER BY campaign_id, traffic_source
OPTIONS(
  description="Combined GA4 and Google Ads performance metrics",
  partition_expiration_days=365
) AS

WITH google_ads_daily AS (
  -- Example Google Ads data structure
  -- Adjust based on your actual Google Ads BigQuery schema
  SELECT
    DATE(day) AS report_date,
    campaign_id,
    campaign_name,
    ad_group_id,
    ad_group_name,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(cost_micros) / 1000000 AS cost_usd,
    SUM(conversions) AS ads_conversions,
    SUM(conversions_value) AS ads_conversion_value
  FROM `analytics.google_ads_raw`
  WHERE
    DATE(day) >= DATE_SUB(CURRENT_DATE(), INTERVAL lookback_hours HOUR)
  GROUP BY
    report_date,
    campaign_id,
    campaign_name,
    ad_group_id,
    ad_group_name
),

ga4_daily AS (
  SELECT
    session_date AS report_date,
    campaign_id,
    traffic_source,
    traffic_medium,
    device_category,

    -- Session metrics
    COUNT(DISTINCT user_pseudo_id) AS users,
    COUNT(*) AS sessions,
    SUM(is_engaged_session) AS engaged_sessions,
    SUM(page_views) AS page_views,
    SUM(session_duration_seconds) AS total_session_duration_seconds,

    -- Conversion metrics
    SUM(purchase_events) AS purchases,
    SUM(revenue_usd) AS revenue_usd,
    SUM(items_purchased) AS items_purchased,
    SUM(sign_up_events) AS sign_ups,
    SUM(add_to_cart_events) AS add_to_cart,
    SUM(begin_checkout_events) AS begin_checkout,

    -- Quality metrics
    SUM(is_quality_session) AS quality_sessions

  FROM `analytics.ga4_sessions`
  WHERE
    campaign_id IS NOT NULL
    AND campaign_id != ''
  GROUP BY
    report_date,
    campaign_id,
    traffic_source,
    traffic_medium,
    device_category
)

SELECT
  -- Date and campaign
  COALESCE(ads.report_date, ga4.report_date) AS report_date,
  COALESCE(ads.campaign_id, ga4.campaign_id) AS campaign_id,
  ads.campaign_name,
  ads.ad_group_id,
  ads.ad_group_name,

  -- Traffic source
  ga4.traffic_source,
  ga4.traffic_medium,
  ga4.device_category,

  -- Google Ads metrics
  COALESCE(ads.impressions, 0) AS impressions,
  COALESCE(ads.clicks, 0) AS clicks,
  COALESCE(ads.cost_usd, 0) AS cost_usd,
  COALESCE(ads.ads_conversions, 0) AS ads_conversions,
  COALESCE(ads.ads_conversion_value, 0) AS ads_conversion_value,

  -- GA4 metrics
  COALESCE(ga4.users, 0) AS users,
  COALESCE(ga4.sessions, 0) AS sessions,
  COALESCE(ga4.engaged_sessions, 0) AS engaged_sessions,
  COALESCE(ga4.page_views, 0) AS page_views,
  COALESCE(ga4.total_session_duration_seconds, 0) AS total_session_duration_seconds,
  COALESCE(ga4.purchases, 0) AS purchases,
  COALESCE(ga4.revenue_usd, 0) AS revenue_usd,
  COALESCE(ga4.items_purchased, 0) AS items_purchased,
  COALESCE(ga4.sign_ups, 0) AS sign_ups,
  COALESCE(ga4.quality_sessions, 0) AS quality_sessions,

  -- Calculated metrics
  SAFE_DIVIDE(ads.clicks, ads.impressions) AS ctr,
  SAFE_DIVIDE(ads.cost_usd, ads.clicks) AS cpc,
  SAFE_DIVIDE(ga4.engaged_sessions, ga4.sessions) AS engagement_rate,
  SAFE_DIVIDE(ga4.purchases, ga4.sessions) AS conversion_rate,
  SAFE_DIVIDE(ga4.revenue_usd, ga4.sessions) AS revenue_per_session,
  SAFE_DIVIDE(ga4.revenue_usd, ads.cost_usd) AS roas,
  SAFE_DIVIDE(ads.cost_usd, ga4.purchases) AS cpa,
  SAFE_DIVIDE(ga4.total_session_duration_seconds, ga4.sessions) AS avg_session_duration,

  CURRENT_TIMESTAMP() AS processed_at

FROM google_ads_daily ads
FULL OUTER JOIN ga4_daily ga4
  ON ads.report_date = ga4.report_date
  AND ads.campaign_id = ga4.campaign_id;

-- ============================================================================
-- QUERY 4: Daily Summary for Looker Dashboard
-- ============================================================================

/*
 * Create a summary table optimized for Looker dashboards
 */

CREATE OR REPLACE TABLE `analytics.marketing_daily_summary`
PARTITION BY report_date
CLUSTER BY traffic_source, device_category
OPTIONS(
  description="Daily marketing summary for Looker dashboards",
  partition_expiration_days=730  -- 2 years
) AS

SELECT
  report_date,

  -- Dimensions
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

  -- Weighted averages
  SAFE_DIVIDE(SUM(clicks), SUM(impressions)) AS avg_ctr,
  SAFE_DIVIDE(SUM(cost_usd), SUM(clicks)) AS avg_cpc,
  SAFE_DIVIDE(SUM(engaged_sessions), SUM(sessions)) AS avg_engagement_rate,
  SAFE_DIVIDE(SUM(purchases), SUM(sessions)) AS avg_conversion_rate,
  SAFE_DIVIDE(SUM(revenue_usd), SUM(sessions)) AS avg_revenue_per_session,
  SAFE_DIVIDE(SUM(revenue_usd), SUM(cost_usd)) AS avg_roas,
  SAFE_DIVIDE(SUM(cost_usd), SUM(purchases)) AS avg_cpa,

  -- Data quality
  COUNT(*) AS campaign_count,
  CURRENT_TIMESTAMP() AS last_updated

FROM `analytics.marketing_performance`
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY
  report_date,
  traffic_source,
  traffic_medium,
  device_category;

-- ============================================================================
-- HELPFUL MONITORING QUERIES
-- ============================================================================

/*
-- Check data freshness
SELECT
  table_name,
  TIMESTAMP_MILLIS(creation_time) AS created,
  TIMESTAMP_MILLIS(last_modified_time) AS last_modified,
  row_count,
  size_bytes / POW(10, 9) AS size_gb
FROM `analytics.__TABLES__`
WHERE table_id IN ('ga4_events_processed', 'ga4_sessions', 'marketing_performance')
ORDER BY last_modified DESC;

-- Check for data gaps
SELECT
  report_date,
  COUNT(*) AS record_count
FROM `analytics.marketing_daily_summary`
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY report_date
ORDER BY report_date DESC;

-- Top performing campaigns
SELECT
  campaign_name,
  SUM(total_revenue_usd) AS revenue,
  SUM(total_cost_usd) AS cost,
  SAFE_DIVIDE(SUM(total_revenue_usd), SUM(total_cost_usd)) AS roas,
  SUM(total_purchases) AS purchases
FROM `analytics.marketing_daily_summary`
WHERE report_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY campaign_name
ORDER BY revenue DESC
LIMIT 10;
*/
