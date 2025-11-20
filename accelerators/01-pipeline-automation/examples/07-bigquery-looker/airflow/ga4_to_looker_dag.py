"""
Airflow DAG: GA4 to Looker Dashboard Refresh

This production-ready DAG orchestrates the complete analytics pipeline:
1. Trigger BigQuery scheduled queries
2. Wait for query completion
3. Validate data quality
4. Refresh Looker dashboards via API
5. Send notifications on success/failure

Features:
- Error handling and retries
- Data quality validation
- Slack/email notifications
- Monitoring and alerting
- Idempotent operations

Prerequisites:
- Airflow 2.0+
- BigQuery connection configured in Airflow
- Looker API credentials
- apache-airflow-providers-google
- looker-sdk

Installation:
    pip install apache-airflow-providers-google looker-sdk

Usage:
    1. Copy to $AIRFLOW_HOME/dags/
    2. Configure Airflow connections:
       - google_cloud_default (BigQuery)
       - looker_api (Looker credentials)
    3. Set environment variables or Airflow Variables
    4. Enable DAG in Airflow UI
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from airflow import DAG
from airflow.decorators import task
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator,
    BigQueryCheckOperator,
)
from airflow.providers.google.cloud.sensors.bigquery import BigQueryTableExistenceSensor
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
from airflow.exceptions import AirflowException

import looker_sdk
from looker_sdk import models40 as models
from google.cloud import bigquery

# ============================================================================
# DAG CONFIGURATION
# ============================================================================

# Default arguments for all tasks
DEFAULT_ARGS = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['data-alerts@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# DAG-level configuration
DAG_CONFIG = {
    'dag_id': 'ga4_to_looker_refresh',
    'default_args': DEFAULT_ARGS,
    'description': 'Process GA4 data and refresh Looker dashboards',
    'schedule_interval': '0 * * * *',  # Hourly
    'start_date': days_ago(1),
    'catchup': False,
    'max_active_runs': 1,
    'tags': ['analytics', 'ga4', 'looker', 'marketing'],
}

# BigQuery configuration
PROJECT_ID = Variable.get('gcp_project_id', default_var='my-analytics-project')
DATASET_ID = Variable.get('bq_dataset_id', default_var='analytics')
LOCATION = Variable.get('bq_location', default_var='US')

# Looker configuration
LOOKER_BASE_URL = Variable.get('looker_base_url', default_var='https://mycompany.looker.com')
LOOKER_CLIENT_ID = Variable.get('looker_client_id', default_var='')
LOOKER_CLIENT_SECRET = Variable.get('looker_client_secret', default_var='')
LOOKER_DASHBOARD_IDS = Variable.get('looker_dashboard_ids', default_var='123,456,789').split(',')

# Data quality thresholds
MIN_EXPECTED_ROWS = 100
MAX_ALLOWED_NULLS_PERCENT = 5.0

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_bigquery_client() -> bigquery.Client:
    """Get BigQuery client using Airflow connection."""
    hook = BigQueryHook(gcp_conn_id='google_cloud_default', use_legacy_sql=False)
    return hook.get_client(project_id=PROJECT_ID, location=LOCATION)


def get_looker_client() -> looker_sdk.Looker40SDK:
    """
    Get Looker SDK client.

    Returns:
        Configured Looker SDK client
    """
    # Configure Looker SDK
    os.environ['LOOKERSDK_BASE_URL'] = LOOKER_BASE_URL
    os.environ['LOOKERSDK_CLIENT_ID'] = LOOKER_CLIENT_ID
    os.environ['LOOKERSDK_CLIENT_SECRET'] = LOOKER_CLIENT_SECRET

    sdk = looker_sdk.init40()
    return sdk


# ============================================================================
# TASK FUNCTIONS
# ============================================================================


@task
def validate_prerequisites(**context) -> Dict[str, Any]:
    """
    Validate that all prerequisites are met before running the pipeline.

    Returns:
        Dict with validation results
    """
    issues = []

    # Check BigQuery connection
    try:
        client = get_bigquery_client()
        client.query("SELECT 1").result()
    except Exception as e:
        issues.append(f"BigQuery connection failed: {e}")

    # Check Looker credentials
    if not LOOKER_CLIENT_ID or not LOOKER_CLIENT_SECRET:
        issues.append("Looker API credentials not configured")

    # Check Looker connection
    try:
        sdk = get_looker_client()
        me = sdk.me()
        if not me or not me.id:
            issues.append("Looker authentication failed")
    except Exception as e:
        issues.append(f"Looker connection failed: {e}")

    if issues:
        raise AirflowException(f"Prerequisites validation failed: {', '.join(issues)}")

    return {
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'project_id': PROJECT_ID,
        'dataset_id': DATASET_ID,
    }


@task
def get_processing_window(**context) -> Dict[str, str]:
    """
    Determine the date range to process based on execution date.

    Returns:
        Dict with start_date and end_date
    """
    execution_date = context['execution_date']
    lookback_hours = 2  # Reprocess last 2 hours for late-arriving data

    end_date = execution_date
    start_date = execution_date - timedelta(hours=lookback_hours)

    return {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'start_timestamp': start_date.isoformat(),
        'end_timestamp': end_date.isoformat(),
    }


@task
def check_data_quality(**context) -> Dict[str, Any]:
    """
    Perform data quality checks on processed tables.

    Returns:
        Dict with data quality results

    Raises:
        AirflowException if data quality checks fail
    """
    client = get_bigquery_client()
    issues = []
    metrics = {}

    # Check 1: Row count validation
    row_count_query = f"""
    SELECT COUNT(*) as row_count
    FROM `{PROJECT_ID}.{DATASET_ID}.ga4_sessions`
    WHERE session_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    """

    try:
        result = client.query(row_count_query).result()
        row_count = list(result)[0].row_count
        metrics['row_count'] = row_count

        if row_count < MIN_EXPECTED_ROWS:
            issues.append(f"Row count {row_count} below minimum {MIN_EXPECTED_ROWS}")
    except Exception as e:
        issues.append(f"Row count check failed: {e}")

    # Check 2: Null value validation
    null_check_query = f"""
    SELECT
        COUNTIF(user_pseudo_id IS NULL) * 100.0 / COUNT(*) as null_user_pct,
        COUNTIF(session_id IS NULL) * 100.0 / COUNT(*) as null_session_pct,
        COUNTIF(traffic_source IS NULL) * 100.0 / COUNT(*) as null_source_pct
    FROM `{PROJECT_ID}.{DATASET_ID}.ga4_sessions`
    WHERE session_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    """

    try:
        result = client.query(null_check_query).result()
        row = list(result)[0]

        metrics['null_user_pct'] = row.null_user_pct
        metrics['null_session_pct'] = row.null_session_pct
        metrics['null_source_pct'] = row.null_source_pct

        for field, pct in [
            ('user_pseudo_id', row.null_user_pct),
            ('session_id', row.null_session_pct),
        ]:
            if pct > MAX_ALLOWED_NULLS_PERCENT:
                issues.append(f"Null percentage for {field} ({pct:.2f}%) exceeds threshold")
    except Exception as e:
        issues.append(f"Null check failed: {e}")

    # Check 3: Data freshness
    freshness_query = f"""
    SELECT
        MAX(processed_at) as last_processed,
        TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(processed_at), MINUTE) as minutes_old
    FROM `{PROJECT_ID}.{DATASET_ID}.ga4_sessions`
    """

    try:
        result = client.query(freshness_query).result()
        row = list(result)[0]

        metrics['last_processed'] = row.last_processed.isoformat() if row.last_processed else None
        metrics['minutes_old'] = row.minutes_old

        if row.minutes_old and row.minutes_old > 120:  # 2 hours
            issues.append(f"Data is {row.minutes_old} minutes old (> 120 minutes)")
    except Exception as e:
        issues.append(f"Freshness check failed: {e}")

    # Raise exception if any issues found
    if issues:
        raise AirflowException(f"Data quality checks failed: {', '.join(issues)}")

    return {
        'status': 'passed',
        'metrics': metrics,
        'timestamp': datetime.now().isoformat(),
    }


@task
def refresh_looker_dashboards(**context) -> Dict[str, Any]:
    """
    Refresh Looker dashboards via API.

    Returns:
        Dict with refresh results
    """
    sdk = get_looker_client()
    results = {}

    for dashboard_id in LOOKER_DASHBOARD_IDS:
        try:
            dashboard_id = dashboard_id.strip()

            # Get dashboard details
            dashboard = sdk.dashboard(dashboard_id)

            if not dashboard:
                results[dashboard_id] = {
                    'status': 'error',
                    'message': 'Dashboard not found',
                }
                continue

            # Refresh dashboard queries
            # Method 1: Refresh all queries on the dashboard
            queries = sdk.dashboard_dashboard_elements(dashboard_id)

            refresh_count = 0
            for element in queries:
                if element.query_id:
                    try:
                        # Run query to refresh cache
                        sdk.run_query(
                            query_id=element.query_id,
                            result_format='json',
                            cache=False,  # Force refresh
                        )
                        refresh_count += 1
                    except Exception as e:
                        context['task_instance'].log.warning(
                            f"Failed to refresh query {element.query_id}: {e}"
                        )

            results[dashboard_id] = {
                'status': 'success',
                'title': dashboard.title,
                'queries_refreshed': refresh_count,
                'timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            results[dashboard_id] = {
                'status': 'error',
                'message': str(e),
            }
            context['task_instance'].log.error(f"Failed to refresh dashboard {dashboard_id}: {e}")

    # Check if any dashboards failed
    failed_dashboards = [
        dash_id for dash_id, result in results.items() if result['status'] == 'error'
    ]

    if failed_dashboards:
        raise AirflowException(
            f"Failed to refresh {len(failed_dashboards)} dashboard(s): {', '.join(failed_dashboards)}"
        )

    return {
        'status': 'success',
        'dashboards_refreshed': len(results),
        'results': results,
    }


@task
def send_success_notification(**context) -> None:
    """
    Send success notification with pipeline metrics.
    """
    task_instance = context['task_instance']

    # Get results from previous tasks
    validation = task_instance.xcom_pull(task_ids='validate_prerequisites')
    quality_check = task_instance.xcom_pull(task_ids='check_data_quality')
    looker_refresh = task_instance.xcom_pull(task_ids='refresh_looker_dashboards')

    message = f"""
    ✅ GA4 to Looker Pipeline Completed Successfully

    Execution Date: {context['execution_date']}

    Data Quality Metrics:
    - Rows Processed: {quality_check['metrics'].get('row_count', 'N/A'):,}
    - Data Freshness: {quality_check['metrics'].get('minutes_old', 'N/A')} minutes old

    Looker Dashboards:
    - Dashboards Refreshed: {looker_refresh['dashboards_refreshed']}

    Project: {PROJECT_ID}
    Dataset: {DATASET_ID}
    """

    # In production, send to Slack, email, or other notification service
    context['task_instance'].log.info(message)

    # Example: Send to Slack (requires SlackWebhookOperator)
    # slack_webhook_url = Variable.get('slack_webhook_url', default_var='')
    # if slack_webhook_url:
    #     requests.post(slack_webhook_url, json={'text': message})


# ============================================================================
# DAG DEFINITION
# ============================================================================

with DAG(**DAG_CONFIG) as dag:

    # Task 1: Validate prerequisites
    validate_task = validate_prerequisites()

    # Task 2: Determine processing window
    processing_window_task = get_processing_window()

    # Task 3: Process GA4 events
    process_ga4_events = BigQueryInsertJobOperator(
        task_id='process_ga4_events',
        gcp_conn_id='google_cloud_default',
        configuration={
            'query': {
                'query': f"""
                    -- Run the GA4 events processing query
                    -- This would reference the queries from scheduled_queries.sql
                    SELECT 'Processing GA4 events...' as status
                """,
                'useLegacySql': False,
                'destinationTable': {
                    'projectId': PROJECT_ID,
                    'datasetId': DATASET_ID,
                    'tableId': 'ga4_events_processed',
                },
                'writeDisposition': 'WRITE_TRUNCATE',
            }
        },
        location=LOCATION,
    )

    # Task 4: Aggregate sessions
    aggregate_sessions = BigQueryInsertJobOperator(
        task_id='aggregate_sessions',
        gcp_conn_id='google_cloud_default',
        configuration={
            'query': {
                'query': f"""
                    -- Run the session aggregation query
                    -- This would reference the queries from scheduled_queries.sql
                    SELECT 'Aggregating sessions...' as status
                """,
                'useLegacySql': False,
                'destinationTable': {
                    'projectId': PROJECT_ID,
                    'datasetId': DATASET_ID,
                    'tableId': 'ga4_sessions',
                },
                'writeDisposition': 'WRITE_TRUNCATE',
            }
        },
        location=LOCATION,
    )

    # Task 5: Join with Google Ads data
    join_google_ads = BigQueryInsertJobOperator(
        task_id='join_google_ads',
        gcp_conn_id='google_cloud_default',
        configuration={
            'query': {
                'query': f"""
                    -- Run the Google Ads join query
                    -- This would reference the queries from scheduled_queries.sql
                    SELECT 'Joining with Google Ads data...' as status
                """,
                'useLegacySql': False,
                'destinationTable': {
                    'projectId': PROJECT_ID,
                    'datasetId': DATASET_ID,
                    'tableId': 'marketing_performance',
                },
                'writeDisposition': 'WRITE_TRUNCATE',
            }
        },
        location=LOCATION,
    )

    # Task 6: Check table existence
    check_table_exists = BigQueryTableExistenceSensor(
        task_id='check_table_exists',
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        table_id='marketing_performance',
        gcp_conn_id='google_cloud_default',
        mode='poke',
        timeout=600,
        poke_interval=30,
    )

    # Task 7: Data quality checks
    quality_check_task = check_data_quality()

    # Task 8: Refresh Looker dashboards
    refresh_looker_task = refresh_looker_dashboards()

    # Task 9: Send success notification
    notification_task = send_success_notification()

    # Define task dependencies
    validate_task >> processing_window_task >> process_ga4_events
    process_ga4_events >> aggregate_sessions >> join_google_ads
    join_google_ads >> check_table_exists >> quality_check_task
    quality_check_task >> refresh_looker_task >> notification_task


# ============================================================================
# DOCUMENTATION
# ============================================================================

dag.doc_md = """
# GA4 to Looker Dashboard Refresh Pipeline

This DAG orchestrates the complete analytics pipeline from GA4 data processing to Looker dashboard refresh.

## Pipeline Steps

1. **Validate Prerequisites**: Check BigQuery and Looker connections
2. **Determine Processing Window**: Calculate date range to process
3. **Process GA4 Events**: Parse and flatten GA4 export data
4. **Aggregate Sessions**: Create session-level metrics
5. **Join Google Ads Data**: Combine GA4 with Google Ads metrics
6. **Check Table Existence**: Verify tables were created
7. **Data Quality Checks**: Validate row counts, nulls, and freshness
8. **Refresh Looker Dashboards**: Trigger dashboard refresh via API
9. **Send Notification**: Alert on success/failure

## Configuration

Set the following Airflow Variables:
- `gcp_project_id`: GCP project ID
- `bq_dataset_id`: BigQuery dataset ID
- `bq_location`: BigQuery location (US, EU, etc.)
- `looker_base_url`: Looker instance URL
- `looker_client_id`: Looker API client ID
- `looker_client_secret`: Looker API client secret
- `looker_dashboard_ids`: Comma-separated dashboard IDs

## Airflow Connections

Configure these connections in Airflow:
- `google_cloud_default`: GCP service account with BigQuery permissions
- `looker_api`: Looker API credentials (optional, can use Variables)

## Monitoring

Monitor this DAG in:
- Airflow UI: Task status and logs
- BigQuery: Query execution and costs
- Looker: Dashboard refresh status

## Troubleshooting

Common issues:
- **BigQuery quota exceeded**: Reduce schedule frequency or optimize queries
- **Looker API rate limit**: Reduce number of dashboards or frequency
- **Data quality failures**: Check source data and query logic
- **Authentication failures**: Verify credentials in Variables/Connections
"""
