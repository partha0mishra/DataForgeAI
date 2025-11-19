"""
Sales CSV to Snowflake Ingestion DAG

This DAG demonstrates a production-ready batch ingestion pipeline:
- Waits for CSV files in S3 using sensor pattern
- Extracts and validates CSV data
- Loads to Snowflake bronze layer using COPY INTO
- Triggers dbt transformations for silver layer
- Implements idempotent design with proper error handling

Author: DataForgeAI
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
import json

from airflow import DAG
from airflow.decorators import task
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.models import Variable
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Configure logging
logger = logging.getLogger(__name__)

# Default arguments for all tasks
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'email': ['data-alerts@company.com'],
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
}

# DAG Configuration
DAG_ID = 'sales_csv_to_snowflake'
SCHEDULE_INTERVAL = '@daily'  # Run daily at midnight UTC

# Get configuration from Airflow Variables with defaults
S3_BUCKET = Variable.get('s3_bucket', default_var='your-bucket-name')
S3_PREFIX = Variable.get('s3_prefix', default_var='sales/')
S3_FILE_PATTERN = Variable.get('s3_file_pattern', default_var='sales_*.csv')
SNOWFLAKE_CONN_ID = 'snowflake_default'
AWS_CONN_ID = 'aws_default'
SNOWFLAKE_DATABASE = Variable.get('snowflake_database', default_var='ANALYTICS')
SNOWFLAKE_SCHEMA = Variable.get('snowflake_schema', default_var='sales')
SNOWFLAKE_WAREHOUSE = Variable.get('snowflake_warehouse', default_var='COMPUTE_WH')


def create_snowflake_tables(snowflake_hook: SnowflakeHook) -> None:
    """
    Create bronze layer table if not exists.
    Idempotent operation - safe to run multiple times.
    """
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {SNOWFLAKE_DATABASE}.bronze.sales_raw (
        sale_id VARCHAR(50),
        customer_id VARCHAR(50),
        product_id VARCHAR(50),
        sale_date VARCHAR(50),
        amount VARCHAR(50),
        quantity VARCHAR(50),
        load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        source_file VARCHAR(500)
    )
    COMMENT = 'Bronze layer - Raw sales data from CSV files';
    """

    logger.info("Creating bronze.sales_raw table if not exists")
    snowflake_hook.run(create_table_sql)
    logger.info("Table creation complete")


@task
def validate_s3_file(s3_key: str) -> Dict[str, Any]:
    """
    Validate S3 file exists and is readable.
    Returns file metadata for downstream tasks.
    """
    try:
        s3_hook = S3Hook(aws_conn_id=AWS_CONN_ID)

        # Check if file exists
        if not s3_hook.check_for_key(key=s3_key, bucket_name=S3_BUCKET):
            raise AirflowException(f"File not found: s3://{S3_BUCKET}/{s3_key}")

        # Get file metadata
        file_obj = s3_hook.get_key(key=s3_key, bucket_name=S3_BUCKET)
        file_size = file_obj.content_length
        last_modified = file_obj.last_modified.isoformat()

        logger.info(f"File validated: {s3_key}, Size: {file_size} bytes, Modified: {last_modified}")

        return {
            's3_key': s3_key,
            's3_bucket': S3_BUCKET,
            's3_uri': f's3://{S3_BUCKET}/{s3_key}',
            'file_size': file_size,
            'last_modified': last_modified
        }

    except Exception as e:
        logger.error(f"File validation failed: {str(e)}")
        raise AirflowException(f"S3 file validation error: {str(e)}")


@task
def create_snowflake_stage(file_metadata: Dict[str, Any]) -> str:
    """
    Create Snowflake stage for S3 file loading.
    Returns stage name for use in COPY command.
    """
    try:
        snowflake_hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)

        # Ensure bronze schema exists
        create_schema_sql = f"""
        CREATE SCHEMA IF NOT EXISTS {SNOWFLAKE_DATABASE}.bronze
        COMMENT = 'Bronze layer - Raw ingested data';
        """
        snowflake_hook.run(create_schema_sql)

        # Create or replace external stage pointing to S3
        stage_name = f"{SNOWFLAKE_DATABASE}.bronze.sales_s3_stage"
        create_stage_sql = f"""
        CREATE STAGE IF NOT EXISTS {stage_name}
        URL = 's3://{S3_BUCKET}/{S3_PREFIX}'
        CREDENTIALS = (AWS_KEY_ID = '{{aws_access_key_id}}' AWS_SECRET_KEY = '{{aws_secret_access_key}}')
        FILE_FORMAT = (
            TYPE = 'CSV'
            FIELD_DELIMITER = ','
            SKIP_HEADER = 1
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            NULL_IF = ('NULL', 'null', '')
            EMPTY_FIELD_AS_NULL = TRUE
            ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
        );
        """

        logger.info(f"Creating Snowflake stage: {stage_name}")
        snowflake_hook.run(create_stage_sql)

        # Create bronze table
        create_snowflake_tables(snowflake_hook)

        return stage_name

    except Exception as e:
        logger.error(f"Stage creation failed: {str(e)}")
        raise AirflowException(f"Snowflake stage creation error: {str(e)}")


@task
def load_to_snowflake_bronze(file_metadata: Dict[str, Any], stage_name: str) -> Dict[str, Any]:
    """
    Load CSV data from S3 to Snowflake bronze layer using COPY INTO.
    Implements idempotent loading - tracks loaded files to prevent duplicates.
    """
    try:
        snowflake_hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)
        s3_key = file_metadata['s3_key']
        file_name = s3_key.split('/')[-1]

        logger.info(f"Loading file to Snowflake: {file_name}")

        # Check if file already loaded (idempotency check)
        check_sql = f"""
        SELECT COUNT(*) as count
        FROM {SNOWFLAKE_DATABASE}.bronze.sales_raw
        WHERE source_file = '{file_name}';
        """

        result = snowflake_hook.get_first(check_sql)
        existing_count = result[0] if result else 0

        if existing_count > 0:
            logger.warning(f"File {file_name} already loaded with {existing_count} rows. Skipping.")
            return {
                'status': 'skipped',
                'file': file_name,
                'rows_loaded': 0,
                'reason': 'already_processed'
            }

        # Load data using COPY INTO
        copy_sql = f"""
        COPY INTO {SNOWFLAKE_DATABASE}.bronze.sales_raw (
            sale_id, customer_id, product_id, sale_date, amount, quantity, source_file
        )
        FROM (
            SELECT
                $1::VARCHAR as sale_id,
                $2::VARCHAR as customer_id,
                $3::VARCHAR as product_id,
                $4::VARCHAR as sale_date,
                $5::VARCHAR as amount,
                $6::VARCHAR as quantity,
                '{file_name}' as source_file
            FROM @{stage_name}/{file_name}
        )
        FILE_FORMAT = (
            TYPE = 'CSV'
            SKIP_HEADER = 1
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            NULL_IF = ('NULL', 'null', '')
        )
        ON_ERROR = 'CONTINUE';
        """

        logger.info("Executing COPY INTO command")
        result = snowflake_hook.run(copy_sql, handler=lambda cur: cur.fetchall())

        # Parse COPY result
        if result and len(result) > 0:
            copy_result = result[0]
            rows_loaded = copy_result[1] if len(copy_result) > 1 else 0
            rows_error = copy_result[2] if len(copy_result) > 2 else 0

            logger.info(f"Load complete: {rows_loaded} rows loaded, {rows_error} errors")

            if rows_error > 0:
                logger.warning(f"Load completed with {rows_error} error rows")

            return {
                'status': 'success',
                'file': file_name,
                'rows_loaded': rows_loaded,
                'rows_error': rows_error,
                's3_uri': file_metadata['s3_uri']
            }
        else:
            raise AirflowException("COPY INTO command did not return expected results")

    except Exception as e:
        logger.error(f"Snowflake load failed: {str(e)}")
        raise AirflowException(f"Data loading error: {str(e)}")


@task
def validate_load(load_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate loaded data meets quality thresholds.
    Checks for minimum row count and data quality.
    """
    try:
        if load_result['status'] == 'skipped':
            logger.info("Load was skipped, validation not needed")
            return load_result

        snowflake_hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)
        file_name = load_result['file']

        # Count records loaded
        count_sql = f"""
        SELECT
            COUNT(*) as total_rows,
            COUNT(DISTINCT sale_id) as distinct_sales,
            SUM(CASE WHEN sale_id IS NULL THEN 1 ELSE 0 END) as null_sale_ids,
            MIN(load_timestamp) as min_load_time,
            MAX(load_timestamp) as max_load_time
        FROM {SNOWFLAKE_DATABASE}.bronze.sales_raw
        WHERE source_file = '{file_name}';
        """

        result = snowflake_hook.get_first(count_sql)

        if result:
            total_rows, distinct_sales, null_sale_ids, min_load_time, max_load_time = result

            logger.info(f"Validation results: {total_rows} total rows, {distinct_sales} distinct sales")

            # Quality checks
            if total_rows == 0:
                raise AirflowException("Validation failed: No rows loaded")

            if null_sale_ids > total_rows * 0.1:  # More than 10% nulls
                logger.warning(f"High null rate in sale_id: {null_sale_ids}/{total_rows}")

            return {
                **load_result,
                'validation': {
                    'total_rows': total_rows,
                    'distinct_sales': distinct_sales,
                    'null_sale_ids': null_sale_ids,
                    'load_time_min': str(min_load_time),
                    'load_time_max': str(max_load_time),
                    'passed': True
                }
            }
        else:
            raise AirflowException("Validation query returned no results")

    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        raise AirflowException(f"Data validation error: {str(e)}")


# Create the DAG
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description='Load sales CSV files from S3 to Snowflake bronze layer',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=datetime(2024, 11, 1),
    catchup=False,
    tags=['sales', 'csv', 'snowflake', 'batch', 'bronze'],
    max_active_runs=1,
) as dag:

    # Task 1: Wait for new CSV file in S3
    # Uses sensor pattern - will poke S3 every 60 seconds for up to 1 hour
    wait_for_file = S3KeySensor(
        task_id='wait_for_s3_file',
        bucket_name=S3_BUCKET,
        bucket_key=f"{S3_PREFIX}{S3_FILE_PATTERN}",
        wildcard_match=True,
        aws_conn_id=AWS_CONN_ID,
        timeout=3600,  # 1 hour timeout
        poke_interval=60,  # Check every 60 seconds
        mode='poke',  # Use poke mode (can also use 'reschedule' for long waits)
    )

    # Task 2: Validate the S3 file
    file_validation = validate_s3_file(f"{S3_PREFIX}sales_2024_11.csv")

    # Task 3: Create Snowflake stage
    stage_creation = create_snowflake_stage(file_validation)

    # Task 4: Load to bronze layer
    bronze_load = load_to_snowflake_bronze(file_validation, stage_creation)

    # Task 5: Validate loaded data
    load_validation = validate_load(bronze_load)

    # Task 6: Run dbt models (bronze -> silver transformation)
    # This assumes dbt is installed and configured in the Airflow environment
    dbt_run = BashOperator(
        task_id='run_dbt_models',
        bash_command="""
        cd /opt/airflow/dbt/sales_pipeline && \
        dbt run --models sales_raw sales_clean --profiles-dir /opt/airflow/dbt
        """,
        env={
            'DBT_SNOWFLAKE_ACCOUNT': '{{ conn.snowflake_default.extra_dejson.account }}',
            'DBT_SNOWFLAKE_USER': '{{ conn.snowflake_default.login }}',
            'DBT_SNOWFLAKE_PASSWORD': '{{ conn.snowflake_default.password }}',
            'DBT_SNOWFLAKE_ROLE': '{{ conn.snowflake_default.extra_dejson.role }}',
            'DBT_SNOWFLAKE_DATABASE': SNOWFLAKE_DATABASE,
            'DBT_SNOWFLAKE_WAREHOUSE': SNOWFLAKE_WAREHOUSE,
        },
    )

    # Task 7: Run dbt tests
    dbt_test = BashOperator(
        task_id='run_dbt_tests',
        bash_command="""
        cd /opt/airflow/dbt/sales_pipeline && \
        dbt test --models sales_raw sales_clean --profiles-dir /opt/airflow/dbt
        """,
        env={
            'DBT_SNOWFLAKE_ACCOUNT': '{{ conn.snowflake_default.extra_dejson.account }}',
            'DBT_SNOWFLAKE_USER': '{{ conn.snowflake_default.login }}',
            'DBT_SNOWFLAKE_PASSWORD': '{{ conn.snowflake_default.password }}',
            'DBT_SNOWFLAKE_ROLE': '{{ conn.snowflake_default.extra_dejson.role }}',
            'DBT_SNOWFLAKE_DATABASE': SNOWFLAKE_DATABASE,
            'DBT_SNOWFLAKE_WAREHOUSE': SNOWFLAKE_WAREHOUSE,
        },
    )

    # Define task dependencies
    wait_for_file >> file_validation >> stage_creation >> bronze_load >> load_validation >> dbt_run >> dbt_test


if __name__ == "__main__":
    # Allow testing DAG syntax by running: python sales_ingestion_dag.py
    print(f"DAG {DAG_ID} loaded successfully")
    print(f"Configuration: S3 Bucket={S3_BUCKET}, Prefix={S3_PREFIX}")
    print(f"Target: {SNOWFLAKE_DATABASE}.bronze.sales_raw")
