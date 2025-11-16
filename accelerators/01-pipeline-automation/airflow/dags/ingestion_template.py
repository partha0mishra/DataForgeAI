"""Generic data ingestion DAG template."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from dataforge_common.logging import get_logger
from dataforge_connectors.databases import PostgreSQLConnector

logger = get_logger(__name__)

# Default DAG arguments
default_args = {
    "owner": "dataforge",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}


def extract_data(**context):
    """
    Extract data from source.

    This is a template - customize for your source.
    """
    logger.info("Starting data extraction")

    # Example: Extract from PostgreSQL
    connector = PostgreSQLConnector(
        host="{{ var.value.source_db_host }}",
        port=5432,
        database="{{ var.value.source_db_name }}",
        user="{{ var.value.source_db_user }}",
        password="{{ var.value.source_db_password }}"
    )

    with connector:
        # Extract data
        df = connector.read_table(
            table="{{ var.value.source_table }}",
            limit=None  # Full extraction
        )

        # Push data to XCom
        context["task_instance"].xcom_push(
            key="extracted_records",
            value=len(df)
        )

        # Save to staging (example: Parquet on S3)
        staging_path = f"/tmp/staging_{context['ds']}.parquet"
        df.to_parquet(staging_path)

        logger.info(f"Extracted {len(df)} records", records=len(df))

    return staging_path


def load_data(**context):
    """
    Load data to destination.

    This is a template - customize for your destination.
    """
    import pandas as pd

    logger.info("Starting data load")

    # Get staging path from previous task
    staging_path = context["task_instance"].xcom_pull(
        task_ids="extract_data"
    )

    # Load data
    df = pd.read_parquet(staging_path)

    # Example: Load to PostgreSQL
    connector = PostgreSQLConnector(
        host="{{ var.value.dest_db_host }}",
        port=5432,
        database="{{ var.value.dest_db_name }}",
        user="{{ var.value.dest_db_user }}",
        password="{{ var.value.dest_db_password }}"
    )

    with connector:
        rows_written = connector.write_dataframe(
            df=df,
            table="{{ var.value.dest_table }}",
            schema="staging",
            if_exists="replace"
        )

        logger.info(f"Loaded {rows_written} records", records=rows_written)

    return rows_written


# Define DAG
with DAG(
    dag_id="ingestion_template",
    default_args=default_args,
    description="Template for data ingestion pipelines",
    schedule="@daily",
    catchup=False,
    tags=["ingestion", "template"],
) as dag:

    # Task 1: Extract data
    extract_task = PythonOperator(
        task_id="extract_data",
        python_callable=extract_data,
        provide_context=True,
    )

    # Task 2: Load data
    load_task = PythonOperator(
        task_id="load_data",
        python_callable=load_data,
        provide_context=True,
    )

    # Define task dependencies
    extract_task >> load_task
