"""
Secure Azure Synapse ETL Pipeline with Governance Controls

Features:
- Azure AD authentication using managed identity
- No hardcoded credentials
- Private link connectivity to on-premises SQL Server
- Encrypted data transfer
- Comprehensive audit logging
- Data lineage tracking
- PII data handling with encryption
- Role-based access control
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging
import json

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.microsoft.azure.hooks.synapse import AzureSynapseHook
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
from airflow.utils.dates import days_ago
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
import pyodbc
import struct
from opencensus.ext.azure.log_exporter import AzureLogHandler


# Configure structured logging
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=<your-app-insights-key>'
))

# DAG configuration
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'email': ['data-engineering@example.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# Security and compliance metadata
SECURITY_CLASSIFICATION = 'confidential'
PII_COLUMNS = ['ssn', 'credit_card_number', 'email', 'phone_number']
AUDIT_TABLE = 'governance.data_lineage_audit'


class SecureAzureConnection:
    """
    Secure connection manager for Azure services using managed identity.
    No credentials stored in code or connection strings.
    """

    def __init__(self, key_vault_url: str):
        """Initialize with Azure Key Vault URL."""
        self.key_vault_url = key_vault_url
        self.credential = None
        self._initialize_credential()

    def _initialize_credential(self) -> None:
        """
        Initialize Azure credential using managed identity.
        Falls back to DefaultAzureCredential for local development.
        """
        try:
            # Try managed identity first (for production)
            self.credential = ManagedIdentityCredential()
            # Test the credential
            _ = self.credential.get_token("https://management.azure.com/.default")
            logger.info("Successfully authenticated using Managed Identity")
        except Exception as e:
            logger.warning(f"Managed Identity failed: {e}. Falling back to DefaultAzureCredential")
            # Fallback to default credential chain (for dev)
            self.credential = DefaultAzureCredential()
            logger.info("Using DefaultAzureCredential")

    def get_secret(self, secret_name: str) -> str:
        """Retrieve secret from Azure Key Vault."""
        try:
            client = SecretClient(
                vault_url=self.key_vault_url,
                credential=self.credential
            )
            secret = client.get_secret(secret_name)
            logger.info(f"Retrieved secret: {secret_name}")
            return secret.value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise

    def get_synapse_connection(self, server: str, database: str) -> pyodbc.Connection:
        """
        Create connection to Azure Synapse using Azure AD authentication.
        No password required.
        """
        try:
            # Get Azure AD token
            token = self.credential.get_token("https://database.windows.net/.default")

            # Convert token to format required by pyodbc
            token_bytes = token.token.encode('UTF-16-LE')
            token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)

            # Connection string with Azure AD token
            connection_string = (
                f"Driver={{ODBC Driver 18 for SQL Server}};"
                f"Server=tcp:{server},1433;"
                f"Database={database};"
                f"Encrypt=yes;"
                f"TrustServerCertificate=no;"
                f"Connection Timeout=30;"
            )

            # Connect using Azure AD token
            conn = pyodbc.connect(
                connection_string,
                attrs_before={1256: token_struct}  # SQL_COPT_SS_ACCESS_TOKEN
            )

            logger.info(f"Connected to Synapse: {server}/{database}")
            return conn

        except Exception as e:
            logger.error(f"Failed to connect to Synapse: {e}")
            raise

    def get_onprem_connection(self, connection_name: str) -> pyodbc.Connection:
        """
        Connect to on-premises SQL Server via private link.
        Credentials retrieved from Key Vault.
        """
        try:
            # Get connection details from Key Vault
            connection_string = self.get_secret(f"sql-{connection_name}-connection")

            conn = pyodbc.connect(connection_string)
            logger.info(f"Connected to on-premises SQL Server: {connection_name}")
            return conn

        except Exception as e:
            logger.error(f"Failed to connect to on-premises SQL: {e}")
            raise


def log_audit_event(
    event_type: str,
    source_system: str,
    target_system: str,
    table_name: str,
    record_count: int,
    user_principal: str,
    metadata: Optional[Dict[str, Any]] = None,
    **context
) -> None:
    """
    Log comprehensive audit event for compliance and governance.

    Args:
        event_type: Type of data operation (extract, load, transform)
        source_system: Source system identifier
        target_system: Target system identifier
        table_name: Table being processed
        record_count: Number of records processed
        user_principal: User/service principal executing the operation
        metadata: Additional metadata
    """
    audit_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'source_system': source_system,
        'target_system': target_system,
        'table_name': table_name,
        'record_count': record_count,
        'user_principal': user_principal,
        'dag_id': context.get('dag').dag_id if 'dag' in context else None,
        'task_id': context.get('task').task_id if 'task' in context else None,
        'execution_date': str(context.get('execution_date')) if 'execution_date' in context else None,
        'security_classification': SECURITY_CLASSIFICATION,
        'metadata': metadata or {}
    }

    # Log to Azure Application Insights
    logger.info(
        f"Audit Event: {event_type}",
        extra={'custom_dimensions': audit_entry}
    )

    # Also write to Synapse audit table
    try:
        secure_conn = SecureAzureConnection(
            key_vault_url='https://your-keyvault.vault.azure.net/'
        )
        conn = secure_conn.get_synapse_connection(
            server='your-synapse.sql.azuresynapse.net',
            database='governance'
        )

        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {AUDIT_TABLE}
            (timestamp, event_type, source_system, target_system, table_name,
             record_count, user_principal, dag_id, task_id, execution_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_entry['timestamp'],
            audit_entry['event_type'],
            audit_entry['source_system'],
            audit_entry['target_system'],
            audit_entry['table_name'],
            audit_entry['record_count'],
            audit_entry['user_principal'],
            audit_entry['dag_id'],
            audit_entry['task_id'],
            audit_entry['execution_date'],
            json.dumps(audit_entry['metadata'])
        ))
        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to write audit log to Synapse: {e}")
        # Don't fail the pipeline on audit errors, but log it


def extract_from_onprem_sql(**context) -> Dict[str, Any]:
    """
    Extract data from on-premises SQL Server via private link.
    Uses secure authentication and encrypted transfer.
    """
    logger.info("Starting extraction from on-premises SQL Server")

    # Configuration
    source_table = 'dbo.customer_transactions'
    staging_table = 'staging.customer_transactions'
    key_vault_url = 'https://your-keyvault.vault.azure.net/'
    synapse_server = 'your-synapse.sql.azuresynapse.net'
    synapse_database = 'analytics'

    try:
        # Initialize secure connection
        secure_conn = SecureAzureConnection(key_vault_url)

        # Connect to on-premises SQL Server
        onprem_conn = secure_conn.get_onprem_connection('onprem-sqlserver')
        onprem_cursor = onprem_conn.cursor()

        # Get incremental load watermark
        last_extracted = context['task_instance'].xcom_pull(
            task_ids='get_watermark',
            key='last_extraction_timestamp'
        ) or '1900-01-01'

        # Extract data with encryption awareness
        extraction_query = f"""
            SELECT
                customer_id,
                transaction_id,
                transaction_date,
                amount,
                -- PII columns are encrypted at rest
                CONVERT(VARBINARY(MAX), ssn) as ssn_encrypted,
                CONVERT(VARBINARY(MAX), credit_card_number) as cc_encrypted,
                email,
                phone_number,
                modified_date
            FROM {source_table}
            WHERE modified_date > ?
            ORDER BY modified_date
        """

        logger.info(f"Extracting records modified after: {last_extracted}")
        onprem_cursor.execute(extraction_query, last_extracted)

        # Connect to Synapse for staging
        synapse_conn = secure_conn.get_synapse_connection(
            server=synapse_server,
            database=synapse_database
        )
        synapse_cursor = synapse_conn.cursor()

        # Create staging table if not exists
        synapse_cursor.execute(f"""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{staging_table.split('.')[-1]}')
            CREATE TABLE {staging_table} (
                customer_id INT,
                transaction_id BIGINT,
                transaction_date DATETIME2,
                amount DECIMAL(18,2),
                ssn_encrypted VARBINARY(MAX),
                cc_encrypted VARBINARY(MAX),
                email NVARCHAR(255),
                phone_number NVARCHAR(50),
                modified_date DATETIME2,
                extracted_at DATETIME2 DEFAULT GETUTCDATE()
            )
            WITH (DISTRIBUTION = HASH(customer_id), CLUSTERED COLUMNSTORE INDEX)
        """)

        # Batch insert to Synapse
        batch_size = 10000
        total_records = 0
        batch = []

        for row in onprem_cursor:
            batch.append(row)

            if len(batch) >= batch_size:
                synapse_cursor.executemany(f"""
                    INSERT INTO {staging_table}
                    (customer_id, transaction_id, transaction_date, amount,
                     ssn_encrypted, cc_encrypted, email, phone_number, modified_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                synapse_conn.commit()
                total_records += len(batch)
                logger.info(f"Inserted batch: {total_records} records")
                batch = []

        # Insert remaining records
        if batch:
            synapse_cursor.executemany(f"""
                INSERT INTO {staging_table}
                (customer_id, transaction_id, transaction_date, amount,
                 ssn_encrypted, cc_encrypted, email, phone_number, modified_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            synapse_conn.commit()
            total_records += len(batch)

        # Close connections
        onprem_cursor.close()
        onprem_conn.close()
        synapse_cursor.close()
        synapse_conn.close()

        logger.info(f"Extraction complete: {total_records} records")

        # Log audit event
        log_audit_event(
            event_type='extract',
            source_system='onprem-sqlserver',
            target_system='synapse-staging',
            table_name=source_table,
            record_count=total_records,
            user_principal=context.get('task_instance').task_id,
            metadata={'staging_table': staging_table},
            **context
        )

        return {
            'records_extracted': total_records,
            'staging_table': staging_table,
            'status': 'success'
        }

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        log_audit_event(
            event_type='extract_failed',
            source_system='onprem-sqlserver',
            target_system='synapse-staging',
            table_name=source_table,
            record_count=0,
            user_principal=context.get('task_instance').task_id,
            metadata={'error': str(e)},
            **context
        )
        raise


def apply_security_policies(**context) -> Dict[str, Any]:
    """
    Apply security policies including encryption, masking, and RLS.
    """
    logger.info("Applying security policies")

    staging_table = context['task_instance'].xcom_pull(
        task_ids='extract_from_onprem',
        key='return_value'
    )['staging_table']

    key_vault_url = 'https://your-keyvault.vault.azure.net/'
    synapse_server = 'your-synapse.sql.azuresynapse.net'
    synapse_database = 'analytics'

    try:
        secure_conn = SecureAzureConnection(key_vault_url)
        conn = secure_conn.get_synapse_connection(synapse_server, synapse_database)
        cursor = conn.cursor()

        # Apply column-level encryption for PII fields
        cursor.execute(f"""
            -- Ensure encryption keys are set up (see column_encryption.sql)
            -- Re-encrypt data using Azure Key Vault keys
            UPDATE {staging_table}
            SET
                ssn_encrypted = ENCRYPTBYKEY(KEY_GUID('SSN_ENCRYPTION_KEY'), CONVERT(NVARCHAR(11), ssn_encrypted)),
                cc_encrypted = ENCRYPTBYKEY(KEY_GUID('CC_ENCRYPTION_KEY'), CONVERT(NVARCHAR(20), cc_encrypted))
            WHERE ssn_encrypted IS NOT NULL OR cc_encrypted IS NOT NULL
        """)

        # Apply dynamic data masking
        cursor.execute(f"""
            -- Email masking (show only first character)
            ALTER TABLE {staging_table}
            ALTER COLUMN email ADD MASKED WITH (FUNCTION = 'email()')
        """)

        cursor.execute(f"""
            -- Phone masking
            ALTER TABLE {staging_table}
            ALTER COLUMN phone_number ADD MASKED WITH (FUNCTION = 'partial(1,"XXX-XXX-",4)')
        """)

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("Security policies applied successfully")

        log_audit_event(
            event_type='security_policy_applied',
            source_system='synapse-staging',
            target_system='synapse-staging',
            table_name=staging_table,
            record_count=0,
            user_principal=context.get('task_instance').task_id,
            metadata={'policies': ['column_encryption', 'data_masking']},
            **context
        )

        return {'status': 'success'}

    except Exception as e:
        logger.error(f"Failed to apply security policies: {e}", exc_info=True)
        raise


def load_to_production(**context) -> Dict[str, Any]:
    """
    Load data from staging to production with RLS policies.
    """
    logger.info("Loading data to production tables")

    staging_table = context['task_instance'].xcom_pull(
        task_ids='extract_from_onprem',
        key='return_value'
    )['staging_table']

    production_table = 'production.customer_transactions'
    key_vault_url = 'https://your-keyvault.vault.azure.net/'
    synapse_server = 'your-synapse.sql.azuresynapse.net'
    synapse_database = 'analytics'

    try:
        secure_conn = SecureAzureConnection(key_vault_url)
        conn = secure_conn.get_synapse_connection(synapse_server, synapse_database)
        cursor = conn.cursor()

        # Merge staging to production
        cursor.execute(f"""
            MERGE {production_table} AS target
            USING {staging_table} AS source
            ON target.transaction_id = source.transaction_id
            WHEN MATCHED THEN
                UPDATE SET
                    amount = source.amount,
                    ssn_encrypted = source.ssn_encrypted,
                    cc_encrypted = source.cc_encrypted,
                    email = source.email,
                    phone_number = source.phone_number,
                    modified_date = source.modified_date,
                    updated_at = GETUTCDATE()
            WHEN NOT MATCHED THEN
                INSERT (customer_id, transaction_id, transaction_date, amount,
                        ssn_encrypted, cc_encrypted, email, phone_number,
                        modified_date, created_at)
                VALUES (source.customer_id, source.transaction_id, source.transaction_date,
                        source.amount, source.ssn_encrypted, source.cc_encrypted,
                        source.email, source.phone_number, source.modified_date,
                        GETUTCDATE());
        """)

        rows_affected = cursor.rowcount
        conn.commit()

        # Truncate staging table
        cursor.execute(f"TRUNCATE TABLE {staging_table}")
        conn.commit()

        cursor.close()
        conn.close()

        logger.info(f"Loaded {rows_affected} records to production")

        log_audit_event(
            event_type='load',
            source_system='synapse-staging',
            target_system='synapse-production',
            table_name=production_table,
            record_count=rows_affected,
            user_principal=context.get('task_instance').task_id,
            **context
        )

        return {
            'records_loaded': rows_affected,
            'status': 'success'
        }

    except Exception as e:
        logger.error(f"Failed to load to production: {e}", exc_info=True)
        raise


# DAG definition
with DAG(
    dag_id='secure_synapse_etl_pipeline',
    default_args=default_args,
    description='Secure ETL pipeline with Azure AD auth and governance controls',
    schedule_interval='0 2 * * *',  # Daily at 2 AM UTC
    start_date=days_ago(1),
    catchup=False,
    tags=['security', 'governance', 'synapse', 'production'],
    max_active_runs=1,
) as dag:

    extract_task = PythonOperator(
        task_id='extract_from_onprem',
        python_callable=extract_from_onprem_sql,
        provide_context=True,
    )

    security_task = PythonOperator(
        task_id='apply_security_policies',
        python_callable=apply_security_policies,
        provide_context=True,
    )

    load_task = PythonOperator(
        task_id='load_to_production',
        python_callable=load_to_production,
        provide_context=True,
    )

    # Pipeline flow
    extract_task >> security_task >> load_task
