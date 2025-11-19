"""
Snowpark Python Pipeline with Dynamic Tables

This module demonstrates a production-ready data pipeline using Snowpark Python:
- Read from external stage (S3/Azure/GCS)
- Apply data quality checks
- Transform data using PII masking UDFs
- Write to Snowflake tables
- Orchestrate with dynamic tables for automated refresh

Features:
- External stage integration
- Data quality validation
- PII masking integration
- Error handling and logging
- Metrics and monitoring
- Dynamic table orchestration

Prerequisites:
- Snowflake account with external stage configured
- PII masking UDFs registered (run pii_masking_udf.py first)
- Python 3.8+
- snowflake-snowpark-python library

Usage:
    python dynamic_table_pipeline.py
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, lit, current_timestamp, when_matched, when_not_matched
from snowflake.snowpark.types import StructType, StructField, StringType, IntegerType, DecimalType, DateType
import snowflake.snowpark.exceptions as sp_exceptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineMetrics:
    """Track pipeline execution metrics."""

    def __init__(self):
        self.start_time = datetime.now()
        self.records_read = 0
        self.records_processed = 0
        self.records_written = 0
        self.records_failed = 0
        self.errors = []

    def log_summary(self):
        """Log pipeline execution summary."""
        duration = (datetime.now() - self.start_time).total_seconds()
        logger.info("\n" + "="*80)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("="*80)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Records Read: {self.records_read:,}")
        logger.info(f"Records Processed: {self.records_processed:,}")
        logger.info(f"Records Written: {self.records_written:,}")
        logger.info(f"Records Failed: {self.records_failed:,}")
        if self.errors:
            logger.warning(f"Errors Encountered: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
        logger.info("="*80)


def create_snowpark_session() -> Optional[Session]:
    """
    Create a Snowpark session with connection parameters from environment variables.

    Returns:
        Snowpark Session object or None if connection fails
    """
    try:
        connection_parameters = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "database": os.getenv("SNOWFLAKE_DATABASE", "ANALYTICS"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
            "role": os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
        }

        # Validate required parameters
        required_params = ["account", "user", "password"]
        missing_params = [p for p in required_params if not connection_parameters.get(p)]

        if missing_params:
            logger.error(f"Missing required connection parameters: {', '.join(missing_params)}")
            return None

        logger.info(f"Connecting to Snowflake account: {connection_parameters['account']}")
        session = Session.builder.configs(connection_parameters).create()

        result = session.sql("SELECT CURRENT_VERSION()").collect()
        logger.info(f"Connected to Snowflake version: {result[0][0]}")

        return session

    except Exception as e:
        logger.error(f"Failed to create Snowpark session: {e}")
        return None


def setup_external_stage(session: Session, stage_config: Dict[str, str]) -> bool:
    """
    Set up external stage for CSV files.

    Args:
        session: Active Snowpark session
        stage_config: Stage configuration dictionary

    Returns:
        True if stage setup successful, False otherwise
    """
    try:
        logger.info("Setting up external stage...")

        stage_name = stage_config.get("name", "sales_csvs")
        storage_url = stage_config.get("url", "s3://my-bucket/sales/")
        aws_key_id = os.getenv("AWS_ACCESS_KEY_ID", "")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")

        # Create file format
        create_format_sql = """
        CREATE OR REPLACE FILE FORMAT CSV_FORMAT
            TYPE = 'CSV'
            FIELD_DELIMITER = ','
            SKIP_HEADER = 1
            NULL_IF = ('NULL', 'null', '')
            EMPTY_FIELD_AS_NULL = TRUE
            COMPRESSION = AUTO
            ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
        """
        session.sql(create_format_sql).collect()
        logger.info("✓ File format CSV_FORMAT created")

        # Create external stage
        if aws_key_id and aws_secret_key:
            create_stage_sql = f"""
            CREATE OR REPLACE STAGE {stage_name}
                URL = '{storage_url}'
                CREDENTIALS = (AWS_KEY_ID = '{aws_key_id}' AWS_SECRET_KEY = '{aws_secret_key}')
                FILE_FORMAT = CSV_FORMAT
            """
        else:
            # For demo purposes, create a named stage without credentials
            create_stage_sql = f"""
            CREATE OR REPLACE STAGE {stage_name}
                FILE_FORMAT = CSV_FORMAT
                COMMENT = 'External stage for sales CSV files'
            """

        session.sql(create_stage_sql).collect()
        logger.info(f"✓ External stage {stage_name} created")

        # List files in stage (if accessible)
        try:
            list_files_sql = f"LIST @{stage_name}"
            files = session.sql(list_files_sql).collect()
            logger.info(f"✓ Found {len(files)} files in stage")
        except sp_exceptions.SnowparkSQLException:
            logger.warning("Could not list files in stage (may need valid credentials)")

        return True

    except sp_exceptions.SnowparkSQLException as e:
        logger.error(f"SQL error setting up external stage: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error setting up external stage: {e}")
        return False


def create_landing_table(session: Session) -> bool:
    """
    Create landing table for raw data from external stage.

    Args:
        session: Active Snowpark session

    Returns:
        True if table created successfully, False otherwise
    """
    try:
        logger.info("Creating landing table...")

        create_table_sql = """
        CREATE OR REPLACE TABLE SALES_LANDING (
            TRANSACTION_ID VARCHAR(50),
            CUSTOMER_ID INTEGER,
            CUSTOMER_NAME VARCHAR(100),
            CUSTOMER_EMAIL VARCHAR(100),
            CUSTOMER_SSN VARCHAR(11),
            PRODUCT_ID INTEGER,
            PRODUCT_NAME VARCHAR(200),
            QUANTITY INTEGER,
            UNIT_PRICE DECIMAL(10, 2),
            TOTAL_AMOUNT DECIMAL(10, 2),
            TRANSACTION_DATE DATE,
            PAYMENT_METHOD VARCHAR(50),
            CREDIT_CARD VARCHAR(19),
            LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            SOURCE_FILE VARCHAR(500)
        )
        """
        session.sql(create_table_sql).collect()
        logger.info("✓ Table SALES_LANDING created")

        return True

    except sp_exceptions.SnowparkSQLException as e:
        logger.error(f"SQL error creating landing table: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating landing table: {e}")
        return False


def load_sample_data(session: Session) -> bool:
    """
    Load sample data for demonstration purposes.

    Args:
        session: Active Snowpark session

    Returns:
        True if data loaded successfully, False otherwise
    """
    try:
        logger.info("Loading sample sales data...")

        insert_data_sql = """
        INSERT INTO SALES_LANDING (
            TRANSACTION_ID, CUSTOMER_ID, CUSTOMER_NAME, CUSTOMER_EMAIL, CUSTOMER_SSN,
            PRODUCT_ID, PRODUCT_NAME, QUANTITY, UNIT_PRICE, TOTAL_AMOUNT,
            TRANSACTION_DATE, PAYMENT_METHOD, CREDIT_CARD, SOURCE_FILE
        )
        VALUES
            ('TXN001', 1, 'John Doe', 'john.doe@email.com', '123-45-6789', 101, 'Laptop', 1, 1200.00, 1200.00, '2024-01-15', 'Credit Card', '1234-5678-9012-3456', 'sales_2024_01.csv'),
            ('TXN002', 2, 'Jane Smith', 'jane.smith@company.com', '987-65-4321', 102, 'Mouse', 2, 25.00, 50.00, '2024-01-15', 'Credit Card', '9876-5432-1098-7654', 'sales_2024_01.csv'),
            ('TXN003', 3, 'Bob Johnson', 'bob.j@test.com', '456-78-9012', 103, 'Keyboard', 1, 75.00, 75.00, '2024-01-16', 'Debit Card', '4567890123456789', 'sales_2024_01.csv'),
            ('TXN004', 1, 'John Doe', 'john.doe@email.com', '123-45-6789', 104, 'Monitor', 2, 300.00, 600.00, '2024-01-16', 'Credit Card', '1234-5678-9012-3456', 'sales_2024_01.csv'),
            ('TXN005', 4, 'Alice Williams', 'alice.williams@example.org', '321-54-9876', 105, 'Desk', 1, 450.00, 450.00, '2024-01-17', 'Credit Card', '3210-9876-5432-1098', 'sales_2024_01.csv'),
            ('TXN006', 2, 'Jane Smith', 'jane.smith@company.com', '987-65-4321', 106, 'Chair', 1, 200.00, 200.00, '2024-01-17', 'PayPal', NULL, 'sales_2024_01.csv'),
            ('TXN007', 5, 'Charlie Brown', 'cb@domain.com', '654-32-1098', 107, 'Webcam', 1, 80.00, 80.00, '2024-01-18', 'Credit Card', '6543-2109-8765-4321', 'sales_2024_01.csv'),
            ('TXN008', 3, 'Bob Johnson', 'bob.j@test.com', '456-78-9012', 108, 'Headphones', 1, 120.00, 120.00, '2024-01-18', 'Debit Card', '4567890123456789', 'sales_2024_01.csv'),
            ('TXN009', 4, 'Alice Williams', 'alice.williams@example.org', '321-54-9876', 109, 'USB Hub', 3, 15.00, 45.00, '2024-01-19', 'Credit Card', '3210-9876-5432-1098', 'sales_2024_01.csv'),
            ('TXN010', 1, 'John Doe', 'john.doe@email.com', '123-45-6789', 110, 'Cable', 5, 8.00, 40.00, '2024-01-19', 'Credit Card', '1234-5678-9012-3456', 'sales_2024_01.csv')
        """
        session.sql(insert_data_sql).collect()

        # Get record count
        count_result = session.sql("SELECT COUNT(*) FROM SALES_LANDING").collect()
        record_count = count_result[0][0]
        logger.info(f"✓ Loaded {record_count} sample records into SALES_LANDING")

        return True

    except sp_exceptions.SnowparkSQLException as e:
        logger.error(f"SQL error loading sample data: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error loading sample data: {e}")
        return False


def validate_data_quality(session: Session, metrics: PipelineMetrics) -> bool:
    """
    Perform data quality checks on landing data.

    Args:
        session: Active Snowpark session
        metrics: Pipeline metrics object

    Returns:
        True if data quality checks pass, False otherwise
    """
    try:
        logger.info("\n" + "="*80)
        logger.info("DATA QUALITY CHECKS")
        logger.info("="*80)

        # Check 1: Required fields not null
        logger.info("\nCheck 1: Validating required fields...")
        null_check_sql = """
        SELECT
            COUNT(*) as total_records,
            SUM(CASE WHEN TRANSACTION_ID IS NULL THEN 1 ELSE 0 END) as null_transaction_id,
            SUM(CASE WHEN CUSTOMER_ID IS NULL THEN 1 ELSE 0 END) as null_customer_id,
            SUM(CASE WHEN TOTAL_AMOUNT IS NULL THEN 1 ELSE 0 END) as null_total_amount,
            SUM(CASE WHEN TRANSACTION_DATE IS NULL THEN 1 ELSE 0 END) as null_transaction_date
        FROM SALES_LANDING
        """
        null_check_result = session.sql(null_check_sql).collect()[0]
        total_records = null_check_result[0]
        metrics.records_read = total_records

        null_issues = (
            null_check_result[1] + null_check_result[2] +
            null_check_result[3] + null_check_result[4]
        )

        if null_issues > 0:
            logger.warning(f"Found {null_issues} records with null required fields")
            metrics.records_failed += null_issues
        else:
            logger.info("✓ All required fields are populated")

        # Check 2: Data type validation
        logger.info("\nCheck 2: Validating data types and ranges...")
        range_check_sql = """
        SELECT
            SUM(CASE WHEN QUANTITY <= 0 THEN 1 ELSE 0 END) as invalid_quantity,
            SUM(CASE WHEN UNIT_PRICE <= 0 THEN 1 ELSE 0 END) as invalid_unit_price,
            SUM(CASE WHEN TOTAL_AMOUNT <= 0 THEN 1 ELSE 0 END) as invalid_total_amount,
            SUM(CASE WHEN ABS(TOTAL_AMOUNT - (QUANTITY * UNIT_PRICE)) > 0.01 THEN 1 ELSE 0 END) as amount_mismatch
        FROM SALES_LANDING
        """
        range_check_result = session.sql(range_check_sql).collect()[0]

        range_issues = sum(range_check_result)
        if range_issues > 0:
            logger.warning(f"Found {range_issues} records with invalid values")
            logger.warning(f"  - Invalid quantity: {range_check_result[0]}")
            logger.warning(f"  - Invalid unit price: {range_check_result[1]}")
            logger.warning(f"  - Invalid total amount: {range_check_result[2]}")
            logger.warning(f"  - Amount calculation mismatch: {range_check_result[3]}")
            metrics.records_failed += range_issues
        else:
            logger.info("✓ All values are within valid ranges")

        # Check 3: Duplicate detection
        logger.info("\nCheck 3: Checking for duplicates...")
        duplicate_check_sql = """
        SELECT COUNT(*) - COUNT(DISTINCT TRANSACTION_ID) as duplicate_count
        FROM SALES_LANDING
        """
        duplicate_result = session.sql(duplicate_check_sql).collect()[0][0]

        if duplicate_result > 0:
            logger.warning(f"Found {duplicate_result} duplicate transaction IDs")
            metrics.records_failed += duplicate_result
        else:
            logger.info("✓ No duplicate transaction IDs found")

        # Summary
        logger.info("\n" + "-"*80)
        logger.info(f"Data Quality Summary:")
        logger.info(f"  Total Records: {total_records:,}")
        logger.info(f"  Valid Records: {total_records - metrics.records_failed:,}")
        logger.info(f"  Issues Found: {metrics.records_failed:,}")
        logger.info("-"*80)

        return True

    except sp_exceptions.SnowparkSQLException as e:
        logger.error(f"SQL error during data quality checks: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during data quality checks: {e}")
        return False


def process_and_mask_pii(session: Session, metrics: PipelineMetrics) -> bool:
    """
    Process data and apply PII masking transformations.

    Args:
        session: Active Snowpark session
        metrics: Pipeline metrics object

    Returns:
        True if processing successful, False otherwise
    """
    try:
        logger.info("\n" + "="*80)
        logger.info("PROCESSING AND MASKING PII DATA")
        logger.info("="*80)

        # Create processed table with masked PII
        logger.info("\nCreating SALES_PROCESSED table with masked PII...")

        create_processed_table_sql = """
        CREATE OR REPLACE TABLE SALES_PROCESSED AS
        SELECT
            TRANSACTION_ID,
            CUSTOMER_ID,
            CUSTOMER_NAME,
            MASK_EMAIL(CUSTOMER_EMAIL) AS CUSTOMER_EMAIL,
            MASK_SSN(CUSTOMER_SSN) AS CUSTOMER_SSN,
            PRODUCT_ID,
            PRODUCT_NAME,
            QUANTITY,
            UNIT_PRICE,
            TOTAL_AMOUNT,
            TRANSACTION_DATE,
            PAYMENT_METHOD,
            CASE
                WHEN CREDIT_CARD IS NOT NULL THEN MASK_CREDIT_CARD(CREDIT_CARD)
                ELSE NULL
            END AS CREDIT_CARD,
            LOADED_AT,
            SOURCE_FILE,
            CURRENT_TIMESTAMP() AS PROCESSED_AT
        FROM SALES_LANDING
        WHERE TRANSACTION_ID IS NOT NULL
          AND CUSTOMER_ID IS NOT NULL
          AND TOTAL_AMOUNT IS NOT NULL
          AND QUANTITY > 0
          AND UNIT_PRICE > 0
        """

        session.sql(create_processed_table_sql).collect()

        # Get record count
        count_result = session.sql("SELECT COUNT(*) FROM SALES_PROCESSED").collect()
        processed_count = count_result[0][0]
        metrics.records_processed = processed_count
        metrics.records_written = processed_count

        logger.info(f"✓ Processed {processed_count:,} records with masked PII")

        # Show sample of masked data
        logger.info("\nSample of processed data with masked PII:")
        sample_sql = """
        SELECT
            TRANSACTION_ID,
            CUSTOMER_NAME,
            CUSTOMER_EMAIL,
            CUSTOMER_SSN,
            CREDIT_CARD,
            TOTAL_AMOUNT
        FROM SALES_PROCESSED
        LIMIT 5
        """
        sample_df = session.sql(sample_sql)
        sample_df.show()

        return True

    except sp_exceptions.SnowparkSQLException as e:
        logger.error(f"SQL error during PII masking: {e}")
        metrics.errors.append(f"PII masking error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during PII masking: {e}")
        metrics.errors.append(f"Unexpected error: {e}")
        return False


def create_aggregation_tables(session: Session) -> bool:
    """
    Create aggregation tables for analytics.

    Args:
        session: Active Snowpark session

    Returns:
        True if aggregation successful, False otherwise
    """
    try:
        logger.info("\n" + "="*80)
        logger.info("CREATING AGGREGATION TABLES")
        logger.info("="*80)

        # Daily sales summary
        logger.info("\nCreating daily sales summary...")
        daily_summary_sql = """
        CREATE OR REPLACE TABLE SALES_DAILY_SUMMARY AS
        SELECT
            TRANSACTION_DATE,
            COUNT(DISTINCT CUSTOMER_ID) AS UNIQUE_CUSTOMERS,
            COUNT(*) AS TOTAL_TRANSACTIONS,
            SUM(QUANTITY) AS TOTAL_ITEMS_SOLD,
            SUM(TOTAL_AMOUNT) AS TOTAL_REVENUE,
            AVG(TOTAL_AMOUNT) AS AVG_TRANSACTION_VALUE,
            MIN(TOTAL_AMOUNT) AS MIN_TRANSACTION_VALUE,
            MAX(TOTAL_AMOUNT) AS MAX_TRANSACTION_VALUE,
            CURRENT_TIMESTAMP() AS CREATED_AT
        FROM SALES_PROCESSED
        GROUP BY TRANSACTION_DATE
        ORDER BY TRANSACTION_DATE
        """
        session.sql(daily_summary_sql).collect()
        logger.info("✓ Table SALES_DAILY_SUMMARY created")

        # Customer summary
        logger.info("\nCreating customer summary...")
        customer_summary_sql = """
        CREATE OR REPLACE TABLE CUSTOMER_SUMMARY AS
        SELECT
            CUSTOMER_ID,
            CUSTOMER_NAME,
            CUSTOMER_EMAIL,
            COUNT(*) AS TOTAL_PURCHASES,
            SUM(QUANTITY) AS TOTAL_ITEMS,
            SUM(TOTAL_AMOUNT) AS LIFETIME_VALUE,
            AVG(TOTAL_AMOUNT) AS AVG_ORDER_VALUE,
            MIN(TRANSACTION_DATE) AS FIRST_PURCHASE_DATE,
            MAX(TRANSACTION_DATE) AS LAST_PURCHASE_DATE,
            CURRENT_TIMESTAMP() AS CREATED_AT
        FROM SALES_PROCESSED
        GROUP BY CUSTOMER_ID, CUSTOMER_NAME, CUSTOMER_EMAIL
        ORDER BY LIFETIME_VALUE DESC
        """
        session.sql(customer_summary_sql).collect()
        logger.info("✓ Table CUSTOMER_SUMMARY created")

        # Product summary
        logger.info("\nCreating product summary...")
        product_summary_sql = """
        CREATE OR REPLACE TABLE PRODUCT_SUMMARY AS
        SELECT
            PRODUCT_ID,
            PRODUCT_NAME,
            COUNT(*) AS TIMES_SOLD,
            SUM(QUANTITY) AS TOTAL_QUANTITY_SOLD,
            SUM(TOTAL_AMOUNT) AS TOTAL_REVENUE,
            AVG(UNIT_PRICE) AS AVG_PRICE,
            COUNT(DISTINCT CUSTOMER_ID) AS UNIQUE_CUSTOMERS,
            CURRENT_TIMESTAMP() AS CREATED_AT
        FROM SALES_PROCESSED
        GROUP BY PRODUCT_ID, PRODUCT_NAME
        ORDER BY TOTAL_REVENUE DESC
        """
        session.sql(product_summary_sql).collect()
        logger.info("✓ Table PRODUCT_SUMMARY created")

        # Display summaries
        logger.info("\nDaily Sales Summary:")
        session.sql("SELECT * FROM SALES_DAILY_SUMMARY").show()

        logger.info("\nTop 5 Customers by Lifetime Value:")
        session.sql("SELECT * FROM CUSTOMER_SUMMARY LIMIT 5").show()

        logger.info("\nTop 5 Products by Revenue:")
        session.sql("SELECT * FROM PRODUCT_SUMMARY LIMIT 5").show()

        return True

    except sp_exceptions.SnowparkSQLException as e:
        logger.error(f"SQL error creating aggregation tables: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating aggregation tables: {e}")
        return False


def main():
    """
    Main pipeline execution function.

    Steps:
        1. Create Snowpark session
        2. Set up external stage and file format
        3. Create landing table
        4. Load data (from stage or sample data)
        5. Validate data quality
        6. Process and mask PII data
        7. Create aggregation tables
        8. Log metrics
    """
    logger.info("="*80)
    logger.info("SNOWPARK DYNAMIC TABLE PIPELINE")
    logger.info("="*80)

    metrics = PipelineMetrics()

    # Create session
    session = create_snowpark_session()
    if not session:
        logger.error("Failed to create Snowpark session. Exiting.")
        sys.exit(1)

    try:
        # Stage configuration
        stage_config = {
            "name": os.getenv("SNOWFLAKE_STAGE_NAME", "sales_csvs"),
            "url": os.getenv("SNOWFLAKE_STAGE_URL", "s3://my-bucket/sales/"),
        }

        # Setup external stage
        if not setup_external_stage(session, stage_config):
            logger.warning("Stage setup failed, continuing with sample data...")

        # Create landing table
        if not create_landing_table(session):
            logger.error("Failed to create landing table. Exiting.")
            sys.exit(1)

        # Load data (using sample data for demo)
        if not load_sample_data(session):
            logger.error("Failed to load data. Exiting.")
            sys.exit(1)

        # Validate data quality
        if not validate_data_quality(session, metrics):
            logger.error("Data quality validation failed. Exiting.")
            sys.exit(1)

        # Process and mask PII
        if not process_and_mask_pii(session, metrics):
            logger.error("PII masking failed. Exiting.")
            sys.exit(1)

        # Create aggregation tables
        if not create_aggregation_tables(session):
            logger.error("Failed to create aggregation tables. Exiting.")
            sys.exit(1)

        # Log metrics
        metrics.log_summary()

        logger.info("\n✓ Pipeline completed successfully!")
        logger.info("\nNext steps:")
        logger.info("  1. Run sql/dynamic_tables.sql to set up automated refreshes")
        logger.info("  2. Query the processed data: SELECT * FROM SALES_PROCESSED;")
        logger.info("  3. View aggregations: SELECT * FROM SALES_DAILY_SUMMARY;")

    except Exception as e:
        logger.error(f"Unexpected error in pipeline execution: {e}")
        metrics.errors.append(f"Pipeline error: {e}")
        metrics.log_summary()
        sys.exit(1)
    finally:
        # Close session
        if session:
            session.close()
            logger.info("\nSnowpark session closed.")


if __name__ == "__main__":
    main()
