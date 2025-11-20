"""
Feature Engineering Pipeline for AI/ML Feature Store

This DAG orchestrates the feature engineering pipeline that:
1. Joins multiple source tables from Snowflake
2. Computes temporal aggregations (7d, 30d, 90d windows)
3. Generates text embeddings for support tickets
4. Writes features to Feast offline store (Snowflake)
5. Materializes features to online store (Redis)
6. Validates data quality

Architecture:
- Source: Snowflake (customer, billing, usage, support tables)
- Feature Store: Feast (offline: Snowflake, online: Redis)
- Embeddings: Snowflake Cortex AI or OpenAI
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.utils.dates import days_ago
import pandas as pd
import numpy as np
from great_expectations_provider.operators.great_expectations import GreatExpectationsOperator


# Configuration
SNOWFLAKE_CONN_ID = 'snowflake_default'
FEAST_REPO_PATH = '/opt/airflow/dags/feature_store/feast_repo'
REDIS_CONN_ID = 'redis_default'

# DAG configuration
default_args = {
    'owner': 'ml-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'email': ['ml-engineering@example.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def extract_customer_features(**context) -> Dict[str, Any]:
    """
    Extract customer demographic and account features from Snowflake.
    """
    logger = logging.getLogger(__name__)
    logger.info("Extracting customer features from Snowflake")

    hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)

    # Query customer base features
    query = """
    SELECT
        customer_id,
        account_created_date,
        customer_tier,
        industry,
        company_size,
        country,
        region,
        account_status,
        CURRENT_TIMESTAMP() as event_timestamp
    FROM analytics.customers
    WHERE account_status = 'active'
    """

    df = hook.get_pandas_df(query)
    logger.info(f"Extracted {len(df)} customer records")

    # Save to XCom for validation
    context['task_instance'].xcom_push(key='customer_count', value=len(df))

    # Write to staging table for feature computation
    hook.run(f"""
        CREATE OR REPLACE TABLE analytics.feature_staging_customers AS
        {query}
    """)

    return {'status': 'success', 'records': len(df)}


def compute_billing_features(**context) -> Dict[str, Any]:
    """
    Compute billing-related features with temporal aggregations.
    Features: spend (7d, 30d, 90d), invoice count, payment patterns
    """
    logger = logging.getLogger(__name__)
    logger.info("Computing billing features")

    hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)

    # Temporal aggregation query
    query = """
    CREATE OR REPLACE TABLE analytics.feature_billing AS
    SELECT
        customer_id,

        -- 7-day features
        SUM(CASE WHEN invoice_date >= DATEADD(day, -7, CURRENT_DATE()) THEN amount ELSE 0 END) as spend_7d,
        COUNT(DISTINCT CASE WHEN invoice_date >= DATEADD(day, -7, CURRENT_DATE()) THEN invoice_id END) as invoice_count_7d,

        -- 30-day features
        SUM(CASE WHEN invoice_date >= DATEADD(day, -30, CURRENT_DATE()) THEN amount ELSE 0 END) as spend_30d,
        COUNT(DISTINCT CASE WHEN invoice_date >= DATEADD(day, -30, CURRENT_DATE()) THEN invoice_id END) as invoice_count_30d,
        AVG(CASE WHEN invoice_date >= DATEADD(day, -30, CURRENT_DATE()) THEN amount END) as avg_invoice_amount_30d,

        -- 90-day features
        SUM(CASE WHEN invoice_date >= DATEADD(day, -90, CURRENT_DATE()) THEN amount ELSE 0 END) as spend_90d,
        COUNT(DISTINCT CASE WHEN invoice_date >= DATEADD(day, -90, CURRENT_DATE()) THEN invoice_id END) as invoice_count_90d,
        MAX(CASE WHEN invoice_date >= DATEADD(day, -90, CURRENT_DATE()) THEN amount END) as max_invoice_amount_90d,

        -- Payment behavior
        AVG(CASE WHEN invoice_date >= DATEADD(day, -90, CURRENT_DATE())
                 THEN DATEDIFF(day, invoice_date, payment_date) END) as avg_payment_delay_days_90d,
        SUM(CASE WHEN invoice_date >= DATEADD(day, -90, CURRENT_DATE()) AND payment_status = 'late'
                 THEN 1 ELSE 0 END) as late_payment_count_90d,

        -- Trend features
        (SUM(CASE WHEN invoice_date >= DATEADD(day, -30, CURRENT_DATE()) THEN amount ELSE 0 END) /
         NULLIF(SUM(CASE WHEN invoice_date >= DATEADD(day, -60, CURRENT_DATE())
                          AND invoice_date < DATEADD(day, -30, CURRENT_DATE()) THEN amount ELSE 0 END), 0)) as spend_trend_30d,

        CURRENT_TIMESTAMP() as event_timestamp

    FROM analytics.billing_transactions
    WHERE invoice_date >= DATEADD(day, -90, CURRENT_DATE())
    GROUP BY customer_id
    """

    hook.run(query)

    # Get count for validation
    count_query = "SELECT COUNT(*) FROM analytics.feature_billing"
    count = hook.get_first(count_query)[0]

    logger.info(f"Computed billing features for {count} customers")

    return {'status': 'success', 'records': count}


def compute_usage_features(**context) -> Dict[str, Any]:
    """
    Compute product usage features.
    Features: session count, feature usage, user activity
    """
    logger = logging.getLogger(__name__)
    logger.info("Computing usage features")

    hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)

    query = """
    CREATE OR REPLACE TABLE analytics.feature_usage AS
    SELECT
        customer_id,

        -- Session features (7d, 30d, 90d)
        COUNT(DISTINCT CASE WHEN session_date >= DATEADD(day, -7, CURRENT_DATE()) THEN session_id END) as session_count_7d,
        COUNT(DISTINCT CASE WHEN session_date >= DATEADD(day, -30, CURRENT_DATE()) THEN session_id END) as session_count_30d,
        COUNT(DISTINCT CASE WHEN session_date >= DATEADD(day, -90, CURRENT_DATE()) THEN session_id END) as session_count_90d,

        -- Active days
        COUNT(DISTINCT CASE WHEN session_date >= DATEADD(day, -7, CURRENT_DATE()) THEN session_date END) as active_days_7d,
        COUNT(DISTINCT CASE WHEN session_date >= DATEADD(day, -30, CURRENT_DATE()) THEN session_date END) as active_days_30d,

        -- Session duration
        AVG(CASE WHEN session_date >= DATEADD(day, -30, CURRENT_DATE())
                 THEN session_duration_minutes END) as avg_session_duration_30d,
        MAX(CASE WHEN session_date >= DATEADD(day, -30, CURRENT_DATE())
                 THEN session_duration_minutes END) as max_session_duration_30d,

        -- Feature usage depth
        COUNT(DISTINCT CASE WHEN session_date >= DATEADD(day, -30, CURRENT_DATE())
                            THEN feature_used END) as unique_features_used_30d,
        SUM(CASE WHEN session_date >= DATEADD(day, -30, CURRENT_DATE())
                 THEN actions_per_session ELSE 0 END) as total_actions_30d,

        -- Engagement trends
        AVG(CASE WHEN session_date >= DATEADD(day, -7, CURRENT_DATE())
                 THEN engagement_score END) as avg_engagement_score_7d,

        CURRENT_TIMESTAMP() as event_timestamp

    FROM analytics.usage_sessions
    WHERE session_date >= DATEADD(day, -90, CURRENT_DATE())
    GROUP BY customer_id
    """

    hook.run(query)

    count_query = "SELECT COUNT(*) FROM analytics.feature_usage"
    count = hook.get_first(count_query)[0]

    logger.info(f"Computed usage features for {count} customers")

    return {'status': 'success', 'records': count}


def compute_support_features(**context) -> Dict[str, Any]:
    """
    Compute customer support interaction features.
    Features: ticket count, resolution time, satisfaction scores
    """
    logger = logging.getLogger(__name__)
    logger.info("Computing support features")

    hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)

    query = """
    CREATE OR REPLACE TABLE analytics.feature_support AS
    SELECT
        customer_id,

        -- Ticket volume
        COUNT(CASE WHEN created_date >= DATEADD(day, -7, CURRENT_DATE()) THEN ticket_id END) as ticket_count_7d,
        COUNT(CASE WHEN created_date >= DATEADD(day, -30, CURRENT_DATE()) THEN ticket_id END) as ticket_count_30d,
        COUNT(CASE WHEN created_date >= DATEADD(day, -90, CURRENT_DATE()) THEN ticket_id END) as ticket_count_90d,

        -- Ticket severity
        SUM(CASE WHEN created_date >= DATEADD(day, -30, CURRENT_DATE()) AND priority = 'critical'
                 THEN 1 ELSE 0 END) as critical_ticket_count_30d,
        SUM(CASE WHEN created_date >= DATEADD(day, -30, CURRENT_DATE()) AND priority = 'high'
                 THEN 1 ELSE 0 END) as high_priority_ticket_count_30d,

        -- Resolution metrics
        AVG(CASE WHEN created_date >= DATEADD(day, -90, CURRENT_DATE()) AND resolution_date IS NOT NULL
                 THEN DATEDIFF(hour, created_date, resolution_date) END) as avg_resolution_time_hours_90d,
        MAX(CASE WHEN created_date >= DATEADD(day, -90, CURRENT_DATE()) AND resolution_date IS NOT NULL
                 THEN DATEDIFF(hour, created_date, resolution_date) END) as max_resolution_time_hours_90d,

        -- Open tickets
        COUNT(CASE WHEN status IN ('open', 'in_progress') THEN ticket_id END) as open_ticket_count,

        -- Satisfaction
        AVG(CASE WHEN created_date >= DATEADD(day, -90, CURRENT_DATE()) AND satisfaction_score IS NOT NULL
                 THEN satisfaction_score END) as avg_satisfaction_score_90d,

        -- Escalation rate
        SUM(CASE WHEN created_date >= DATEADD(day, -90, CURRENT_DATE()) AND is_escalated = TRUE
                 THEN 1 ELSE 0 END)::FLOAT /
        NULLIF(COUNT(CASE WHEN created_date >= DATEADD(day, -90, CURRENT_DATE()) THEN ticket_id END), 0) as escalation_rate_90d,

        CURRENT_TIMESTAMP() as event_timestamp

    FROM analytics.support_tickets
    WHERE created_date >= DATEADD(day, -90, CURRENT_DATE())
    GROUP BY customer_id
    """

    hook.run(query)

    count_query = "SELECT COUNT(*) FROM analytics.feature_support"
    count = hook.get_first(count_query)[0]

    logger.info(f"Computed support features for {count} customers")

    return {'status': 'success', 'records': count}


def generate_embeddings(**context) -> Dict[str, Any]:
    """
    Generate text embeddings for support ticket descriptions.
    Calls external embeddings generator script.
    """
    logger = logging.getLogger(__name__)
    logger.info("Generating text embeddings for support tickets")

    import subprocess
    import sys

    # Call embeddings generator script
    result = subprocess.run(
        [sys.executable, f"{FEAST_REPO_PATH}/../embeddings_generator.py"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"Embedding generation failed: {result.stderr}")
        raise Exception(f"Embedding generation failed: {result.stderr}")

    logger.info(f"Embedding generation output: {result.stdout}")

    return {'status': 'success'}


def join_and_write_to_feast(**context) -> Dict[str, Any]:
    """
    Join all feature tables and write to Feast offline store.
    """
    logger = logging.getLogger(__name__)
    logger.info("Joining features and writing to Feast offline store")

    hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)

    # Create complete feature table
    query = """
    CREATE OR REPLACE TABLE analytics.feast_features AS
    SELECT
        c.customer_id,
        c.event_timestamp,

        -- Customer features
        c.customer_tier,
        c.industry,
        c.company_size,
        c.country,
        c.region,
        DATEDIFF(day, c.account_created_date, CURRENT_DATE()) as account_age_days,

        -- Billing features
        COALESCE(b.spend_7d, 0) as spend_7d,
        COALESCE(b.spend_30d, 0) as spend_30d,
        COALESCE(b.spend_90d, 0) as spend_90d,
        COALESCE(b.invoice_count_7d, 0) as invoice_count_7d,
        COALESCE(b.invoice_count_30d, 0) as invoice_count_30d,
        COALESCE(b.invoice_count_90d, 0) as invoice_count_90d,
        COALESCE(b.avg_invoice_amount_30d, 0) as avg_invoice_amount_30d,
        COALESCE(b.avg_payment_delay_days_90d, 0) as avg_payment_delay_days_90d,
        COALESCE(b.late_payment_count_90d, 0) as late_payment_count_90d,
        COALESCE(b.spend_trend_30d, 1.0) as spend_trend_30d,

        -- Usage features
        COALESCE(u.session_count_7d, 0) as session_count_7d,
        COALESCE(u.session_count_30d, 0) as session_count_30d,
        COALESCE(u.session_count_90d, 0) as session_count_90d,
        COALESCE(u.active_days_7d, 0) as active_days_7d,
        COALESCE(u.active_days_30d, 0) as active_days_30d,
        COALESCE(u.avg_session_duration_30d, 0) as avg_session_duration_30d,
        COALESCE(u.unique_features_used_30d, 0) as unique_features_used_30d,
        COALESCE(u.total_actions_30d, 0) as total_actions_30d,
        COALESCE(u.avg_engagement_score_7d, 0) as avg_engagement_score_7d,

        -- Support features
        COALESCE(s.ticket_count_7d, 0) as ticket_count_7d,
        COALESCE(s.ticket_count_30d, 0) as ticket_count_30d,
        COALESCE(s.ticket_count_90d, 0) as ticket_count_90d,
        COALESCE(s.critical_ticket_count_30d, 0) as critical_ticket_count_30d,
        COALESCE(s.high_priority_ticket_count_30d, 0) as high_priority_ticket_count_30d,
        COALESCE(s.avg_resolution_time_hours_90d, 0) as avg_resolution_time_hours_90d,
        COALESCE(s.open_ticket_count, 0) as open_ticket_count,
        COALESCE(s.avg_satisfaction_score_90d, 0) as avg_satisfaction_score_90d,
        COALESCE(s.escalation_rate_90d, 0) as escalation_rate_90d

    FROM analytics.feature_staging_customers c
    LEFT JOIN analytics.feature_billing b ON c.customer_id = b.customer_id
    LEFT JOIN analytics.feature_usage u ON c.customer_id = u.customer_id
    LEFT JOIN analytics.feature_support s ON c.customer_id = s.customer_id
    """

    hook.run(query)

    # Get count
    count_query = "SELECT COUNT(*) FROM analytics.feast_features"
    count = hook.get_first(count_query)[0]

    logger.info(f"Created joined feature table with {count} records")

    return {'status': 'success', 'records': count}


def materialize_to_online_store(**context) -> Dict[str, Any]:
    """
    Materialize features from offline store (Snowflake) to online store (Redis).
    Uses Feast CLI.
    """
    logger = logging.getLogger(__name__)
    logger.info("Materializing features to online store (Redis)")

    import subprocess
    import os

    # Change to Feast repo directory
    os.chdir(FEAST_REPO_PATH)

    # Run feast materialize command
    result = subprocess.run(
        [
            'feast', 'materialize-incremental',
            datetime.now().isoformat()
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"Feast materialization failed: {result.stderr}")
        raise Exception(f"Feast materialization failed: {result.stderr}")

    logger.info(f"Feast materialization output: {result.stdout}")

    return {'status': 'success'}


def validate_features(**context) -> Dict[str, Any]:
    """
    Validate feature quality using Great Expectations.
    """
    logger = logging.getLogger(__name__)
    logger.info("Validating feature quality")

    hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)

    # Get features for validation
    query = "SELECT * FROM analytics.feast_features LIMIT 10000"
    df = hook.get_pandas_df(query)

    # Basic validations
    validations = {
        'null_check': df.isnull().sum().to_dict(),
        'negative_spend': (df['spend_30d'] < 0).sum(),
        'invalid_ratios': ((df['escalation_rate_90d'] < 0) | (df['escalation_rate_90d'] > 1)).sum(),
        'record_count': len(df)
    }

    logger.info(f"Feature validation results: {validations}")

    # Raise error if critical validations fail
    if validations['negative_spend'] > 0:
        raise ValueError(f"Found {validations['negative_spend']} records with negative spend")

    return {'status': 'success', 'validations': validations}


# DAG definition
with DAG(
    dag_id='feature_engineering_pipeline',
    default_args=default_args,
    description='Feature engineering pipeline for ML feature store',
    schedule_interval='0 3 * * *',  # Daily at 3 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['ml', 'feature-store', 'feast', 'production'],
    max_active_runs=1,
) as dag:

    extract_customers = PythonOperator(
        task_id='extract_customer_features',
        python_callable=extract_customer_features,
        provide_context=True,
    )

    compute_billing = PythonOperator(
        task_id='compute_billing_features',
        python_callable=compute_billing_features,
        provide_context=True,
    )

    compute_usage = PythonOperator(
        task_id='compute_usage_features',
        python_callable=compute_usage_features,
        provide_context=True,
    )

    compute_support = PythonOperator(
        task_id='compute_support_features',
        python_callable=compute_support_features,
        provide_context=True,
    )

    generate_emb = PythonOperator(
        task_id='generate_embeddings',
        python_callable=generate_embeddings,
        provide_context=True,
    )

    join_features = PythonOperator(
        task_id='join_and_write_to_feast',
        python_callable=join_and_write_to_feast,
        provide_context=True,
    )

    materialize = PythonOperator(
        task_id='materialize_to_online_store',
        python_callable=materialize_to_online_store,
        provide_context=True,
    )

    validate = PythonOperator(
        task_id='validate_features',
        python_callable=validate_features,
        provide_context=True,
    )

    # Pipeline dependencies
    extract_customers >> [compute_billing, compute_usage, compute_support]
    compute_support >> generate_emb
    [compute_billing, compute_usage, generate_emb] >> join_features
    join_features >> validate >> materialize
