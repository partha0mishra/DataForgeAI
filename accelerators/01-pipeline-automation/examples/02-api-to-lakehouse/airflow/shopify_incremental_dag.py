"""
Shopify Incremental Extraction DAG

Production-ready Airflow DAG for incremental API extraction with:
- Scheduled 15-minute intervals
- Shopify API extraction with rate limiting
- Delta Lake merge/upsert operations
- Watermark state management
- Comprehensive error handling and alerts

Author: DataForgeAI
"""

from datetime import datetime, timedelta
import logging
import os
from typing import Dict, Any

from airflow import DAG
from airflow.decorators import task
from airflow.providers.databricks.operators.databricks import DatabricksSubmitRunOperator
from airflow.models import Variable
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

# Import custom extractors (assumes they're in Python path)
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
    'max_retry_delay': timedelta(minutes=30),
}

# DAG Configuration
DAG_ID = 'shopify_orders_incremental'
SCHEDULE_INTERVAL = '*/15 * * * *'  # Every 15 minutes

# Get configuration from Airflow Variables
SHOPIFY_SHOP_URL = Variable.get('shopify_shop_url', default_var='your-store.myshopify.com')
SHOPIFY_API_KEY = Variable.get('shopify_api_key', default_var='')
SHOPIFY_API_SECRET = Variable.get('shopify_api_secret', default_var='')
OUTPUT_BUCKET = Variable.get('shopify_output_bucket', default_var='lakehouse-bronze')
OUTPUT_PREFIX = Variable.get('shopify_output_prefix', default_var='shopify/orders/')
DELTA_TARGET_PATH = Variable.get('delta_target_path', default_var='s3a://lakehouse/bronze/shopify/orders')
DATABRICKS_CONN_ID = 'databricks_default'
AWS_CONN_ID = 'aws_default'


@task
def extract_shopify_orders(
    start_date: str = None,
    end_date: str = None,
    full_refresh: bool = False,
    **context
) -> Dict[str, Any]:
    """
    Extract orders from Shopify API.

    Args:
        start_date: Start date for extraction (ISO format)
        end_date: End date for extraction (ISO format)
        full_refresh: Force full extraction

    Returns:
        Extraction result metadata
    """
    try:
        from shopify_extractor import ShopifyExtractor, ExtractionConfig

        logger.info("Starting Shopify orders extraction")

        # Build output path with execution date
        execution_date = context['execution_date'].strftime('%Y/%m/%d')
        output_path = f"/tmp/shopify/{execution_date}"

        config = ExtractionConfig(
            shop_url=SHOPIFY_SHOP_URL,
            api_key=SHOPIFY_API_KEY,
            api_secret=SHOPIFY_API_SECRET,
            api_version="2024-01",
            endpoint="orders",
            rate_limit_per_second=2.0,
            page_size=250,
            output_format='parquet',
            output_path=output_path,
            incremental_state_file='/opt/airflow/state/shopify_watermark.json',
        )

        extractor = ShopifyExtractor(config)

        # Run extraction
        output_file = extractor.extract(
            start_date=start_date,
            end_date=end_date,
            full_refresh=full_refresh
        )

        # Get file statistics
        file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0

        result = {
            'status': 'success',
            'output_file': output_file,
            'file_size': file_size,
            'execution_date': execution_date,
        }

        logger.info(f"Extraction completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Shopify extraction failed: {e}")
        raise AirflowException(f"Extraction error: {str(e)}")


@task
def upload_to_s3(extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upload extracted data to S3 staging area.

    Args:
        extraction_result: Result from extraction task

    Returns:
        S3 upload metadata
    """
    try:
        output_file = extraction_result['output_file']

        if not os.path.exists(output_file):
            raise AirflowException(f"Output file not found: {output_file}")

        s3_hook = S3Hook(aws_conn_id=AWS_CONN_ID)

        # Build S3 key
        filename = os.path.basename(output_file)
        s3_key = f"{OUTPUT_PREFIX}{extraction_result['execution_date']}/{filename}"

        logger.info(f"Uploading {output_file} to s3://{OUTPUT_BUCKET}/{s3_key}")

        # Upload file
        s3_hook.load_file(
            filename=output_file,
            key=s3_key,
            bucket_name=OUTPUT_BUCKET,
            replace=True
        )

        # Get uploaded file metadata
        file_obj = s3_hook.get_key(key=s3_key, bucket_name=OUTPUT_BUCKET)
        file_size = file_obj.content_length

        result = {
            'status': 'success',
            's3_bucket': OUTPUT_BUCKET,
            's3_key': s3_key,
            's3_uri': f's3://{OUTPUT_BUCKET}/{s3_key}',
            'file_size': file_size,
        }

        logger.info(f"Upload completed: {result}")

        # Cleanup local file
        try:
            os.remove(output_file)
            logger.info(f"Removed local file: {output_file}")
        except Exception as e:
            logger.warning(f"Failed to remove local file: {e}")

        return result

    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise AirflowException(f"Upload error: {str(e)}")


@task
def trigger_delta_merge(s3_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trigger Delta Lake merge operation via Databricks.

    Args:
        s3_result: Result from S3 upload task

    Returns:
        Merge operation metadata
    """
    try:
        logger.info("Triggering Delta Lake merge operation")

        # For this example, we'll use local Spark
        # In production, this would submit to Databricks
        from delta_merger import DeltaMerger, MergeConfig

        config = MergeConfig(
            source_path=s3_result['s3_uri'],
            target_path=DELTA_TARGET_PATH,
            merge_keys=['id'],
            partition_cols=['_merge_date'],
            enable_schema_evolution=True,
            optimize_after_merge=True,
            vacuum_after_merge=False,
        )

        merger = DeltaMerger(config)
        merge_result = merger.run()

        logger.info(f"Merge completed: {merge_result}")
        return merge_result

    except Exception as e:
        logger.error(f"Delta merge failed: {e}")
        raise AirflowException(f"Merge error: {str(e)}")


@task
def validate_merge(merge_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate merge operation completed successfully.

    Args:
        merge_result: Result from merge task

    Returns:
        Validation result
    """
    try:
        logger.info("Validating merge operation")

        if merge_result.get('status') != 'success':
            raise AirflowException(f"Merge did not complete successfully: {merge_result}")

        metrics = merge_result.get('metrics', {})

        # Extract merge statistics
        num_inserted = int(metrics.get('numTargetRowsInserted', 0))
        num_updated = int(metrics.get('numTargetRowsUpdated', 0))
        num_deleted = int(metrics.get('numTargetRowsDeleted', 0))

        total_changes = num_inserted + num_updated + num_deleted

        logger.info(
            f"Merge validation: {total_changes} total changes "
            f"({num_inserted} inserted, {num_updated} updated, {num_deleted} deleted)"
        )

        validation_result = {
            'status': 'validated',
            'total_changes': total_changes,
            'num_inserted': num_inserted,
            'num_updated': num_updated,
            'num_deleted': num_deleted,
        }

        return validation_result

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise AirflowException(f"Validation error: {str(e)}")


@task
def send_completion_notification(validation_result: Dict[str, Any]) -> None:
    """
    Send notification about pipeline completion.

    Args:
        validation_result: Validation result
    """
    logger.info("=" * 80)
    logger.info("Shopify Incremental Pipeline Completed Successfully")
    logger.info("=" * 80)
    logger.info(f"Total changes: {validation_result['total_changes']}")
    logger.info(f"  - Inserted: {validation_result['num_inserted']}")
    logger.info(f"  - Updated: {validation_result['num_updated']}")
    logger.info(f"  - Deleted: {validation_result['num_deleted']}")
    logger.info("=" * 80)

    # In production, this would send email/Slack notification
    # For now, just log


# Create the DAG
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description='Incremental Shopify orders extraction to Delta Lake',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=datetime(2024, 11, 1),
    catchup=False,
    tags=['shopify', 'api', 'delta-lake', 'incremental'],
    max_active_runs=1,
    params={
        'full_refresh': False,
        'start_date': None,
        'end_date': None,
    }
) as dag:

    # Task 1: Extract from Shopify API
    extraction = extract_shopify_orders(
        start_date="{{ params.start_date }}",
        end_date="{{ params.end_date }}",
        full_refresh="{{ params.full_refresh }}"
    )

    # Task 2: Upload to S3
    s3_upload = upload_to_s3(extraction)

    # Task 3: Merge into Delta Lake
    delta_merge = trigger_delta_merge(s3_upload)

    # Task 4: Validate merge
    validation = validate_merge(delta_merge)

    # Task 5: Send notification
    notification = send_completion_notification(validation)

    # Define dependencies
    extraction >> s3_upload >> delta_merge >> validation >> notification


# Alternative: Using Databricks Operator for production
def create_databricks_merge_task():
    """
    Example of using Databricks operator for Delta merge.
    Uncomment and configure for production Databricks deployment.
    """
    return DatabricksSubmitRunOperator(
        task_id='databricks_delta_merge',
        databricks_conn_id=DATABRICKS_CONN_ID,
        new_cluster={
            'spark_version': '13.3.x-scala2.12',
            'node_type_id': 'i3.xlarge',
            'num_workers': 2,
            'spark_conf': {
                'spark.databricks.delta.preview.enabled': 'true',
            }
        },
        spark_python_task={
            'python_file': 'dbfs:/scripts/delta_merger.py',
            'parameters': [
                '--source-path', '{{ task_instance.xcom_pull(task_ids="upload_to_s3")["s3_uri"] }}',
                '--target-path', DELTA_TARGET_PATH,
                '--merge-keys', 'id',
            ]
        },
    )


if __name__ == "__main__":
    # Allow testing DAG syntax
    print(f"DAG {DAG_ID} loaded successfully")
    print(f"Schedule: {SCHEDULE_INTERVAL}")
    print(f"Target: {DELTA_TARGET_PATH}")
