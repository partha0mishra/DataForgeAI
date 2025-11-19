-- ============================================================================
-- Compliance and Audit Log Queries for Azure Synapse Analytics
-- ============================================================================
-- This script provides queries for compliance reporting and audit analysis
--
-- Data Sources:
-- 1. Azure Synapse audit logs (sys.fn_get_audit_file)
-- 2. Custom audit tables (governance schema)
-- 3. Azure Activity Log (via Log Analytics)
-- 4. Microsoft Purview lineage data
--
-- Compliance Requirements Covered:
-- - GDPR: Data access tracking, PII access reports
-- - HIPAA: PHI access auditing
-- - SOX: Financial data access controls
-- - PCI DSS: Credit card data access monitoring
-- ============================================================================

USE analytics;
GO

-- ============================================================================
-- Section 1: PII/PHI Data Access Reports
-- ============================================================================

-- Query 1.1: All PII column access in last 30 days
-- Shows who accessed sensitive PII columns and when
SELECT
    event_time,
    server_principal_name AS user_name,
    database_name,
    schema_name,
    object_name AS table_name,
    statement AS query_executed,
    client_ip,
    application_name,
    session_id,
    -- Classify as potential PII access
    CASE
        WHEN statement LIKE '%ssn%' OR statement LIKE '%social_security%' THEN 'SSN'
        WHEN statement LIKE '%credit_card%' OR statement LIKE '%cc_%' THEN 'Credit Card'
        WHEN statement LIKE '%email%' THEN 'Email'
        WHEN statement LIKE '%phone%' THEN 'Phone'
        ELSE 'Other PII'
    END AS pii_type
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -30, GETUTCDATE())
    AND (
        -- PII column access patterns
        statement LIKE '%ssn%'
        OR statement LIKE '%credit_card%'
        OR statement LIKE '%email%'
        OR statement LIKE '%phone%'
        OR schema_name = 'production' AND object_name IN ('customers', 'customer_transactions')
    )
    AND action_id = 'SL'  -- SELECT statements
ORDER BY event_time DESC;
GO

-- Query 1.2: PII Access Summary by User
-- Aggregate view of PII access patterns per user
SELECT
    server_principal_name AS user_name,
    COUNT(*) AS total_pii_accesses,
    COUNT(DISTINCT object_name) AS unique_tables_accessed,
    MIN(event_time) AS first_access,
    MAX(event_time) AS last_access,
    COUNT(DISTINCT client_ip) AS distinct_ip_addresses,
    COUNT(DISTINCT CAST(event_time AS DATE)) AS access_days
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -30, GETUTCDATE())
    AND (statement LIKE '%ssn%' OR statement LIKE '%credit_card%' OR statement LIKE '%email%')
    AND action_id = 'SL'
GROUP BY server_principal_name
HAVING COUNT(*) > 10  -- Flag users with high access frequency
ORDER BY total_pii_accesses DESC;
GO

-- Query 1.3: After-Hours PII Access (potential suspicious activity)
-- Flag PII access outside business hours (9 AM - 6 PM local time)
SELECT
    event_time,
    DATEPART(HOUR, event_time) AS access_hour,
    server_principal_name AS user_name,
    database_name,
    object_name AS table_name,
    statement,
    client_ip,
    application_name,
    -- Risk score based on time
    CASE
        WHEN DATEPART(HOUR, event_time) BETWEEN 0 AND 6 THEN 'High Risk - Late Night'
        WHEN DATEPART(HOUR, event_time) BETWEEN 18 AND 23 THEN 'Medium Risk - Evening'
        WHEN DATEPART(WEEKDAY, event_time) IN (1, 7) THEN 'Medium Risk - Weekend'
        ELSE 'Normal Hours'
    END AS risk_classification
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -30, GETUTCDATE())
    AND (statement LIKE '%ssn%' OR statement LIKE '%credit_card%')
    AND (
        DATEPART(HOUR, event_time) NOT BETWEEN 9 AND 18  -- Outside 9 AM - 6 PM
        OR DATEPART(WEEKDAY, event_time) IN (1, 7)  -- Weekend
    )
ORDER BY event_time DESC;
GO

-- ============================================================================
-- Section 2: Failed Authentication and Authorization Attempts
-- ============================================================================

-- Query 2.1: Failed Login Attempts
-- Track failed authentication attempts for security monitoring
SELECT
    event_time,
    server_principal_name AS attempted_username,
    client_ip,
    application_name,
    additional_information,
    COUNT(*) OVER (
        PARTITION BY server_principal_name, client_ip
        ORDER BY event_time
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_failures
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -7, GETUTCDATE())
    AND action_id = 'LGIF'  -- Login failed
ORDER BY event_time DESC;
GO

-- Query 2.2: Brute Force Attack Detection
-- Identify potential brute force attacks (multiple failed logins)
SELECT
    client_ip,
    server_principal_name AS attempted_username,
    COUNT(*) AS failed_attempts,
    MIN(event_time) AS first_attempt,
    MAX(event_time) AS last_attempt,
    DATEDIFF(MINUTE, MIN(event_time), MAX(event_time)) AS attack_duration_minutes
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -1, GETUTCDATE())
    AND action_id = 'LGIF'
GROUP BY client_ip, server_principal_name
HAVING COUNT(*) >= 5  -- 5 or more failed attempts
ORDER BY failed_attempts DESC, last_attempt DESC;
GO

-- Query 2.3: Permission Denied Events
-- Track authorization failures
SELECT
    event_time,
    server_principal_name AS user_name,
    database_name,
    schema_name,
    object_name,
    statement,
    permission_bitmask,
    -- Decode permission type
    CASE
        WHEN action_id = 'SL' THEN 'SELECT Denied'
        WHEN action_id = 'IN' THEN 'INSERT Denied'
        WHEN action_id = 'UP' THEN 'UPDATE Denied'
        WHEN action_id = 'DL' THEN 'DELETE Denied'
        ELSE 'Other Permission Denied'
    END AS denied_permission,
    client_ip
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -30, GETUTCDATE())
    AND succeeded = 0  -- Failed operations
ORDER BY event_time DESC;
GO

-- ============================================================================
-- Section 3: Schema and Permission Changes
-- ============================================================================

-- Query 3.1: Database Schema Changes
-- Track DDL operations for change management
SELECT
    event_time,
    server_principal_name AS changed_by,
    database_name,
    schema_name,
    object_name,
    object_type,
    CASE action_id
        WHEN 'CR' THEN 'CREATE'
        WHEN 'AL' THEN 'ALTER'
        WHEN 'DR' THEN 'DROP'
        ELSE action_id
    END AS change_type,
    statement,
    session_id
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -30, GETUTCDATE())
    AND action_id IN ('CR', 'AL', 'DR')  -- CREATE, ALTER, DROP
    AND object_type IN ('U', 'V', 'P', 'FN', 'IF')  -- Tables, Views, Procedures, Functions
ORDER BY event_time DESC;
GO

-- Query 3.2: Permission Grant/Revoke Activities
-- Audit changes to user permissions
SELECT
    event_time,
    server_principal_name AS changed_by,
    database_name,
    CASE action_id
        WHEN 'G' THEN 'GRANT'
        WHEN 'R' THEN 'REVOKE'
        WHEN 'D' THEN 'DENY'
        ELSE action_id
    END AS permission_action,
    statement,
    -- Extract grantee from statement (simplified)
    SUBSTRING(
        statement,
        CHARINDEX('TO ', statement) + 3,
        CHARINDEX(' ', statement + ' ', CHARINDEX('TO ', statement) + 3) - CHARINDEX('TO ', statement) - 3
    ) AS grantee,
    client_ip
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -90, GETUTCDATE())
    AND action_id IN ('G', 'R', 'D')
ORDER BY event_time DESC;
GO

-- ============================================================================
-- Section 4: Data Modification Audit (DML)
-- ============================================================================

-- Query 4.1: INSERT/UPDATE/DELETE Operations on Sensitive Tables
SELECT
    event_time,
    server_principal_name AS user_name,
    database_name,
    schema_name,
    object_name AS table_name,
    CASE action_id
        WHEN 'IN' THEN 'INSERT'
        WHEN 'UP' THEN 'UPDATE'
        WHEN 'DL' THEN 'DELETE'
        ELSE action_id
    END AS operation_type,
    statement,
    affected_rows,
    client_ip,
    application_name
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -30, GETUTCDATE())
    AND action_id IN ('IN', 'UP', 'DL')
    AND schema_name = 'production'
    AND object_name IN ('customers', 'customer_transactions', 'financial_records')
ORDER BY event_time DESC;
GO

-- Query 4.2: Bulk Data Exports
-- Identify large data exports (potential data exfiltration)
SELECT
    event_time,
    server_principal_name AS user_name,
    database_name,
    object_name,
    statement,
    -- Estimate exported rows
    CASE
        WHEN statement LIKE '%INTO OUTFILE%' OR statement LIKE '%bcp%' THEN 'File Export'
        WHEN statement LIKE '%OPENROWSET%' THEN 'Linked Server Export'
        ELSE 'SELECT Query'
    END AS export_type,
    client_ip,
    application_name,
    session_id
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(DAY, -30, GETUTCDATE())
    AND (
        statement LIKE '%INTO OUTFILE%'
        OR statement LIKE '%OPENROWSET%'
        OR (action_id = 'SL' AND LEN(statement) > 2000)  -- Large queries
    )
ORDER BY event_time DESC;
GO

-- ============================================================================
-- Section 5: Custom Application Audit Logs
-- ============================================================================

-- Query 5.1: ETL Pipeline Execution Audit
-- Track all ETL pipeline runs from custom audit table
SELECT
    timestamp,
    event_type,
    source_system,
    target_system,
    table_name,
    record_count,
    user_principal,
    dag_id,
    task_id,
    execution_date,
    JSON_VALUE(metadata, '$.staging_table') AS staging_table,
    JSON_VALUE(metadata, '$.error') AS error_message
FROM governance.data_lineage_audit
WHERE timestamp >= DATEADD(DAY, -30, GETUTCDATE())
ORDER BY timestamp DESC;
GO

-- Query 5.2: Failed ETL Runs for Troubleshooting
SELECT
    timestamp,
    event_type,
    source_system,
    target_system,
    table_name,
    user_principal,
    dag_id,
    task_id,
    JSON_VALUE(metadata, '$.error') AS error_message,
    metadata
FROM governance.data_lineage_audit
WHERE
    timestamp >= DATEADD(DAY, -7, GETUTCDATE())
    AND event_type LIKE '%failed%'
ORDER BY timestamp DESC;
GO

-- Query 5.3: Data Lineage Report
-- Show complete lineage for specific table
WITH lineage_chain AS (
    SELECT
        timestamp,
        event_type,
        source_system,
        target_system,
        table_name,
        record_count,
        dag_id,
        task_id,
        ROW_NUMBER() OVER (PARTITION BY target_system ORDER BY timestamp) AS sequence_num
    FROM governance.data_lineage_audit
    WHERE
        table_name = 'customer_transactions'
        AND timestamp >= DATEADD(DAY, -7, GETUTCDATE())
)
SELECT
    timestamp,
    event_type,
    source_system + ' -> ' + target_system AS data_flow,
    table_name,
    record_count,
    dag_id + '.' + task_id AS pipeline_task,
    sequence_num
FROM lineage_chain
ORDER BY timestamp;
GO

-- ============================================================================
-- Section 6: Compliance-Specific Reports
-- ============================================================================

-- Query 6.1: GDPR Right to Access Report
-- List all access to specific customer's data (for GDPR access requests)
DECLARE @customer_email NVARCHAR(255) = 'john.doe@example.com';

SELECT
    event_time AS access_timestamp,
    server_principal_name AS accessed_by,
    database_name,
    object_name AS table_accessed,
    'Azure Synapse Audit Log' AS source,
    client_ip,
    application_name
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(YEAR, -1, GETUTCDATE())  -- Last 12 months
    AND statement LIKE '%' + @customer_email + '%'
    AND action_id = 'SL'

UNION ALL

-- Include custom audit logs
SELECT
    timestamp AS access_timestamp,
    user_principal AS accessed_by,
    target_system AS database_name,
    table_name AS table_accessed,
    'ETL Pipeline Audit' AS source,
    NULL AS client_ip,
    NULL AS application_name
FROM governance.data_lineage_audit
WHERE
    timestamp >= DATEADD(YEAR, -1, GETUTCDATE())
    AND (
        JSON_VALUE(metadata, '$.filters') LIKE '%' + @customer_email + '%'
        OR table_name IN (
            SELECT DISTINCT table_name
            FROM production.customers
            WHERE email = @customer_email
        )
    )
ORDER BY access_timestamp DESC;
GO

-- Query 6.2: GDPR Right to Erasure Compliance
-- Verify customer data deletion across all systems
DECLARE @deleted_customer_id INT = 12345;

SELECT
    'production.customers' AS table_name,
    COUNT(*) AS records_found,
    CASE WHEN COUNT(*) > 0 THEN 'NOT DELETED' ELSE 'DELETED' END AS status
FROM production.customers
WHERE customer_id = @deleted_customer_id

UNION ALL

SELECT
    'production.customer_transactions',
    COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN 'NOT DELETED' ELSE 'DELETED' END
FROM production.customer_transactions
WHERE customer_id = @deleted_customer_id

UNION ALL

SELECT
    'governance.data_lineage_audit (anonymized)',
    COUNT(*),
    'ANONYMIZED'
FROM governance.data_lineage_audit
WHERE JSON_VALUE(metadata, '$.customer_id') = CAST(@deleted_customer_id AS NVARCHAR(10));
GO

-- Query 6.3: SOX Compliance - Financial Data Access Control
-- Report on who accessed financial tables in last quarter
SELECT
    DATEPART(YEAR, event_time) AS year,
    DATEPART(QUARTER, event_time) AS quarter,
    server_principal_name AS user_name,
    object_name AS financial_table,
    COUNT(*) AS access_count,
    COUNT(DISTINCT CAST(event_time AS DATE)) AS access_days,
    MIN(event_time) AS first_access,
    MAX(event_time) AS last_access
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(QUARTER, -1, GETUTCDATE())
    AND schema_name = 'production'
    AND object_name LIKE '%financial%'
    AND action_id = 'SL'
GROUP BY
    DATEPART(YEAR, event_time),
    DATEPART(QUARTER, event_time),
    server_principal_name,
    object_name
ORDER BY year DESC, quarter DESC, access_count DESC;
GO

-- ============================================================================
-- Section 7: Export to Microsoft Purview (Data Governance)
-- ============================================================================

-- Query 7.1: Prepare Lineage Data for Purview Export
SELECT
    timestamp,
    source_system AS source_qualified_name,
    target_system AS target_qualified_name,
    table_name,
    record_count,
    dag_id AS process_id,
    user_principal,
    JSON_VALUE(metadata, '$.transformation_type') AS transformation_type,
    'AirflowETL' AS process_type
FROM governance.data_lineage_audit
WHERE timestamp >= DATEADD(DAY, -1, GETUTCDATE())
ORDER BY timestamp
FOR JSON PATH;
GO

-- Query 7.2: Data Quality Metrics for Purview
SELECT
    table_name,
    COUNT(*) AS total_pipeline_runs,
    SUM(record_count) AS total_records_processed,
    AVG(record_count) AS avg_records_per_run,
    SUM(CASE WHEN event_type LIKE '%failed%' THEN 1 ELSE 0 END) AS failed_runs,
    CAST(SUM(CASE WHEN event_type LIKE '%failed%' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 AS failure_rate_pct
FROM governance.data_lineage_audit
WHERE timestamp >= DATEADD(DAY, -30, GETUTCDATE())
GROUP BY table_name
ORDER BY failure_rate_pct DESC;
GO

-- ============================================================================
-- Section 8: Alerting Queries (for scheduled monitoring)
-- ============================================================================

-- Query 8.1: High-Risk Activities Alert
-- Identify activities requiring immediate attention
SELECT
    event_time,
    'HIGH' AS alert_severity,
    server_principal_name AS user_name,
    CASE
        WHEN action_id = 'DR' AND object_name LIKE 'production%' THEN 'Production table dropped'
        WHEN action_id = 'AL' AND statement LIKE '%ENCRYPTION%' THEN 'Encryption settings changed'
        WHEN statement LIKE '%sp_addrole%' OR statement LIKE '%sp_addrolemember%' THEN 'Security role modified'
        WHEN client_ip NOT LIKE '10.%' AND client_ip NOT LIKE '192.168%' THEN 'External IP access'
        ELSE 'Other high-risk activity'
    END AS alert_reason,
    statement,
    client_ip
FROM sys.fn_get_audit_file(
    'https://<storage-account>.blob.core.windows.net/sqlaudit/**',
    DEFAULT,
    DEFAULT
)
WHERE
    event_time >= DATEADD(HOUR, -1, GETUTCDATE())  -- Last hour
    AND (
        (action_id = 'DR' AND schema_name = 'production')
        OR statement LIKE '%ENCRYPTION%'
        OR statement LIKE '%sp_addrole%'
        OR statement LIKE '%sp_addrolemember%'
        OR (client_ip NOT LIKE '10.%' AND client_ip NOT LIKE '192.168%')
    )
ORDER BY event_time DESC;
GO

PRINT '========================================================================';
PRINT 'Compliance and Audit Queries Loaded Successfully';
PRINT '========================================================================';
PRINT 'Available Report Categories:';
PRINT '  1. PII/PHI Data Access Reports (GDPR, HIPAA)';
PRINT '  2. Failed Authentication and Authorization';
PRINT '  3. Schema and Permission Changes';
PRINT '  4. Data Modification Audit (DML)';
PRINT '  5. Custom Application Audit Logs';
PRINT '  6. Compliance-Specific Reports (GDPR, SOX)';
PRINT '  7. Export to Microsoft Purview';
PRINT '  8. Alerting Queries';
PRINT '';
PRINT 'Note: Update the storage account URL in sys.fn_get_audit_file() calls';
PRINT '      with your actual Azure Storage account for audit logs.';
PRINT '========================================================================';
GO
