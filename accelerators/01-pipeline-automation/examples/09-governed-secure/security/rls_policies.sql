-- ============================================================================
-- Row-Level Security (RLS) Policies for Multi-Tenant Data Access Control
-- ============================================================================
-- This script implements Row-Level Security in Azure Synapse Analytics
--
-- Use Cases:
-- 1. Multi-tenant SaaS applications - isolate tenant data
-- 2. Regional data access - restrict by geography
-- 3. Department-level access - show only relevant department data
-- 4. Manager hierarchy - show data for direct reports only
--
-- Security Benefits:
-- - Transparent data filtering based on user context
-- - Centralized security logic (no application-level filtering needed)
-- - Prevents data leakage across tenants/departments
-- - Audit trail of who accessed what data
-- ============================================================================

USE analytics;
GO

-- ============================================================================
-- Step 1: Enable Row-Level Security Feature
-- ============================================================================

-- Create schema for security objects
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'security')
BEGIN
    EXEC('CREATE SCHEMA security');
    PRINT 'Schema created: security';
END
GO

-- ============================================================================
-- Step 2: Create Security Predicate Functions
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Predicate Function 1: Tenant-based filtering
-- ---------------------------------------------------------------------------
-- This function filters rows based on the tenant_id
-- Users can only see data for their assigned tenant(s)

CREATE OR ALTER FUNCTION security.fn_tenant_access_predicate(@tenant_id INT)
    RETURNS TABLE
    WITH SCHEMABINDING
AS
RETURN
    SELECT 1 AS tenant_access_allowed
    WHERE
        -- Option 1: Use SESSION_CONTEXT (recommended for application connections)
        @tenant_id = CAST(SESSION_CONTEXT(N'tenant_id') AS INT)

        -- Option 2: Use database roles/users for specific tenants
        OR IS_MEMBER('db_owner') = 1  -- DB owners can see all data
        OR IS_MEMBER('compliance_officer_role') = 1  -- Compliance can see all

        -- Option 3: Join with user-tenant mapping table
        OR EXISTS (
            SELECT 1
            FROM security.user_tenant_access uta
            WHERE uta.user_principal = USER_NAME()
            AND uta.tenant_id = @tenant_id
            AND uta.is_active = 1
            AND GETUTCDATE() BETWEEN uta.valid_from AND uta.valid_to
        );
GO

-- ---------------------------------------------------------------------------
-- Predicate Function 2: Regional access filtering
-- ---------------------------------------------------------------------------
-- Filter data based on user's authorized regions

CREATE OR ALTER FUNCTION security.fn_region_access_predicate(@region NVARCHAR(50))
    RETURNS TABLE
    WITH SCHEMABINDING
AS
RETURN
    SELECT 1 AS region_access_allowed
    WHERE
        -- Global administrators can see all regions
        IS_MEMBER('global_admin_role') = 1

        -- Region-specific roles
        OR (@region = 'US' AND IS_MEMBER('us_region_access') = 1)
        OR (@region = 'EU' AND IS_MEMBER('eu_region_access') = 1)
        OR (@region = 'APAC' AND IS_MEMBER('apac_region_access') = 1)

        -- Session context for dynamic region filtering
        OR @region = CAST(SESSION_CONTEXT(N'user_region') AS NVARCHAR(50))

        -- User-region mapping table
        OR EXISTS (
            SELECT 1
            FROM security.user_region_access ura
            WHERE ura.user_principal = USER_NAME()
            AND ura.region = @region
            AND ura.is_active = 1
        );
GO

-- ---------------------------------------------------------------------------
-- Predicate Function 3: Department hierarchy filtering
-- ---------------------------------------------------------------------------
-- Managers can see their department's data and subordinate departments

CREATE OR ALTER FUNCTION security.fn_department_access_predicate(@department_id INT)
    RETURNS TABLE
    WITH SCHEMABINDING
AS
RETURN
    SELECT 1 AS department_access_allowed
    WHERE
        -- C-level executives see all departments
        IS_MEMBER('executive_role') = 1

        -- User's own department
        OR EXISTS (
            SELECT 1
            FROM security.user_department_access uda
            WHERE uda.user_principal = USER_NAME()
            AND (
                uda.department_id = @department_id  -- Own department
                OR EXISTS (  -- Subordinate departments
                    SELECT 1
                    FROM security.department_hierarchy dh
                    WHERE dh.parent_department_id = uda.department_id
                    AND dh.child_department_id = @department_id
                )
            )
            AND uda.is_active = 1
        );
GO

-- ---------------------------------------------------------------------------
-- Predicate Function 4: Data sensitivity level filtering
-- ---------------------------------------------------------------------------
-- Filter based on user's clearance level

CREATE OR ALTER FUNCTION security.fn_sensitivity_level_predicate(@sensitivity_level NVARCHAR(20))
    RETURNS TABLE
    WITH SCHEMABINDING
AS
RETURN
    SELECT 1 AS sensitivity_access_allowed
    WHERE
        -- Admin can see all levels
        IS_MEMBER('db_owner') = 1

        -- Match or exceed required sensitivity level
        OR EXISTS (
            SELECT 1
            FROM security.user_clearance uc
            WHERE uc.user_principal = USER_NAME()
            AND (
                -- User clearance level >= required level
                (uc.clearance_level = 'HIGH' AND @sensitivity_level IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'HIGH'))
                OR (uc.clearance_level = 'CONFIDENTIAL' AND @sensitivity_level IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL'))
                OR (uc.clearance_level = 'INTERNAL' AND @sensitivity_level IN ('PUBLIC', 'INTERNAL'))
                OR (uc.clearance_level = 'PUBLIC' AND @sensitivity_level = 'PUBLIC')
            )
            AND uc.is_active = 1
        );
GO

-- ============================================================================
-- Step 3: Create Supporting Tables for RLS
-- ============================================================================

-- User-tenant access mapping
CREATE TABLE security.user_tenant_access
(
    access_id       INT IDENTITY(1,1) PRIMARY KEY,
    user_principal  NVARCHAR(128) NOT NULL,
    tenant_id       INT NOT NULL,
    is_active       BIT DEFAULT 1,
    valid_from      DATETIME2 DEFAULT GETUTCDATE(),
    valid_to        DATETIME2 DEFAULT '9999-12-31',
    granted_by      NVARCHAR(128) DEFAULT SYSTEM_USER,
    granted_date    DATETIME2 DEFAULT GETUTCDATE(),
    INDEX IX_user_tenant (user_principal, tenant_id)
)
WITH (DISTRIBUTION = REPLICATE);
GO

-- User-region access mapping
CREATE TABLE security.user_region_access
(
    access_id       INT IDENTITY(1,1) PRIMARY KEY,
    user_principal  NVARCHAR(128) NOT NULL,
    region          NVARCHAR(50) NOT NULL,
    is_active       BIT DEFAULT 1,
    granted_by      NVARCHAR(128) DEFAULT SYSTEM_USER,
    granted_date    DATETIME2 DEFAULT GETUTCDATE(),
    INDEX IX_user_region (user_principal, region)
)
WITH (DISTRIBUTION = REPLICATE);
GO

-- User-department access mapping
CREATE TABLE security.user_department_access
(
    access_id       INT IDENTITY(1,1) PRIMARY KEY,
    user_principal  NVARCHAR(128) NOT NULL,
    department_id   INT NOT NULL,
    is_active       BIT DEFAULT 1,
    granted_by      NVARCHAR(128) DEFAULT SYSTEM_USER,
    granted_date    DATETIME2 DEFAULT GETUTCDATE(),
    INDEX IX_user_department (user_principal, department_id)
)
WITH (DISTRIBUTION = REPLICATE);
GO

-- Department hierarchy
CREATE TABLE security.department_hierarchy
(
    hierarchy_id            INT IDENTITY(1,1) PRIMARY KEY,
    parent_department_id    INT NOT NULL,
    child_department_id     INT NOT NULL,
    depth                   INT DEFAULT 1,
    INDEX IX_hierarchy (parent_department_id, child_department_id)
)
WITH (DISTRIBUTION = REPLICATE);
GO

-- User clearance levels
CREATE TABLE security.user_clearance
(
    clearance_id    INT IDENTITY(1,1) PRIMARY KEY,
    user_principal  NVARCHAR(128) NOT NULL,
    clearance_level NVARCHAR(20) NOT NULL CHECK (clearance_level IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'HIGH')),
    is_active       BIT DEFAULT 1,
    granted_by      NVARCHAR(128) DEFAULT SYSTEM_USER,
    granted_date    DATETIME2 DEFAULT GETUTCDATE(),
    INDEX IX_user_clearance (user_principal)
)
WITH (DISTRIBUTION = REPLICATE);
GO

-- ============================================================================
-- Step 4: Apply RLS Policies to Tables
-- ============================================================================

-- Apply tenant-based RLS to customer transactions
CREATE SECURITY POLICY security.tenant_isolation_policy
ADD FILTER PREDICATE security.fn_tenant_access_predicate(tenant_id)
    ON production.customer_transactions
WITH (STATE = ON, SCHEMABINDING = ON);
GO

PRINT 'Applied RLS policy: tenant_isolation_policy on production.customer_transactions';
GO

-- Apply regional RLS to customer data
CREATE SECURITY POLICY security.regional_data_policy
ADD FILTER PREDICATE security.fn_region_access_predicate(region)
    ON production.customers
WITH (STATE = ON, SCHEMABINDING = ON);
GO

PRINT 'Applied RLS policy: regional_data_policy on production.customers';
GO

-- Apply department-based RLS to sales data (example table)
/*
CREATE SECURITY POLICY security.department_access_policy
ADD FILTER PREDICATE security.fn_department_access_predicate(department_id)
    ON production.sales_data
WITH (STATE = ON, SCHEMABINDING = ON);
GO
*/

-- Apply sensitivity level RLS
/*
CREATE SECURITY POLICY security.sensitivity_level_policy
ADD FILTER PREDICATE security.fn_sensitivity_level_predicate(sensitivity_level)
    ON production.confidential_data
WITH (STATE = ON, SCHEMABINDING = ON);
GO
*/

-- ============================================================================
-- Step 5: Add Block Predicates (for INSERT/UPDATE/DELETE)
-- ============================================================================

-- Block predicate prevents unauthorized users from modifying data
-- they don't have access to

-- Example: Prevent users from inserting data for other tenants
ALTER SECURITY POLICY security.tenant_isolation_policy
ADD BLOCK PREDICATE security.fn_tenant_access_predicate(tenant_id)
    ON production.customer_transactions AFTER INSERT;
GO

ALTER SECURITY POLICY security.tenant_isolation_policy
ADD BLOCK PREDICATE security.fn_tenant_access_predicate(tenant_id)
    ON production.customer_transactions AFTER UPDATE;
GO

PRINT 'Added block predicates to prevent unauthorized INSERT/UPDATE';
GO

-- ============================================================================
-- Step 6: Sample Data for Testing
-- ============================================================================

-- Insert sample user-tenant access mappings
INSERT INTO security.user_tenant_access (user_principal, tenant_id, is_active)
VALUES
    ('user1@example.com', 1, 1),
    ('user1@example.com', 2, 1),
    ('user2@example.com', 2, 1),
    ('user3@example.com', 3, 1);
GO

-- Insert sample user-region access
INSERT INTO security.user_region_access (user_principal, region, is_active)
VALUES
    ('user1@example.com', 'US', 1),
    ('user2@example.com', 'EU', 1),
    ('user3@example.com', 'APAC', 1);
GO

-- Insert sample department hierarchy
INSERT INTO security.department_hierarchy (parent_department_id, child_department_id, depth)
VALUES
    (1, 2, 1),  -- Department 1 is parent of Department 2
    (1, 3, 1),  -- Department 1 is parent of Department 3
    (2, 4, 1),  -- Department 2 is parent of Department 4
    (1, 4, 2);  -- Department 1 is grandparent of Department 4
GO

-- Insert sample user clearances
INSERT INTO security.user_clearance (user_principal, clearance_level, is_active)
VALUES
    ('user1@example.com', 'HIGH', 1),
    ('user2@example.com', 'CONFIDENTIAL', 1),
    ('user3@example.com', 'INTERNAL', 1),
    ('user4@example.com', 'PUBLIC', 1);
GO

-- ============================================================================
-- Step 7: Test RLS Policies
-- ============================================================================

-- Test Script 1: Tenant Isolation
-- Set session context for Tenant 1
EXEC sp_set_session_context @key = N'tenant_id', @value = 1;
GO

-- This query will only return rows for tenant_id = 1
SELECT tenant_id, customer_id, transaction_date, amount
FROM production.customer_transactions
ORDER BY transaction_date DESC;
GO

-- Change to Tenant 2
EXEC sp_set_session_context @key = N'tenant_id', @value = 2;
GO

-- Now only Tenant 2 data is visible
SELECT tenant_id, customer_id, transaction_date, amount
FROM production.customer_transactions
ORDER BY transaction_date DESC;
GO

-- Clear session context
EXEC sp_set_session_context @key = N'tenant_id', @value = NULL;
GO

-- Test Script 2: Regional Access
EXEC sp_set_session_context @key = N'user_region', @value = 'US';
GO

SELECT region, customer_id, first_name, last_name
FROM production.customers
ORDER BY customer_id;
GO

-- ============================================================================
-- Step 8: Monitoring and Auditing RLS
-- ============================================================================

-- Query to check active security policies
SELECT
    t.name AS table_name,
    sp.name AS security_policy_name,
    sp.is_enabled,
    sp.is_schema_bound,
    c.name AS predicate_column,
    spo.predicate_type_desc
FROM sys.security_policies sp
INNER JOIN sys.security_predicates spo ON sp.object_id = spo.object_id
INNER JOIN sys.tables t ON spo.target_object_id = t.object_id
LEFT JOIN sys.columns c ON spo.target_object_id = c.object_id AND spo.target_column_id = c.column_id
ORDER BY t.name, sp.name;
GO

-- Query to check user access mappings
SELECT
    user_principal,
    tenant_id,
    is_active,
    valid_from,
    valid_to,
    granted_by,
    granted_date
FROM security.user_tenant_access
ORDER BY user_principal, tenant_id;
GO

-- ============================================================================
-- Step 9: Administrative Procedures
-- ============================================================================

-- Procedure to grant tenant access to user
CREATE OR ALTER PROCEDURE security.sp_grant_tenant_access
    @user_principal NVARCHAR(128),
    @tenant_id INT,
    @valid_days INT = 365
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        INSERT INTO security.user_tenant_access
        (user_principal, tenant_id, is_active, valid_from, valid_to, granted_by)
        VALUES
        (
            @user_principal,
            @tenant_id,
            1,
            GETUTCDATE(),
            DATEADD(DAY, @valid_days, GETUTCDATE()),
            SYSTEM_USER
        );

        PRINT 'Granted tenant access: ' + @user_principal + ' -> Tenant ' + CAST(@tenant_id AS NVARCHAR(10));
    END TRY
    BEGIN CATCH
        PRINT 'Error granting access: ' + ERROR_MESSAGE();
        THROW;
    END CATCH
END
GO

-- Procedure to revoke tenant access
CREATE OR ALTER PROCEDURE security.sp_revoke_tenant_access
    @user_principal NVARCHAR(128),
    @tenant_id INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        UPDATE security.user_tenant_access
        SET is_active = 0,
            valid_to = GETUTCDATE()
        WHERE user_principal = @user_principal
        AND tenant_id = @tenant_id
        AND is_active = 1;

        PRINT 'Revoked tenant access: ' + @user_principal + ' -> Tenant ' + CAST(@tenant_id AS NVARCHAR(10));
    END TRY
    BEGIN CATCH
        PRINT 'Error revoking access: ' + ERROR_MESSAGE();
        THROW;
    END CATCH
END
GO

-- Procedure to audit RLS access attempts
CREATE OR ALTER PROCEDURE security.sp_audit_rls_access
    @user_principal NVARCHAR(128),
    @table_name NVARCHAR(128),
    @access_type NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    -- Log to audit table
    INSERT INTO governance.rls_access_audit
    (user_principal, table_name, access_type, access_time, session_context)
    VALUES
    (
        @user_principal,
        @table_name,
        @access_type,
        GETUTCDATE(),
        (SELECT SESSION_CONTEXT(N'tenant_id'))
    );
END
GO

-- ============================================================================
-- Step 10: Disable/Enable RLS Policies (for maintenance)
-- ============================================================================

-- Temporarily disable RLS (requires ALTER ANY SECURITY POLICY permission)
/*
ALTER SECURITY POLICY security.tenant_isolation_policy
WITH (STATE = OFF);
GO

-- Re-enable RLS
ALTER SECURITY POLICY security.tenant_isolation_policy
WITH (STATE = ON);
GO
*/

-- Drop RLS policy (for cleanup/testing)
/*
DROP SECURITY POLICY IF EXISTS security.tenant_isolation_policy;
DROP SECURITY POLICY IF EXISTS security.regional_data_policy;
GO
*/

-- ============================================================================
-- Step 11: Performance Considerations
-- ============================================================================

-- Create indexes on RLS predicate columns for better performance
CREATE NONCLUSTERED INDEX IX_customer_transactions_tenant
ON production.customer_transactions(tenant_id)
INCLUDE (customer_id, transaction_date, amount);
GO

CREATE NONCLUSTERED INDEX IX_customers_region
ON production.customers(region)
INCLUDE (customer_id, first_name, last_name);
GO

-- Update statistics for RLS tables
UPDATE STATISTICS security.user_tenant_access;
UPDATE STATISTICS security.user_region_access;
GO

-- ============================================================================
-- Summary and Best Practices
-- ============================================================================

PRINT '========================================================================';
PRINT 'Row-Level Security (RLS) Implementation Complete!';
PRINT '========================================================================';
PRINT '';
PRINT 'Security Policies Applied:';
PRINT '  - Tenant isolation on production.customer_transactions';
PRINT '  - Regional access control on production.customers';
PRINT '';
PRINT 'Best Practices:';
PRINT '  1. Always use SCHEMABINDING for predicate functions';
PRINT '  2. Index columns used in RLS predicates for performance';
PRINT '  3. Use SESSION_CONTEXT for application-driven filtering';
PRINT '  4. Replicate security mapping tables for low latency';
PRINT '  5. Regularly audit user access mappings';
PRINT '  6. Test RLS policies with different user contexts';
PRINT '  7. Document security policies and their purpose';
PRINT '  8. Monitor query performance impact of RLS';
PRINT '';
PRINT 'Next Steps:';
PRINT '  1. Configure application to set SESSION_CONTEXT on connection';
PRINT '  2. Grant appropriate permissions to users/roles';
PRINT '  3. Test with actual user accounts';
PRINT '  4. Set up monitoring for RLS-related performance issues';
PRINT '  5. Create runbook for managing user access';
PRINT '========================================================================';
GO
