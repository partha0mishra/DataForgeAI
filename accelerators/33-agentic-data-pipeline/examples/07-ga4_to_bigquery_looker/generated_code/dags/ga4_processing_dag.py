from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCreateEmptyTableOperator,
    BigQueryInsertJobOperator
)
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'analytics',
    'depends_on_past': False,
    'email': ['analytics@company.com'],
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='ga4_to_bigquery_looker',
    default_args=default_args,
    schedule_interval='0 */4 * * *',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ga4', 'bigquery', 'analytics'],
) as dag:

    # Process user sessions
    process_sessions = BigQueryInsertJobOperator(
        task_id='process_user_sessions',
        configuration={
            'query': {
                'query': '''
                    CREATE OR REPLACE TABLE `your-gcp-project.analytics_reporting.user_sessions` AS
                    SELECT
                        user_pseudo_id,
                        PARSE_DATE('%Y%m%d', event_date) AS session_date,
                        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
                        MIN(TIMESTAMP_MICROS(event_timestamp)) AS session_start,
                        MAX(TIMESTAMP_MICROS(event_timestamp)) AS session_end,
                        TIMESTAMP_DIFF(
                            MAX(TIMESTAMP_MICROS(event_timestamp)),
                            MIN(TIMESTAMP_MICROS(event_timestamp)),
                            SECOND
                        ) AS session_duration_seconds,
                        COUNT(*) AS event_count,
                        COUNTIF(event_name = 'page_view') AS page_views,
                        COUNTIF(event_name = 'add_to_cart') AS add_to_carts,
                        COUNTIF(event_name = 'purchase') AS purchases,
                        MAX((SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location')) AS landing_page,
                        ANY_VALUE(device.category) AS device_category,
                        ANY_VALUE(geo.country) AS country,
                        ANY_VALUE(traffic_source.source) AS traffic_source
                    FROM `your-gcp-project.analytics_raw.events_*`
                    WHERE _TABLE_SUFFIX = FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
                    GROUP BY user_pseudo_id, session_date, session_id
                ''',
                'useLegacySql': False
            }
        }
    )

    # Process page views
    process_page_views = BigQueryInsertJobOperator(
        task_id='process_page_views',
        configuration={
            'query': {
                'query': '''
                    CREATE OR REPLACE TABLE `your-gcp-project.analytics_reporting.page_views` AS
                    SELECT
                        PARSE_DATE('%Y%m%d', event_date) AS page_view_date,
                        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page_url,
                        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title') AS page_title,
                        COUNT(DISTINCT user_pseudo_id) AS unique_users,
                        COUNT(*) AS total_page_views,
                        AVG(engagement_time_msec / 1000) AS avg_engagement_seconds
                    FROM `your-gcp-project.analytics_raw.events_*`
                    WHERE _TABLE_SUFFIX = FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
                        AND event_name = 'page_view'
                    GROUP BY page_view_date, page_url, page_title
                ''',
                'useLegacySql': False
            }
        }
    )

    # Process conversion funnel
    process_funnel = BigQueryInsertJobOperator(
        task_id='process_conversion_funnel',
        configuration={
            'query': {
                'query': '''
                    CREATE OR REPLACE TABLE `your-gcp-project.analytics_reporting.conversion_funnel` AS
                    WITH user_events AS (
                        SELECT
                            user_pseudo_id,
                            PARSE_DATE('%Y%m%d', event_date) AS event_date,
                            MAX(CASE WHEN event_name = 'page_view' THEN 1 ELSE 0 END) AS viewed,
                            MAX(CASE WHEN event_name = 'add_to_cart' THEN 1 ELSE 0 END) AS added_to_cart,
                            MAX(CASE WHEN event_name = 'begin_checkout' THEN 1 ELSE 0 END) AS began_checkout,
                            MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS purchased
                        FROM `your-gcp-project.analytics_raw.events_*`
                        WHERE _TABLE_SUFFIX = FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
                        GROUP BY user_pseudo_id, event_date
                    )
                    SELECT
                        event_date,
                        SUM(viewed) AS users_viewed,
                        SUM(added_to_cart) AS users_added_to_cart,
                        SUM(began_checkout) AS users_began_checkout,
                        SUM(purchased) AS users_purchased,
                        SAFE_DIVIDE(SUM(added_to_cart), SUM(viewed)) AS cart_rate,
                        SAFE_DIVIDE(SUM(began_checkout), SUM(added_to_cart)) AS checkout_rate,
                        SAFE_DIVIDE(SUM(purchased), SUM(began_checkout)) AS purchase_rate
                    FROM user_events
                    GROUP BY event_date
                ''',
                'useLegacySql': False
            }
        }
    )

    # Process traffic sources
    process_traffic = BigQueryInsertJobOperator(
        task_id='process_traffic_sources',
        configuration={
            'query': {
                'query': '''
                    CREATE OR REPLACE TABLE `your-gcp-project.analytics_reporting.traffic_sources` AS
                    SELECT
                        PARSE_DATE('%Y%m%d', event_date) AS traffic_date,
                        traffic_source.source,
                        traffic_source.medium,
                        traffic_source.name AS campaign,
                        COUNT(DISTINCT user_pseudo_id) AS unique_users,
                        COUNT(DISTINCT(SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id')) AS sessions,
                        COUNTIF(event_name = 'purchase') AS conversions,
                        SUM(ecommerce.purchase_revenue) AS revenue
                    FROM `your-gcp-project.analytics_raw.events_*`
                    WHERE _TABLE_SUFFIX = FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
                    GROUP BY traffic_date, source, medium, campaign
                ''',
                'useLegacySql': False
            }
        }
    )

    # Define dependencies
    [process_sessions, process_page_views, process_funnel, process_traffic]
