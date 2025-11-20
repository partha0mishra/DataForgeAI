-- ============================================================================
-- Snowflake Target DDL for Oracle Migration
-- ============================================================================
-- This script creates the target schemas and tables in Snowflake for
-- Oracle to Snowflake migration.
--
-- Features:
--   - Schema organization matching Oracle structure
--   - Data type mappings from Oracle to Snowflake
--   - Primary key constraints
--   - Clustering keys for performance
--   - CDC metadata columns
--
-- Author: DataForgeAI
-- ============================================================================

-- ============================================================================
-- 1. Database and Schema Setup
-- ============================================================================

-- Create database for migrated data
CREATE DATABASE IF NOT EXISTS MIGRATED
COMMENT = 'Migrated data from Oracle database';

USE DATABASE MIGRATED;

-- Create schemas matching Oracle structure
CREATE SCHEMA IF NOT EXISTS hr
COMMENT = 'HR schema migrated from Oracle';

CREATE SCHEMA IF NOT EXISTS finance
COMMENT = 'Finance schema migrated from Oracle';

-- Create control schema for migration metadata
CREATE SCHEMA IF NOT EXISTS control
COMMENT = 'Migration control and metadata';

-- ============================================================================
-- 2. HR Schema Tables
-- ============================================================================

-- HR.EMPLOYEES table
CREATE OR REPLACE TABLE hr.employees (
    -- Primary Key
    employee_id NUMBER(6,0) NOT NULL PRIMARY KEY,

    -- Employee Information
    first_name VARCHAR(20),
    last_name VARCHAR(25) NOT NULL,
    email VARCHAR(50) NOT NULL,
    phone_number VARCHAR(20),
    hire_date DATE NOT NULL,

    -- Job Information
    job_id VARCHAR(10) NOT NULL,
    salary NUMBER(8,2),
    commission_pct NUMBER(2,2),

    -- Organizational Structure
    manager_id NUMBER(6,0),
    department_id NUMBER(4,0),

    -- Oracle CDC metadata
    last_updated TIMESTAMP_NTZ,

    -- Snowflake migration metadata
    _extracted_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _scn NUMBER(38,0),
    _source_system VARCHAR(50) DEFAULT 'ORACLE_HR',

    -- Foreign key relationships (informational only, not enforced in Snowflake)
    -- CONSTRAINT fk_emp_dept FOREIGN KEY (department_id) REFERENCES hr.departments(department_id),
    -- CONSTRAINT fk_emp_job FOREIGN KEY (job_id) REFERENCES hr.jobs(job_id),
    -- CONSTRAINT fk_emp_manager FOREIGN KEY (manager_id) REFERENCES hr.employees(employee_id)
)
COMMENT = 'Employee master data migrated from Oracle HR.EMPLOYEES'
CLUSTER BY (department_id, hire_date);

-- HR.DEPARTMENTS table (supporting table)
CREATE OR REPLACE TABLE hr.departments (
    department_id NUMBER(4,0) NOT NULL PRIMARY KEY,
    department_name VARCHAR(30) NOT NULL,
    manager_id NUMBER(6,0),
    location_id NUMBER(4,0),

    -- Metadata
    last_updated TIMESTAMP_NTZ,
    _extracted_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _scn NUMBER(38,0),
    _source_system VARCHAR(50) DEFAULT 'ORACLE_HR'
)
COMMENT = 'Department master data migrated from Oracle HR.DEPARTMENTS';

-- HR.JOBS table (supporting table)
CREATE OR REPLACE TABLE hr.jobs (
    job_id VARCHAR(10) NOT NULL PRIMARY KEY,
    job_title VARCHAR(35) NOT NULL,
    min_salary NUMBER(6,0),
    max_salary NUMBER(6,0),

    -- Metadata
    last_updated TIMESTAMP_NTZ,
    _extracted_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _scn NUMBER(38,0),
    _source_system VARCHAR(50) DEFAULT 'ORACLE_HR'
)
COMMENT = 'Job definitions migrated from Oracle HR.JOBS';

-- ============================================================================
-- 3. Finance Schema Tables
-- ============================================================================

-- FINANCE.GL_TRANSACTIONS table
CREATE OR REPLACE TABLE finance.gl_transactions (
    -- Primary Key
    transaction_id NUMBER(15,0) NOT NULL PRIMARY KEY,

    -- Transaction Details
    transaction_date DATE NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    account_id NUMBER(10,0) NOT NULL,

    -- Financial Information
    debit_amount NUMBER(15,2),
    credit_amount NUMBER(15,2),
    currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',

    -- Reference Information
    document_number VARCHAR(50),
    description VARCHAR(500),
    reference_id VARCHAR(100),

    -- Accounting Period
    fiscal_year NUMBER(4,0) NOT NULL,
    fiscal_period NUMBER(2,0) NOT NULL,
    fiscal_quarter NUMBER(1,0) NOT NULL,

    -- Status and Control
    status VARCHAR(20) DEFAULT 'POSTED',
    posted_by VARCHAR(50),
    posted_date TIMESTAMP_NTZ,

    -- Oracle CDC metadata
    created_date TIMESTAMP_NTZ NOT NULL,
    last_updated TIMESTAMP_NTZ,

    -- Snowflake migration metadata
    _extracted_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _scn NUMBER(38,0),
    _source_system VARCHAR(50) DEFAULT 'ORACLE_FINANCE',

    -- Constraints
    CONSTRAINT chk_debit_credit CHECK (
        (debit_amount IS NOT NULL AND credit_amount IS NULL) OR
        (debit_amount IS NULL AND credit_amount IS NOT NULL)
    )
)
COMMENT = 'General Ledger transactions migrated from Oracle FINANCE.GL_TRANSACTIONS'
CLUSTER BY (fiscal_year, fiscal_period, transaction_date);

-- FINANCE.GL_ACCOUNTS table (supporting table)
CREATE OR REPLACE TABLE finance.gl_accounts (
    account_id NUMBER(10,0) NOT NULL PRIMARY KEY,
    account_number VARCHAR(20) NOT NULL UNIQUE,
    account_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    account_category VARCHAR(50),
    parent_account_id NUMBER(10,0),
    is_active BOOLEAN DEFAULT TRUE,

    -- Metadata
    created_date TIMESTAMP_NTZ,
    last_updated TIMESTAMP_NTZ,
    _extracted_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _scn NUMBER(38,0),
    _source_system VARCHAR(50) DEFAULT 'ORACLE_FINANCE'
)
COMMENT = 'Chart of accounts migrated from Oracle FINANCE.GL_ACCOUNTS';

-- ============================================================================
-- 4. Control Schema Tables
-- ============================================================================

-- Migration state tracking
CREATE OR REPLACE TABLE control.migration_state (
    source_schema VARCHAR(128) NOT NULL,
    source_table VARCHAR(128) NOT NULL,
    target_schema VARCHAR(128) NOT NULL,
    target_table VARCHAR(128) NOT NULL,
    last_scn NUMBER(38,0),
    last_extraction_timestamp TIMESTAMP_NTZ,
    rows_extracted NUMBER(38,0),
    rows_loaded NUMBER(38,0),
    migration_status VARCHAR(50),
    last_updated TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (source_schema, source_table)
)
COMMENT = 'Tracks migration state for each table';

-- Migration execution log
CREATE OR REPLACE TABLE control.migration_log (
    log_id NUMBER(38,0) AUTOINCREMENT PRIMARY KEY,
    source_schema VARCHAR(128),
    source_table VARCHAR(128),
    start_scn NUMBER(38,0),
    end_scn NUMBER(38,0),
    rows_extracted NUMBER(38,0),
    rows_loaded NUMBER(38,0),
    rows_error NUMBER(38,0),
    execution_start_time TIMESTAMP_NTZ,
    execution_end_time TIMESTAMP_NTZ,
    execution_duration_seconds NUMBER(10,2),
    status VARCHAR(50),
    error_message VARCHAR(4000),
    airflow_dag_id VARCHAR(250),
    airflow_run_id VARCHAR(250),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Detailed log of all migration executions';

-- Data quality metrics
CREATE OR REPLACE TABLE control.data_quality_metrics (
    metric_id NUMBER(38,0) AUTOINCREMENT PRIMARY KEY,
    source_schema VARCHAR(128),
    source_table VARCHAR(128),
    metric_name VARCHAR(100),
    metric_value NUMBER(38,4),
    metric_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    description VARCHAR(500)
)
COMMENT = 'Data quality metrics for migrated tables';

-- ============================================================================
-- 5. File Formats and Stages for Data Loading
-- ============================================================================

-- Create file format for Parquet files
CREATE OR REPLACE FILE FORMAT control.parquet_format
TYPE = 'PARQUET'
COMPRESSION = 'SNAPPY';

-- Create file format for CSV files
CREATE OR REPLACE FILE FORMAT control.csv_format
TYPE = 'CSV'
FIELD_DELIMITER = ','
SKIP_HEADER = 1
NULL_IF = ('NULL', 'null', '')
EMPTY_FIELD_AS_NULL = TRUE
FIELD_OPTIONALLY_ENCLOSED_BY = '"'
COMPRESSION = 'AUTO';

-- Create external stage pointing to S3
CREATE OR REPLACE STAGE control.migration_stage
URL = 's3://migration-staging/oracle-cdc/'
-- CREDENTIALS = (AWS_KEY_ID = 'your-key' AWS_SECRET_KEY = 'your-secret')
FILE_FORMAT = control.parquet_format
COMMENT = 'External stage for Oracle CDC data files';

-- ============================================================================
-- 6. Views for Data Quality and Monitoring
-- ============================================================================

-- View: Latest migration status
CREATE OR REPLACE VIEW control.v_migration_status AS
SELECT
    source_schema,
    source_table,
    target_schema || '.' || target_table as target_table,
    last_scn,
    last_extraction_timestamp,
    rows_extracted,
    rows_loaded,
    migration_status,
    CASE
        WHEN rows_extracted = rows_loaded THEN 'OK'
        WHEN rows_loaded < rows_extracted THEN 'WARNING'
        ELSE 'ERROR'
    END as data_integrity_status,
    DATEDIFF('hour', last_extraction_timestamp, CURRENT_TIMESTAMP()) as hours_since_last_extraction
FROM control.migration_state
ORDER BY last_extraction_timestamp DESC;

-- View: Migration execution summary
CREATE OR REPLACE VIEW control.v_migration_execution_summary AS
SELECT
    source_schema,
    source_table,
    COUNT(*) as total_executions,
    SUM(rows_extracted) as total_rows_extracted,
    SUM(rows_loaded) as total_rows_loaded,
    SUM(rows_error) as total_rows_error,
    AVG(execution_duration_seconds) as avg_duration_seconds,
    MAX(execution_end_time) as last_execution_time,
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_executions,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_executions
FROM control.migration_log
GROUP BY source_schema, source_table
ORDER BY source_schema, source_table;

-- View: Employee count by department
CREATE OR REPLACE VIEW hr.v_employee_by_department AS
SELECT
    d.department_name,
    COUNT(e.employee_id) as employee_count,
    AVG(e.salary) as avg_salary,
    MIN(e.hire_date) as earliest_hire_date,
    MAX(e.hire_date) as latest_hire_date
FROM hr.employees e
LEFT JOIN hr.departments d ON e.department_id = d.department_id
GROUP BY d.department_name
ORDER BY employee_count DESC;

-- View: GL transaction summary by period
CREATE OR REPLACE VIEW finance.v_gl_summary_by_period AS
SELECT
    fiscal_year,
    fiscal_period,
    transaction_type,
    COUNT(*) as transaction_count,
    SUM(COALESCE(debit_amount, 0)) as total_debits,
    SUM(COALESCE(credit_amount, 0)) as total_credits,
    SUM(COALESCE(debit_amount, 0)) - SUM(COALESCE(credit_amount, 0)) as net_amount
FROM finance.gl_transactions
GROUP BY fiscal_year, fiscal_period, transaction_type
ORDER BY fiscal_year DESC, fiscal_period DESC;

-- ============================================================================
-- 7. Initialize Migration State
-- ============================================================================

-- Insert initial state for tables being migrated
INSERT INTO control.migration_state (
    source_schema,
    source_table,
    target_schema,
    target_table,
    last_scn,
    rows_extracted,
    rows_loaded,
    migration_status
) VALUES
('HR', 'EMPLOYEES', 'hr', 'employees', 0, 0, 0, 'INITIALIZED'),
('FINANCE', 'GL_TRANSACTIONS', 'finance', 'gl_transactions', 0, 0, 0, 'INITIALIZED');

-- ============================================================================
-- 8. Performance Optimization
-- ============================================================================

-- Create search optimization for frequently queried columns
ALTER TABLE hr.employees ADD SEARCH OPTIMIZATION ON EQUALITY(employee_id, email, department_id);
ALTER TABLE finance.gl_transactions ADD SEARCH OPTIMIZATION ON EQUALITY(transaction_id, account_id);

-- ============================================================================
-- 9. Row Access Policies (Optional - for data governance)
-- ============================================================================

-- Example: Restrict access to salary information
-- CREATE OR REPLACE ROW ACCESS POLICY hr.salary_access_policy
-- AS (current_role VARCHAR) RETURNS BOOLEAN ->
--     current_role IN ('HR_ADMIN', 'EXECUTIVE')
--     OR current_user() = 'HR_SYSTEM';

-- Apply policy to employees table
-- ALTER TABLE hr.employees ADD ROW ACCESS POLICY hr.salary_access_policy ON (salary);

-- ============================================================================
-- 10. Grant Permissions
-- ============================================================================

-- Create roles
CREATE ROLE IF NOT EXISTS migration_loader;
CREATE ROLE IF NOT EXISTS migration_reader;
CREATE ROLE IF NOT EXISTS data_analyst;

-- Grant usage on database and schemas
GRANT USAGE ON DATABASE MIGRATED TO ROLE migration_loader;
GRANT USAGE ON SCHEMA hr TO ROLE migration_loader;
GRANT USAGE ON SCHEMA finance TO ROLE migration_loader;
GRANT USAGE ON SCHEMA control TO ROLE migration_loader;

-- Grant loading permissions
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA hr TO ROLE migration_loader;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA finance TO ROLE migration_loader;
GRANT ALL ON ALL TABLES IN SCHEMA control TO ROLE migration_loader;
GRANT USAGE ON ALL FILE FORMATS IN SCHEMA control TO ROLE migration_loader;
GRANT USAGE ON ALL STAGES IN SCHEMA control TO ROLE migration_loader;

-- Grant read permissions to analysts
GRANT USAGE ON DATABASE MIGRATED TO ROLE data_analyst;
GRANT USAGE ON SCHEMA hr TO ROLE data_analyst;
GRANT USAGE ON SCHEMA finance TO ROLE data_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA hr TO ROLE data_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA finance TO ROLE data_analyst;
GRANT SELECT ON ALL VIEWS IN SCHEMA hr TO ROLE data_analyst;
GRANT SELECT ON ALL VIEWS IN SCHEMA finance TO ROLE data_analyst;
GRANT SELECT ON ALL VIEWS IN SCHEMA control TO ROLE data_analyst;

-- ============================================================================
-- 11. Verification Queries
-- ============================================================================

-- Check database and schemas
SHOW DATABASES LIKE 'MIGRATED';
SHOW SCHEMAS IN DATABASE MIGRATED;

-- Check tables
SHOW TABLES IN SCHEMA hr;
SHOW TABLES IN SCHEMA finance;
SHOW TABLES IN SCHEMA control;

-- Check file formats and stages
SHOW FILE FORMATS IN SCHEMA control;
SHOW STAGES IN SCHEMA control;

-- Check migration state
SELECT * FROM control.migration_state;

-- ============================================================================
-- NOTES
-- ============================================================================
--
-- 1. Data Type Mappings:
--    Oracle NUMBER(p,s) → Snowflake NUMBER(p,s)
--    Oracle VARCHAR2(n) → Snowflake VARCHAR(n)
--    Oracle DATE → Snowflake DATE
--    Oracle TIMESTAMP → Snowflake TIMESTAMP_NTZ
--
-- 2. Clustering Keys:
--    - Added on frequently filtered columns
--    - Improves query performance
--    - Automatically maintained by Snowflake
--
-- 3. CDC Metadata Columns:
--    _extracted_at: Timestamp of extraction from Oracle
--    _scn: Oracle System Change Number for this record
--    _source_system: Source system identifier
--
-- 4. Performance Features:
--    - Search optimization for point lookups
--    - Clustering for range queries
--    - Automatic statistics maintenance
--
-- 5. Best Practices:
--    - Use separate schemas for different source systems
--    - Maintain control schema for metadata
--    - Implement data quality views
--    - Grant minimal required privileges
--
-- ============================================================================
