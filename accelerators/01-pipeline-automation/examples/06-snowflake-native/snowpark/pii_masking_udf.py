"""
Snowpark Python UDFs for PII Masking

This module demonstrates production-ready PII masking using Snowflake Snowpark UDFs.
It creates and registers User-Defined Functions for masking sensitive data like
email addresses, SSNs, and credit card numbers.

Features:
- Email masking (preserves first 2 chars and domain)
- SSN masking (shows only last 4 digits)
- Credit card masking (shows only last 4 digits)
- Production error handling
- Session management
- UDF registration in Snowflake

Prerequisites:
- Snowflake account with Snowpark enabled
- Python 3.8+
- snowflake-snowpark-python library

Usage:
    python pii_masking_udf.py
"""

import os
import sys
import logging
from typing import Optional
from snowflake.snowpark import Session
from snowflake.snowpark.functions import udf, col
from snowflake.snowpark.types import StringType
import snowflake.snowpark.exceptions as sp_exceptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_snowpark_session() -> Optional[Session]:
    """
    Create a Snowpark session with connection parameters from environment variables.

    Required environment variables:
        SNOWFLAKE_ACCOUNT: Snowflake account identifier (e.g., xy12345)
        SNOWFLAKE_USER: Username for authentication
        SNOWFLAKE_PASSWORD: Password for authentication
        SNOWFLAKE_WAREHOUSE: Warehouse name (default: COMPUTE_WH)
        SNOWFLAKE_DATABASE: Database name (default: ANALYTICS)
        SNOWFLAKE_SCHEMA: Schema name (default: PUBLIC)
        SNOWFLAKE_ROLE: Role name (default: SYSADMIN)

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
            logger.error("Please set the following environment variables:")
            for param in missing_params:
                logger.error(f"  - SNOWFLAKE_{param.upper()}")
            return None

        logger.info(f"Connecting to Snowflake account: {connection_parameters['account']}")
        logger.info(f"Database: {connection_parameters['database']}, Schema: {connection_parameters['schema']}")

        session = Session.builder.configs(connection_parameters).create()

        # Test connection
        result = session.sql("SELECT CURRENT_VERSION()").collect()
        logger.info(f"Successfully connected to Snowflake version: {result[0][0]}")

        return session

    except sp_exceptions.SnowparkSessionException as e:
        logger.error(f"Failed to create Snowpark session: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating Snowpark session: {e}")
        return None


def mask_email_func(email: str) -> str:
    """
    Mask email address, preserving first 2 characters and domain.

    Examples:
        john.doe@company.com -> jo********@company.com
        a@test.com -> a*@test.com
        invalid -> invalid (no @ symbol)

    Args:
        email: Email address to mask

    Returns:
        Masked email address
    """
    if not email or '@' not in email:
        return email

    try:
        local, domain = email.split('@', 1)

        if len(local) <= 2:
            masked_local = local[0] + '*'
        else:
            masked_local = local[:2] + '*' * (len(local) - 2)

        return f"{masked_local}@{domain}"
    except Exception:
        return email


def mask_ssn_func(ssn: str) -> str:
    """
    Mask SSN, showing only last 4 digits.

    Handles formats:
        - 123-45-6789 -> XXX-XX-6789
        - 123456789 -> XXXXX6789

    Args:
        ssn: SSN to mask

    Returns:
        Masked SSN
    """
    if not ssn:
        return ssn

    try:
        # Remove all non-digit characters to get the raw SSN
        digits = ''.join(c for c in ssn if c.isdigit())

        if len(digits) != 9:
            return ssn  # Invalid SSN, return as-is

        # Check if original had dashes
        if '-' in ssn:
            return f"XXX-XX-{digits[-4:]}"
        else:
            return f"XXXXX{digits[-4:]}"
    except Exception:
        return ssn


def mask_credit_card_func(cc: str) -> str:
    """
    Mask credit card number, showing only last 4 digits.

    Handles formats:
        - 1234567890123456 -> ************3456
        - 1234-5678-9012-3456 -> ****-****-****-3456
        - 1234 5678 9012 3456 -> **** **** **** 3456

    Args:
        cc: Credit card number to mask

    Returns:
        Masked credit card number
    """
    if not cc:
        return cc

    try:
        # Extract digits and separators
        digits = ''.join(c for c in cc if c.isdigit())

        if len(digits) < 4:
            return '*' * len(cc)

        # Determine separator (dash, space, or none)
        separator = ''
        if '-' in cc:
            separator = '-'
        elif ' ' in cc:
            separator = ' '

        # Get last 4 digits
        last_four = digits[-4:]

        if separator:
            # Preserve original format
            if separator == '-':
                return f"****{separator}****{separator}****{separator}{last_four}"
            else:  # space
                return f"**** **** **** {last_four}"
        else:
            # No separator
            return '*' * (len(digits) - 4) + last_four
    except Exception:
        return cc


def register_udfs(session: Session) -> bool:
    """
    Register PII masking UDFs in Snowflake.

    Creates permanent UDFs in the current schema that can be used in SQL queries.

    Args:
        session: Active Snowpark session

    Returns:
        True if registration successful, False otherwise
    """
    try:
        logger.info("Registering PII masking UDFs...")

        # Register email masking UDF
        session.udf.register(
            func=mask_email_func,
            name="MASK_EMAIL",
            replace=True,
            is_permanent=True,
            stage_location="@~/udf_stage",
            return_type=StringType(),
            input_types=[StringType()],
        )
        logger.info("✓ Registered MASK_EMAIL UDF")

        # Register SSN masking UDF
        session.udf.register(
            func=mask_ssn_func,
            name="MASK_SSN",
            replace=True,
            is_permanent=True,
            stage_location="@~/udf_stage",
            return_type=StringType(),
            input_types=[StringType()],
        )
        logger.info("✓ Registered MASK_SSN UDF")

        # Register credit card masking UDF
        session.udf.register(
            func=mask_credit_card_func,
            name="MASK_CREDIT_CARD",
            replace=True,
            is_permanent=True,
            stage_location="@~/udf_stage",
            return_type=StringType(),
            input_types=[StringType()],
        )
        logger.info("✓ Registered MASK_CREDIT_CARD UDF")

        logger.info("All UDFs registered successfully!")
        return True

    except sp_exceptions.SnowparkSQLException as e:
        logger.error(f"SQL error registering UDFs: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error registering UDFs: {e}")
        return False


def create_sample_table(session: Session) -> bool:
    """
    Create a sample table with PII data for demonstration.

    Args:
        session: Active Snowpark session

    Returns:
        True if table created successfully, False otherwise
    """
    try:
        logger.info("Creating sample table with PII data...")

        # Create sample table
        create_table_sql = """
        CREATE OR REPLACE TABLE CUSTOMER_PII (
            CUSTOMER_ID INTEGER,
            NAME VARCHAR(100),
            EMAIL VARCHAR(100),
            SSN VARCHAR(11),
            CREDIT_CARD VARCHAR(19),
            PHONE VARCHAR(15),
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        session.sql(create_table_sql).collect()

        # Insert sample data
        insert_data_sql = """
        INSERT INTO CUSTOMER_PII (CUSTOMER_ID, NAME, EMAIL, SSN, CREDIT_CARD, PHONE)
        VALUES
            (1, 'John Doe', 'john.doe@email.com', '123-45-6789', '1234-5678-9012-3456', '555-123-4567'),
            (2, 'Jane Smith', 'jane.smith@company.com', '987-65-4321', '9876-5432-1098-7654', '555-987-6543'),
            (3, 'Bob Johnson', 'bob.j@test.com', '456-78-9012', '4567890123456789', '555-456-7890'),
            (4, 'Alice Williams', 'alice.williams@example.org', '321-54-9876', '3210 9876 5432 1098', '555-321-0987'),
            (5, 'Charlie Brown', 'cb@domain.com', '654-32-1098', '6543-2109-8765-4321', '555-654-3210')
        """
        session.sql(insert_data_sql).collect()

        logger.info("✓ Sample table created with 5 records")
        return True

    except sp_exceptions.SnowparkSQLException as e:
        logger.error(f"SQL error creating sample table: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating sample table: {e}")
        return False


def demonstrate_masking(session: Session) -> bool:
    """
    Demonstrate PII masking UDFs on sample data.

    Args:
        session: Active Snowpark session

    Returns:
        True if demonstration successful, False otherwise
    """
    try:
        logger.info("\n" + "="*80)
        logger.info("DEMONSTRATING PII MASKING")
        logger.info("="*80)

        # Show original data
        logger.info("\nOriginal Data (BEFORE masking):")
        original_query = """
        SELECT CUSTOMER_ID, NAME, EMAIL, SSN, CREDIT_CARD, PHONE
        FROM CUSTOMER_PII
        ORDER BY CUSTOMER_ID
        """
        original_df = session.sql(original_query)
        original_df.show()

        # Show masked data
        logger.info("\nMasked Data (AFTER applying UDFs):")
        masked_query = """
        SELECT
            CUSTOMER_ID,
            NAME,
            MASK_EMAIL(EMAIL) AS MASKED_EMAIL,
            MASK_SSN(SSN) AS MASKED_SSN,
            MASK_CREDIT_CARD(CREDIT_CARD) AS MASKED_CREDIT_CARD,
            PHONE
        FROM CUSTOMER_PII
        ORDER BY CUSTOMER_ID
        """
        masked_df = session.sql(masked_query)
        masked_df.show()

        # Create masked view for analytics
        logger.info("\nCreating CUSTOMER_PII_MASKED view for analytics...")
        create_view_sql = """
        CREATE OR REPLACE VIEW CUSTOMER_PII_MASKED AS
        SELECT
            CUSTOMER_ID,
            NAME,
            MASK_EMAIL(EMAIL) AS EMAIL,
            MASK_SSN(SSN) AS SSN,
            MASK_CREDIT_CARD(CREDIT_CARD) AS CREDIT_CARD,
            PHONE,
            CREATED_AT
        FROM CUSTOMER_PII
        """
        session.sql(create_view_sql).collect()
        logger.info("✓ View CUSTOMER_PII_MASKED created successfully")

        logger.info("\n" + "="*80)
        logger.info("DEMONSTRATION COMPLETE")
        logger.info("="*80)
        logger.info("\nYou can now query the masked view:")
        logger.info("  SELECT * FROM CUSTOMER_PII_MASKED;")
        logger.info("\nOr use the UDFs in your own queries:")
        logger.info("  SELECT MASK_EMAIL('test@example.com');")
        logger.info("  SELECT MASK_SSN('123-45-6789');")
        logger.info("  SELECT MASK_CREDIT_CARD('1234-5678-9012-3456');")

        return True

    except sp_exceptions.SnowparkSQLException as e:
        logger.error(f"SQL error during demonstration: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during demonstration: {e}")
        return False


def main():
    """
    Main execution function.

    Steps:
        1. Create Snowpark session
        2. Register PII masking UDFs
        3. Create sample table with PII data
        4. Demonstrate masking functionality
    """
    logger.info("="*80)
    logger.info("SNOWPARK PII MASKING UDF DEMO")
    logger.info("="*80)

    # Create session
    session = create_snowpark_session()
    if not session:
        logger.error("Failed to create Snowpark session. Exiting.")
        sys.exit(1)

    try:
        # Register UDFs
        if not register_udfs(session):
            logger.error("Failed to register UDFs. Exiting.")
            sys.exit(1)

        # Create sample table
        if not create_sample_table(session):
            logger.error("Failed to create sample table. Exiting.")
            sys.exit(1)

        # Demonstrate masking
        if not demonstrate_masking(session):
            logger.error("Failed to demonstrate masking. Exiting.")
            sys.exit(1)

        logger.info("\n✓ All operations completed successfully!")

    except Exception as e:
        logger.error(f"Unexpected error in main execution: {e}")
        sys.exit(1)
    finally:
        # Close session
        if session:
            session.close()
            logger.info("\nSnowpark session closed.")


if __name__ == "__main__":
    main()
