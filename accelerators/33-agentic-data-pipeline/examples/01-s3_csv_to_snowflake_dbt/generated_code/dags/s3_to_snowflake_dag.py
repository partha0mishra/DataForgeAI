from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['alerts@company.com'],
    'email_on_failure': True,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='s3_csv_to_snowflake_dbt',
    default_args=default_args,
    schedule_interval='0 2 * * *',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['sales', 'etl', 'snowflake'],
) as dag:
    check_s3_file = S3KeySensor(
        task_id='check_s3_file',
        bucket_name='company-data-lake',
        bucket_key='raw/sales/{{ ds }}/sales_*.csv',
        aws_conn_id='aws_default',
    )

    load_bronze = SnowflakeOperator(
        task_id='load_to_bronze',
        snowflake_conn_id='snowflake_default',
        sql="""
        COPY INTO sales.bronze.sales_raw
        FROM @sales.external_stages.s3_sales_stage/{{ ds }}/
        FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1)
        ON_ERROR = 'CONTINUE'
        FORCE = TRUE;
        """,
    )

    run_dbt = BashOperator(
        task_id='run_dbt',
        bash_command='cd /opt/airflow/dbt && dbt run --models silver.sales_clean',
    )

    run_dbt_tests = BashOperator(
        task_id='run_dbt_tests',
        bash_command='cd /opt/airflow/dbt && dbt test --models silver.sales_clean',
    )

    check_s3_file >> load_bronze >> run_dbt >> run_dbt_tests
