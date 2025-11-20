from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator, DatabricksSubmitRunOperator
from airflow.operators.dummy import DummyOperator

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['alerts@company.com'],
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Databricks connection
databricks_conn_id = 'databricks_default'
existing_cluster_id = '0123-456789-abcdef'

with DAG(
    dag_id='medallion_multi_source_pipeline',
    default_args=default_args,
    schedule_interval='0 */4 * * *',  # Every 4 hours
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['medallion', 'databricks', 'multi-source'],
) as dag:

    start = DummyOperator(task_id='start')

    # Bronze Layer - Batch ingestion from PostgreSQL
    bronze_batch = DatabricksSubmitRunOperator(
        task_id='bronze_batch_postgres',
        databricks_conn_id=databricks_conn_id,
        existing_cluster_id=existing_cluster_id,
        notebook_task={
            'notebook_path': '/Workspace/Pipelines/bronze_batch',
            'base_parameters': {
                'execution_date': '{{ ds }}'
            }
        },
    )

    # Note: Streaming jobs run continuously, managed separately
    # This DAG handles batch transformations

    # Silver Layer - Data cleansing (batch)
    silver_users = DatabricksSubmitRunOperator(
        task_id='silver_transform_users',
        databricks_conn_id=databricks_conn_id,
        existing_cluster_id=existing_cluster_id,
        notebook_task={
            'notebook_path': '/Workspace/Pipelines/silver_transformations',
            'base_parameters': {
                'execution_date': '{{ ds }}',
                'tables': 'users,products'
            }
        },
    )

    # Gold Layer - Aggregations
    gold_user_activity = DatabricksSubmitRunOperator(
        task_id='gold_user_activity',
        databricks_conn_id=databricks_conn_id,
        existing_cluster_id=existing_cluster_id,
        notebook_task={
            'notebook_path': '/Workspace/Pipelines/gold_aggregations',
            'base_parameters': {
                'execution_date': '{{ ds }}',
                'aggregation': 'user_activity'
            }
        },
    )

    gold_transaction_metrics = DatabricksSubmitRunOperator(
        task_id='gold_transaction_metrics',
        databricks_conn_id=databricks_conn_id,
        existing_cluster_id=existing_cluster_id,
        notebook_task={
            'notebook_path': '/Workspace/Pipelines/gold_aggregations',
            'base_parameters': {
                'execution_date': '{{ ds }}',
                'aggregation': 'transaction_metrics'
            }
        },
    )

    gold_product_performance = DatabricksSubmitRunOperator(
        task_id='gold_product_performance',
        databricks_conn_id=databricks_conn_id,
        existing_cluster_id=existing_cluster_id,
        notebook_task={
            'notebook_path': '/Workspace/Pipelines/gold_aggregations',
            'base_parameters': {
                'execution_date': '{{ ds }}',
                'aggregation': 'product_performance'
            }
        },
    )

    gold_user_ltv = DatabricksSubmitRunOperator(
        task_id='gold_user_ltv',
        databricks_conn_id=databricks_conn_id,
        existing_cluster_id=existing_cluster_id,
        notebook_task={
            'notebook_path': '/Workspace/Pipelines/gold_aggregations',
            'base_parameters': {
                'execution_date': '{{ ds }}',
                'aggregation': 'user_ltv'
            }
        },
    )

    end = DummyOperator(task_id='end')

    # Define dependencies
    start >> bronze_batch >> silver_users

    silver_users >> [
        gold_user_activity,
        gold_transaction_metrics,
        gold_product_performance,
        gold_user_ltv
    ] >> end
