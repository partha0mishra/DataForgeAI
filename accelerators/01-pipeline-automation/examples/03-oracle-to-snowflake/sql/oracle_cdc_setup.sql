-- ============================================================================
-- Oracle CDC Setup Script
-- ============================================================================
-- This script sets up Change Data Capture (CDC) capabilities in Oracle
-- for incremental data extraction to Snowflake.
--
-- Prerequisites:
--   - DBA privileges to grant Flashback permissions
--   - Tables to be migrated must have primary keys
--   - Sufficient undo retention for Flashback queries
--
-- Author: DataForgeAI
-- ============================================================================

-- ============================================================================
-- 1. Create Read-Only User for Data Extraction
-- ============================================================================

-- Create dedicated user for data extraction
CREATE USER migration_reader IDENTIFIED BY "SecurePassword123!";

-- Grant connect privilege
GRANT CREATE SESSION TO migration_reader;

-- ============================================================================
-- 2. Grant Required Privileges for CDC
-- ============================================================================

-- Allow reading data dictionary
GRANT SELECT_CATALOG_ROLE TO migration_reader;

-- Grant Flashback privileges (required for SCN-based CDC)
GRANT FLASHBACK ANY TABLE TO migration_reader;

-- Grant SELECT on specific tables to be migrated
GRANT SELECT ON hr.employees TO migration_reader;
GRANT SELECT ON finance.gl_transactions TO migration_reader;

-- Grant access to change tracking views
GRANT SELECT ON v$database TO migration_reader;
GRANT SELECT ON v$transaction TO migration_reader;
GRANT SELECT ON dba_tables TO migration_reader;
GRANT SELECT ON dba_tab_columns TO migration_reader;
GRANT SELECT ON dba_constraints TO migration_reader;
GRANT SELECT ON dba_cons_columns TO migration_reader;
GRANT SELECT ON dba_indexes TO migration_reader;
GRANT SELECT ON dba_ind_columns TO migration_reader;

-- ============================================================================
-- 3. Enable Supplemental Logging (Optional - for advanced CDC)
-- ============================================================================

-- Enable minimal supplemental logging at database level
-- This is required for LogMiner-based CDC (alternative to Flashback)
ALTER DATABASE ADD SUPPLEMENTAL LOG DATA;

-- Enable primary key logging for specific tables
ALTER TABLE hr.employees ADD SUPPLEMENTAL LOG DATA (PRIMARY KEY) COLUMNS;
ALTER TABLE finance.gl_transactions ADD SUPPLEMENTAL LOG DATA (PRIMARY KEY) COLUMNS;

-- ============================================================================
-- 4. Configure Undo Retention
-- ============================================================================

-- Set undo retention to 24 hours (86400 seconds)
-- This allows Flashback queries to go back 24 hours
-- Adjust based on your CDC frequency
ALTER SYSTEM SET undo_retention = 86400 SCOPE=BOTH;

-- ============================================================================
-- 5. Create Tracking Tables for CDC State Management
-- ============================================================================

-- Create schema for CDC metadata
CREATE USER cdc_control IDENTIFIED BY "ControlPassword123!";
GRANT CREATE SESSION, CREATE TABLE, UNLIMITED TABLESPACE TO cdc_control;

-- Create CDC state tracking table
CREATE TABLE cdc_control.extraction_state (
    source_schema VARCHAR2(128) NOT NULL,
    source_table VARCHAR2(128) NOT NULL,
    last_scn NUMBER(38) NOT NULL,
    last_extracted_at TIMESTAMP NOT NULL,
    extraction_status VARCHAR2(50),
    rows_extracted NUMBER(38),
    PRIMARY KEY (source_schema, source_table)
);

-- Create CDC execution log
CREATE TABLE cdc_control.extraction_log (
    log_id NUMBER(38) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_schema VARCHAR2(128) NOT NULL,
    source_table VARCHAR2(128) NOT NULL,
    start_scn NUMBER(38),
    end_scn NUMBER(38),
    rows_extracted NUMBER(38),
    extraction_start_time TIMESTAMP NOT NULL,
    extraction_end_time TIMESTAMP,
    status VARCHAR2(50),
    error_message VARCHAR2(4000)
);

-- Grant access to migration reader
GRANT SELECT, INSERT, UPDATE ON cdc_control.extraction_state TO migration_reader;
GRANT SELECT, INSERT ON cdc_control.extraction_log TO migration_reader;

-- ============================================================================
-- 6. Initialize Tracking for Target Tables
-- ============================================================================

-- Get current SCN for initial state
DECLARE
    v_current_scn NUMBER;
BEGIN
    SELECT current_scn INTO v_current_scn FROM v$database;

    -- Initialize HR.EMPLOYEES
    INSERT INTO cdc_control.extraction_state (
        source_schema,
        source_table,
        last_scn,
        last_extracted_at,
        extraction_status,
        rows_extracted
    ) VALUES (
        'HR',
        'EMPLOYEES',
        v_current_scn,
        SYSTIMESTAMP,
        'INITIALIZED',
        0
    );

    -- Initialize FINANCE.GL_TRANSACTIONS
    INSERT INTO cdc_control.extraction_state (
        source_schema,
        source_table,
        last_scn,
        last_extracted_at,
        extraction_status,
        rows_extracted
    ) VALUES (
        'FINANCE',
        'GL_TRANSACTIONS',
        v_current_scn,
        SYSTIMESTAMP,
        'INITIALIZED',
        0
    );

    COMMIT;
END;
/

-- ============================================================================
-- 7. Create Helper Procedures
-- ============================================================================

-- Procedure to update extraction state
CREATE OR REPLACE PROCEDURE cdc_control.update_extraction_state(
    p_schema VARCHAR2,
    p_table VARCHAR2,
    p_scn NUMBER,
    p_rows NUMBER,
    p_status VARCHAR2
) AS
BEGIN
    UPDATE cdc_control.extraction_state
    SET last_scn = p_scn,
        last_extracted_at = SYSTIMESTAMP,
        extraction_status = p_status,
        rows_extracted = p_rows
    WHERE source_schema = p_schema
      AND source_table = p_table;

    COMMIT;
END;
/

-- Grant execute on procedure
GRANT EXECUTE ON cdc_control.update_extraction_state TO migration_reader;

-- ============================================================================
-- 8. Add Timestamps to Tables (if not exist)
-- ============================================================================

-- Add LAST_UPDATED column to HR.EMPLOYEES if it doesn't exist
DECLARE
    v_column_exists NUMBER;
BEGIN
    SELECT COUNT(*)
    INTO v_column_exists
    FROM all_tab_columns
    WHERE owner = 'HR'
      AND table_name = 'EMPLOYEES'
      AND column_name = 'LAST_UPDATED';

    IF v_column_exists = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE hr.employees ADD (last_updated TIMESTAMP DEFAULT SYSTIMESTAMP)';
    END IF;
END;
/

-- Add trigger to update LAST_UPDATED on changes
CREATE OR REPLACE TRIGGER hr.employees_last_updated_trg
BEFORE UPDATE ON hr.employees
FOR EACH ROW
BEGIN
    :NEW.last_updated := SYSTIMESTAMP;
END;
/

-- Similar for GL_TRANSACTIONS
DECLARE
    v_column_exists NUMBER;
BEGIN
    SELECT COUNT(*)
    INTO v_column_exists
    FROM all_tab_columns
    WHERE owner = 'FINANCE'
      AND table_name = 'GL_TRANSACTIONS'
      AND column_name = 'LAST_UPDATED';

    IF v_column_exists = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE finance.gl_transactions ADD (last_updated TIMESTAMP DEFAULT SYSTIMESTAMP)';
    END IF;
END;
/

CREATE OR REPLACE TRIGGER finance.gl_trans_last_updated_trg
BEFORE UPDATE ON finance.gl_transactions
FOR EACH ROW
BEGIN
    :NEW.last_updated := SYSTIMESTAMP;
END;
/

-- ============================================================================
-- 9. Verify Setup
-- ============================================================================

-- Check current SCN
SELECT current_scn FROM v$database;

-- Check undo retention
SELECT value FROM v$parameter WHERE name = 'undo_retention';

-- Check supplemental logging
SELECT supplemental_log_data_min FROM v$database;

-- Check extraction state
SELECT * FROM cdc_control.extraction_state ORDER BY source_schema, source_table;

-- Check user privileges
SELECT * FROM dba_sys_privs WHERE grantee = 'MIGRATION_READER';
SELECT * FROM dba_tab_privs WHERE grantee = 'MIGRATION_READER';

-- ============================================================================
-- 10. Test CDC Query
-- ============================================================================

-- Test Flashback query (should work if setup is correct)
SELECT COUNT(*)
FROM hr.employees AS OF SCN (SELECT current_scn FROM v$database);

-- Test incremental query using ORA_ROWSCN
SELECT employee_id, first_name, last_name, ORA_ROWSCN
FROM hr.employees
WHERE ORA_ROWSCN > (SELECT last_scn FROM cdc_control.extraction_state WHERE source_table = 'EMPLOYEES')
FETCH FIRST 10 ROWS ONLY;

-- ============================================================================
-- NOTES
-- ============================================================================
--
-- 1. SCN-based CDC:
--    - Uses ORA_ROWSCN pseudo-column to track changes
--    - Requires FLASHBACK ANY TABLE privilege
--    - Limited by undo retention period
--    - Best for tables with moderate change rates
--
-- 2. Timestamp-based CDC:
--    - Uses LAST_UPDATED column
--    - Simpler but requires application to maintain timestamps
--    - No dependency on undo retention
--    - Best for tables with explicit audit columns
--
-- 3. LogMiner-based CDC (advanced):
--    - Reads redo logs for all changes
--    - Captures INSERT, UPDATE, DELETE operations
--    - Requires supplemental logging
--    - More complex but most comprehensive
--
-- 4. Performance Considerations:
--    - Ensure adequate undo tablespace size
--    - Monitor undo retention effectiveness
--    - Add indexes on incremental columns
--    - Consider partitioning large tables
--
-- 5. Security:
--    - Use separate read-only user
--    - Grant minimum required privileges
--    - Rotate passwords regularly
--    - Monitor extraction user activity
--
-- ============================================================================
