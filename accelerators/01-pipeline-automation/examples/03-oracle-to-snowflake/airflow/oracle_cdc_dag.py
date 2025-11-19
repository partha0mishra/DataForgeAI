"""
Oracle to Snowflake CDC Migration DAG

Production-ready Airflow DAG for Oracle to Snowflake migration with:
- Schema discovery and DDL generation
- Parallel table extraction
- CDC processing with SCN tracking
- Snowflake COPY INTO loading
- Data validation and reconciliation

Author: DataForgeAI
"""

from datetime import datetime, timedelta
import logging
import json
from typing import Dict, Any, List

from airflow import DAG
from airflow.decorators import task, task_group
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.models import Variable
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

import sys
sys.path.append('/opt/airflow/scripts')

# Configure logging
logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'email': ['data-alerts@company.com'],
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
}

# DAG Configuration
DAG_ID = 'oracle_to_snowflake_cdc'
SCHEDULE_INTERVAL = '0 */4 * * *'  # Every 4 hours

# Configuration from Airflow Variables
ORACLE_CONN_ID = 'oracle_source'
SNOWFLAKE_CONN_ID = 'snowflake_target'
AWS_CONN_ID = 'aws_default'
S3_BUCKET = Variable.get('migration_s3_bucket', default_var='migration-staging')
S3_PREFIX = Variable.get('migration_s3_prefix', default_var='oracle-cdc/')
SNOWFLAKE_DATABASE = Variable.get('snowflake_migration_db', default_var='MIGRATED')
SNOWFLAKE_WAREHOUSE = Variable.get('snowflake_migration_wh', default_var='MIGRATION_WH')

# Tables to migrate (would typically come from configuration)
MIGRATION_TABLES = [
    {
        'schema': 'HR',
        'table': 'EMPLOYEES',
        'primary_key': ['EMPLOYEE_ID'],
        'incremental_column': 'LAST_UPDATED'
    },
    {
        'schema': 'FINANCE',
        'table': 'GL_TRANSACTIONS',
        'primary_key': ['TRANSACTION_ID'],
        'incremental_column': 'CREATED_DATE'
    }
]


@task
def discover_oracle_schema() -> Dict[str, Any]:
    """
    Discover Oracle schema metadata and generate Snowflake DDL.

    Returns:
        Schema discovery results
    """
    try:
        from schema_discovery import OracleSchemaDiscovery

        logger.info("Starting Oracle schema discovery")

        # Get Oracle connection details from Airflow
        from airflow.hooks.base import BaseHook
        oracle_conn = BaseHook.get_connection(ORACLE_CONN_ID)

        # Parse connection
        discoverer = OracleSchemaDiscovery(
            host=oracle_conn.host,
            port=oracle_conn.port or 1521,
            service_name=oracle_conn.extra_dejson.get('service_name', oracle_conn.schema),
            username=oracle_conn.login,
            password=oracle_conn.password
        )

        discoverer.connect()

        # Get schemas to migrate
        schemas = list(set(t['schema'] for t in MIGRATION_TABLES))

        # Discover metadata
        all_tables_metadata = []
        for table_config in MIGRATION_TABLES:
            metadata = discoverer.get_table_metadata(
                table_config['schema'],
                table_config['table']
            )
            all_tables_metadata.append(metadata)

        # Export to files
        output_dir = '/tmp/oracle_discovery'
        import os
        os.makedirs(output_dir, exist_ok=True)

        yaml_file = f'{output_dir}/schema_manifest.yaml'
        sql_file = f'{output_dir}/snowflake_ddl.sql'

        discoverer.export_to_yaml(all_tables_metadata, yaml_file)
        discoverer.export_to_sql(all_tables_metadata, sql_file)

        discoverer.disconnect()

        logger.info(f"Schema discovery complete: {len(all_tables_metadata)} tables")

        return {
            'status': 'success',
            'tables_discovered': len(all_tables_metadata),
            'yaml_file': yaml_file,
            'sql_file': sql_file,
        }

    except Exception as e:
        logger.error(f"Schema discovery failed: {e}")
        raise AirflowException(f"Discovery error: {str(e)}")


@task
def create_snowflake_schemas(discovery_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create schemas and tables in Snowflake.

    Args:
        discovery_result: Result from schema discovery

    Returns:
        Schema creation result
    """
    try:
        logger.info("Creating Snowflake schemas and tables")

        snowflake_hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)

        # Read generated DDL
        with open(discovery_result['sql_file'], 'r') as f:
            ddl = f.read()

        # Execute DDL
        logger.info("Executing Snowflake DDL")
        snowflake_hook.run(ddl)

        logger.info("Snowflake schemas and tables created")

        return {
            'status': 'success',
            'ddl_executed': True,
        }

    except Exception as e:
        logger.error(f"Schema creation failed: {e}")
        raise AirflowException(f"Schema creation error: {str(e)}")


@task
def extract_table_cdc(
    table_config: Dict[str, str],
    full_refresh: bool = False
) -> Dict[str, Any]:
    """
    Extract CDC data from a single Oracle table.

    Args:
        table_config: Table configuration
        full_refresh: Whether to do full refresh

    Returns:
        Extraction result
    """
    try:
        from cdc_processor import OracleCDCProcessor, CDCConfig

        logger.info(f"Extracting CDC for {table_config['schema']}.{table_config['table']}")

        # Get Oracle connection
        from airflow.hooks.base import BaseHook
        oracle_conn = BaseHook.get_connection(ORACLE_CONN_ID)

        # Configure CDC processor
        config = CDCConfig(
            host=oracle_conn.host,
            port=oracle_conn.port or 1521,
            service_name=oracle_conn.extra_dejson.get('service_name', oracle_conn.schema),
            username=oracle_conn.login,
            password=oracle_conn.password,
            schema=table_config['schema'],
            table=table_config['table'],
            primary_key=table_config['primary_key'],
            incremental_column=table_config.get('incremental_column', 'LAST_UPDATED'),
            output_path=f'/tmp/cdc/{table_config["schema"]}',
            use_scn=True,
        )

        # Run CDC extraction
        processor = OracleCDCProcessor(config)
        result = processor.run_cdc_extraction(full_refresh=full_refresh)

        logger.info(f"CDC extraction complete: {result['rows_extracted']} rows")

        return result

    except Exception as e:
        logger.error(f"CDC extraction failed for {table_config['table']}: {e}")
        raise AirflowException(f"CDC error: {str(e)}")


@task
def upload_to_s3(extraction_result: Dict[str, Any], table_config: Dict[str, str]) -> Dict[str, Any]:
    """
    Upload extracted Parquet file to S3.

    Args:
        extraction_result: CDC extraction result
        table_config: Table configuration

    Returns:
        Upload result
    """
    try:
        output_file = extraction_result.get('output_file')

        if not output_file or extraction_result['rows_extracted'] == 0:
            logger.info("No data to upload")
            return {
                'status': 'skipped',
                'reason': 'no_data'
            }

        logger.info(f"Uploading {output_file} to S3")

        s3_hook = S3Hook(aws_conn_id=AWS_CONN_ID)

        # Build S3 key
        import os
        filename = os.path.basename(output_file)
        s3_key = f"{S3_PREFIX}{table_config['schema']}/{table_config['table']}/{filename}"

        # Upload file
        s3_hook.load_file(
            filename=output_file,
            key=s3_key,
            bucket_name=S3_BUCKET,
            replace=True
        )

        s3_uri = f"s3://{S3_BUCKET}/{s3_key}"

        logger.info(f"Uploaded to {s3_uri}")

        return {
            'status': 'success',
            's3_bucket': S3_BUCKET,
            's3_key': s3_key,
            's3_uri': s3_uri,
            'rows': extraction_result['rows_extracted'],
        }

    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise AirflowException(f"Upload error: {str(e)}")


@task
def load_to_snowflake(
    s3_result: Dict[str, Any],
    table_config: Dict[str, str]
) -> Dict[str, Any]:
    """
    Load data from S3 to Snowflake using COPY INTO.

    Args:
        s3_result: S3 upload result
        table_config: Table configuration

    Returns:
        Load result
    """
    try:
        if s3_result.get('status') == 'skipped':
            logger.info("Skipping load - no data")
            return {'status': 'skipped'}

        logger.info(f"Loading to Snowflake: {table_config['schema']}.{table_config['table']}")

        snowflake_hook = SnowflakeHook(snowflake_conn_id=SNOWFLAKE_CONN_ID)

        # Create stage if not exists
        stage_name = f"{SNOWFLAKE_DATABASE}.PUBLIC.CDC_STAGE"
        create_stage_sql = f"""
        CREATE STAGE IF NOT EXISTS {stage_name}
        URL = 's3://{s3_result['s3_bucket']}'
        CREDENTIALS = (AWS_KEY_ID = '{{aws_key}}' AWS_SECRET_KEY = '{{aws_secret}}')
        FILE_FORMAT = (TYPE = 'PARQUET');
        """

        snowflake_hook.run(create_stage_sql)

        # COPY INTO target table
        target_table = f"{SNOWFLAKE_DATABASE}.{table_config['schema'].lower()}.{table_config['table'].lower()}"

        copy_sql = f"""
        COPY INTO {target_table}
        FROM @{stage_name}/{s3_result['s3_key']}
        FILE_FORMAT = (TYPE = 'PARQUET')
        MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
        ON_ERROR = 'CONTINUE';
        """

        logger.info(f"Executing COPY INTO: {target_table}")
        result = snowflake_hook.run(copy_sql, handler=lambda cur: cur.fetchall())

        # Parse result
        if result and len(result) > 0:
            rows_loaded = result[0][1] if len(result[0]) > 1 else 0
            rows_error = result[0][2] if len(result[0]) > 2 else 0

            logger.info(f"Loaded {rows_loaded} rows, {rows_error} errors")

            return {
                'status': 'success',
                'table': target_table,
                'rows_loaded': rows_loaded,
                'rows_error': rows_error,
            }
        else:
            raise AirflowException("COPY INTO returned no results")

    except Exception as e:
        logger.error(f"Snowflake load failed: {e}")
        raise AirflowException(f"Load error: {str(e)}")


@task
def validate_table_load(
    load_result: Dict[str, Any],
    extraction_result: Dict[str, Any],
    table_config: Dict[str, str]
) -> Dict[str, Any]:
    """
    Validate data load by comparing row counts.

    Args:
        load_result: Snowflake load result
        extraction_result: CDC extraction result
        table_config: Table configuration

    Returns:
        Validation result
    """
    try:
        if load_result.get('status') == 'skipped':
            return {'status': 'skipped'}

        logger.info(f"Validating {table_config['table']} load")

        extracted_rows = extraction_result['rows_extracted']
        loaded_rows = load_result['rows_loaded']
        error_rows = load_result.get('rows_error', 0)

        # Check if loaded + errors = extracted
        total_processed = loaded_rows + error_rows

        if total_processed != extracted_rows:
            logger.warning(
                f"Row count mismatch: extracted={extracted_rows}, "
                f"loaded={loaded_rows}, errors={error_rows}"
            )

        validation_passed = (error_rows == 0) and (loaded_rows == extracted_rows)

        result = {
            'status': 'validated' if validation_passed else 'warning',
            'table': table_config['table'],
            'extracted_rows': extracted_rows,
            'loaded_rows': loaded_rows,
            'error_rows': error_rows,
            'validation_passed': validation_passed,
        }

        logger.info(f"Validation result: {result}")
        return result

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise AirflowException(f"Validation error: {str(e)}")


@task
def aggregate_results(validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate results from all table migrations.

    Args:
        validation_results: List of validation results

    Returns:
        Aggregated results
    """
    total_extracted = sum(r.get('extracted_rows', 0) for r in validation_results)
    total_loaded = sum(r.get('loaded_rows', 0) for r in validation_results)
    total_errors = sum(r.get('error_rows', 0) for r in validation_results)

    all_passed = all(r.get('validation_passed', False) for r in validation_results)

    result = {
        'total_tables': len(validation_results),
        'total_extracted': total_extracted,
        'total_loaded': total_loaded,
        'total_errors': total_errors,
        'all_validations_passed': all_passed,
        'timestamp': datetime.utcnow().isoformat(),
    }

    logger.info("=" * 80)
    logger.info("Migration Summary")
    logger.info("=" * 80)
    logger.info(f"Tables migrated: {result['total_tables']}")
    logger.info(f"Total rows extracted: {result['total_extracted']}")
    logger.info(f"Total rows loaded: {result['total_loaded']}")
    logger.info(f"Total errors: {result['total_errors']}")
    logger.info(f"All validations passed: {result['all_validations_passed']}")
    logger.info("=" * 80)

    return result


# Create the DAG
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description='Oracle to Snowflake CDC migration pipeline',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=datetime(2024, 11, 1),
    catchup=False,
    tags=['oracle', 'snowflake', 'cdc', 'migration'],
    max_active_runs=1,
    params={
        'full_refresh': False,
    }
) as dag:

    # Task 1: Discover Oracle schemas
    schema_discovery = discover_oracle_schema()

    # Task 2: Create Snowflake schemas
    snowflake_setup = create_snowflake_schemas(schema_discovery)

    # Task 3-6: Process each table in parallel
    validation_results = []

    for table_config in MIGRATION_TABLES:
        with TaskGroup(group_id=f"migrate_{table_config['table'].lower()}") as table_group:
            # Extract CDC
            cdc_extract = extract_table_cdc(
                table_config=table_config,
                full_refresh="{{ params.full_refresh }}"
            )

            # Upload to S3
            s3_upload = upload_to_s3(cdc_extract, table_config)

            # Load to Snowflake
            sf_load = load_to_snowflake(s3_upload, table_config)

            # Validate
            validation = validate_table_load(sf_load, cdc_extract, table_config)

            # Define dependencies within group
            cdc_extract >> s3_upload >> sf_load >> validation

            validation_results.append(validation)

        # Set dependencies
        snowflake_setup >> table_group

    # Task 7: Aggregate all results
    summary = aggregate_results(validation_results)


if __name__ == "__main__":
    print(f"DAG {DAG_ID} loaded successfully")
    print(f"Tables to migrate: {len(MIGRATION_TABLES)}")
