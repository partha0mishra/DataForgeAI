-- ============================================================================
-- Azure Synapse Always Encrypted - Column-Level Encryption Setup
-- ============================================================================
-- This script sets up Always Encrypted for PII columns using Azure Key Vault
--
-- Prerequisites:
-- 1. Azure Key Vault with appropriate access policies
-- 2. Service Principal with Key Vault permissions
-- 3. SQL Server Management Studio (SSMS) with Always Encrypted enabled
-- 4. ALTER ANY COLUMN MASTER KEY and ALTER ANY COLUMN ENCRYPTION KEY permissions
--
-- Security Benefits:
-- - Data encrypted at rest and in transit
-- - Encryption keys stored in Azure Key Vault (external to database)
-- - Transparent encryption/decryption for authorized clients
-- - Protection against DBA access to sensitive data
-- ============================================================================

USE analytics;
GO

-- ============================================================================
-- Step 1: Create Column Master Key (CMK) in Azure Key Vault
-- ============================================================================
-- The Column Master Key is stored in Azure Key Vault, never in the database
-- This provides separation of duties and enhanced security

-- Check if Column Master Key exists
IF NOT EXISTS (
    SELECT * FROM sys.column_master_keys
    WHERE name = 'CMK_AzureKeyVault_PII'
)
BEGIN
    CREATE COLUMN MASTER KEY [CMK_AzureKeyVault_PII]
    WITH
    (
        KEY_STORE_PROVIDER_NAME = N'AZURE_KEY_VAULT',
        KEY_PATH = N'https://your-keyvault.vault.azure.net/keys/SynapsePIIKey/1234567890abcdef1234567890abcdef'
    );

    PRINT 'Column Master Key created: CMK_AzureKeyVault_PII';
END
ELSE
BEGIN
    PRINT 'Column Master Key already exists: CMK_AzureKeyVault_PII';
END
GO

-- ============================================================================
-- Step 2: Create Column Encryption Keys (CEK)
-- ============================================================================
-- Column Encryption Keys are encrypted by the Column Master Key
-- Different CEKs for different PII types provide granular key rotation

-- CEK for SSN (Social Security Number)
IF NOT EXISTS (
    SELECT * FROM sys.column_encryption_keys
    WHERE name = 'CEK_SSN'
)
BEGIN
    CREATE COLUMN ENCRYPTION KEY [CEK_SSN]
    WITH VALUES
    (
        COLUMN_MASTER_KEY = [CMK_AzureKeyVault_PII],
        ALGORITHM = 'RSA_OAEP',
        ENCRYPTED_VALUE = 0x... -- This is generated automatically by SSMS or Azure portal
    );

    PRINT 'Column Encryption Key created: CEK_SSN';
END
GO

-- CEK for Credit Card Numbers
IF NOT EXISTS (
    SELECT * FROM sys.column_encryption_keys
    WHERE name = 'CEK_CreditCard'
)
BEGIN
    CREATE COLUMN ENCRYPTION KEY [CEK_CreditCard]
    WITH VALUES
    (
        COLUMN_MASTER_KEY = [CMK_AzureKeyVault_PII],
        ALGORITHM = 'RSA_OAEP',
        ENCRYPTED_VALUE = 0x... -- This is generated automatically
    );

    PRINT 'Column Encryption Key created: CEK_CreditCard';
END
GO

-- CEK for Email addresses
IF NOT EXISTS (
    SELECT * FROM sys.column_encryption_keys
    WHERE name = 'CEK_Email'
)
BEGIN
    CREATE COLUMN ENCRYPTION KEY [CEK_Email]
    WITH VALUES
    (
        COLUMN_MASTER_KEY = [CMK_AzureKeyVault_PII],
        ALGORITHM = 'RSA_OAEP',
        ENCRYPTED_VALUE = 0x...
    );

    PRINT 'Column Encryption Key created: CEK_Email';
END
GO

-- ============================================================================
-- Step 3: Create Tables with Encrypted Columns
-- ============================================================================

-- Create schema for production data
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'production')
BEGIN
    EXEC('CREATE SCHEMA production');
    PRINT 'Schema created: production';
END
GO

-- Create customer table with encrypted PII columns
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'customers' AND schema_id = SCHEMA_ID('production'))
BEGIN
    CREATE TABLE production.customers
    (
        customer_id         INT IDENTITY(1,1) PRIMARY KEY,
        first_name          NVARCHAR(100) NOT NULL,
        last_name           NVARCHAR(100) NOT NULL,

        -- Encrypted columns with deterministic encryption (allows equality comparison)
        ssn                 NVARCHAR(11)
                            COLLATE Latin1_General_BIN2
                            ENCRYPTED WITH (
                                COLUMN_ENCRYPTION_KEY = [CEK_SSN],
                                ENCRYPTION_TYPE = Deterministic,
                                ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
                            ),

        -- Encrypted with randomized encryption (highest security, no operations allowed)
        credit_card_number  NVARCHAR(20)
                            COLLATE Latin1_General_BIN2
                            ENCRYPTED WITH (
                                COLUMN_ENCRYPTION_KEY = [CEK_CreditCard],
                                ENCRYPTION_TYPE = Randomized,
                                ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
                            ),

        -- Email with deterministic encryption (allows searching)
        email               NVARCHAR(255)
                            COLLATE Latin1_General_BIN2
                            ENCRYPTED WITH (
                                COLUMN_ENCRYPTION_KEY = [CEK_Email],
                                ENCRYPTION_TYPE = Deterministic,
                                ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
                            ),

        -- Non-encrypted columns
        phone_number        NVARCHAR(50),
        address_line1       NVARCHAR(255),
        address_line2       NVARCHAR(255),
        city                NVARCHAR(100),
        state               NVARCHAR(50),
        zip_code            NVARCHAR(20),
        country             NVARCHAR(50) DEFAULT 'USA',

        -- Audit columns
        created_at          DATETIME2 DEFAULT GETUTCDATE(),
        created_by          NVARCHAR(100) DEFAULT SYSTEM_USER,
        updated_at          DATETIME2 DEFAULT GETUTCDATE(),
        updated_by          NVARCHAR(100) DEFAULT SYSTEM_USER
    )
    WITH
    (
        DISTRIBUTION = HASH(customer_id),
        CLUSTERED COLUMNSTORE INDEX
    );

    PRINT 'Table created: production.customers with encrypted columns';
END
GO

-- Create transaction table with encrypted columns
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'customer_transactions' AND schema_id = SCHEMA_ID('production'))
BEGIN
    CREATE TABLE production.customer_transactions
    (
        transaction_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
        customer_id         INT NOT NULL,
        transaction_date    DATETIME2 NOT NULL,
        amount              DECIMAL(18,2) NOT NULL,
        transaction_type    NVARCHAR(50) NOT NULL,

        -- Encrypted payment information
        cc_encrypted        VARBINARY(MAX)
                            ENCRYPTED WITH (
                                COLUMN_ENCRYPTION_KEY = [CEK_CreditCard],
                                ENCRYPTION_TYPE = Randomized,
                                ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
                            ),

        ssn_encrypted       VARBINARY(MAX)
                            ENCRYPTED WITH (
                                COLUMN_ENCRYPTION_KEY = [CEK_SSN],
                                ENCRYPTION_TYPE = Deterministic,
                                ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
                            ),

        -- Non-encrypted fields
        email               NVARCHAR(255),
        phone_number        NVARCHAR(50),
        modified_date       DATETIME2 DEFAULT GETUTCDATE(),
        created_at          DATETIME2 DEFAULT GETUTCDATE(),
        updated_at          DATETIME2 DEFAULT GETUTCDATE()
    )
    WITH
    (
        DISTRIBUTION = HASH(customer_id),
        CLUSTERED COLUMNSTORE INDEX
    );

    PRINT 'Table created: production.customer_transactions with encrypted columns';
END
GO

-- ============================================================================
-- Step 4: Encrypt Existing Columns (if migrating existing tables)
-- ============================================================================

-- If you have an existing table without encryption, use ALTER TABLE
-- WARNING: This requires a table rebuild and can be time-consuming

/*
-- Example: Encrypt existing SSN column
ALTER TABLE production.customers
ALTER COLUMN ssn
    NVARCHAR(11) COLLATE Latin1_General_BIN2
    ENCRYPTED WITH (
        COLUMN_ENCRYPTION_KEY = [CEK_SSN],
        ENCRYPTION_TYPE = Deterministic,
        ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
    );
GO
*/

-- ============================================================================
-- Step 5: Create Views with Decryption (for authorized users)
-- ============================================================================

-- View for customer service representatives (partial PII access)
CREATE OR ALTER VIEW production.vw_customers_masked AS
SELECT
    customer_id,
    first_name,
    last_name,
    -- Show last 4 digits of SSN only
    'XXX-XX-' + RIGHT(ssn, 4) AS ssn_masked,
    -- Show masked email
    LEFT(email, 1) + '***@' + SUBSTRING(email, CHARINDEX('@', email) + 1, LEN(email)) AS email_masked,
    phone_number,
    city,
    state,
    zip_code,
    created_at,
    updated_at
FROM production.customers;
GO

-- View for compliance officers (full access with audit)
CREATE OR ALTER VIEW production.vw_customers_full_access AS
SELECT
    customer_id,
    first_name,
    last_name,
    ssn,  -- Decrypted automatically for authorized users
    credit_card_number,
    email,
    phone_number,
    address_line1,
    address_line2,
    city,
    state,
    zip_code,
    created_at,
    updated_at,
    -- Audit who accessed PII
    SYSTEM_USER AS accessed_by,
    GETUTCDATE() AS accessed_at
FROM production.customers;
GO

-- ============================================================================
-- Step 6: Dynamic Data Masking (additional layer of security)
-- ============================================================================

-- Apply dynamic data masking to non-encrypted PII columns
-- This masks data for users without UNMASK permission

ALTER TABLE production.customers
ALTER COLUMN phone_number ADD MASKED WITH (FUNCTION = 'partial(1,"XXX-XXX-",4)');
GO

ALTER TABLE production.customer_transactions
ALTER COLUMN email ADD MASKED WITH (FUNCTION = 'email()');
GO

ALTER TABLE production.customer_transactions
ALTER COLUMN phone_number ADD MASKED WITH (FUNCTION = 'partial(1,"XXX-XXX-",4)');
GO

-- ============================================================================
-- Step 7: Grant Permissions
-- ============================================================================

-- Create role for users who can view masked data
CREATE ROLE customer_service_role;
GO

GRANT SELECT ON production.vw_customers_masked TO customer_service_role;
GO

-- Create role for compliance users with full PII access
CREATE ROLE compliance_officer_role;
GO

GRANT SELECT ON production.vw_customers_full_access TO compliance_officer_role;
GRANT UNMASK TO compliance_officer_role;  -- Allow viewing unmasked data
GO

-- Grant VIEW ANY COLUMN MASTER KEY DEFINITION for encryption-aware applications
-- GRANT VIEW ANY COLUMN MASTER KEY DEFINITION TO [application_service_principal];
-- GRANT VIEW ANY COLUMN ENCRYPTION KEY DEFINITION TO [application_service_principal];
GO

-- ============================================================================
-- Step 8: Test Encryption
-- ============================================================================

-- Insert test data (requires Always Encrypted enabled connection)
/*
INSERT INTO production.customers
(first_name, last_name, ssn, credit_card_number, email, phone_number, city, state, zip_code)
VALUES
('John', 'Doe', '123-45-6789', '4111111111111111', 'john.doe@example.com', '555-123-4567', 'New York', 'NY', '10001'),
('Jane', 'Smith', '987-65-4321', '5500000000000004', 'jane.smith@example.com', '555-987-6543', 'Los Angeles', 'CA', '90001');
GO
*/

-- Query encrypted data (authorized users see decrypted values)
-- SELECT * FROM production.customers WHERE ssn = '123-45-6789';
-- GO

-- Query through masked view (customer service sees masked data)
-- SELECT * FROM production.vw_customers_masked;
-- GO

-- ============================================================================
-- Step 9: Key Rotation Procedure
-- ============================================================================

-- Create stored procedure for rotating encryption keys
CREATE OR ALTER PROCEDURE production.sp_rotate_column_encryption_key
    @key_name NVARCHAR(128)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @msg NVARCHAR(500);
    DECLARE @rotation_date DATETIME2 = GETUTCDATE();

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Log rotation start
        INSERT INTO governance.encryption_key_rotation_log
        (key_name, rotation_date, status, initiated_by)
        VALUES (@key_name, @rotation_date, 'STARTED', SYSTEM_USER);

        -- Generate new key in Azure Key Vault (this must be done externally)
        -- Then update the Column Encryption Key

        -- Example for CEK_SSN
        IF @key_name = 'CEK_SSN'
        BEGIN
            -- Add new encrypted value with new CMK version
            ALTER COLUMN ENCRYPTION KEY [CEK_SSN]
            ADD VALUE
            (
                COLUMN_MASTER_KEY = [CMK_AzureKeyVault_PII],
                ALGORITHM = 'RSA_OAEP',
                ENCRYPTED_VALUE = 0x... -- New encrypted value from Key Vault
            );

            -- Drop old encrypted value after migration
            -- ALTER COLUMN ENCRYPTION KEY [CEK_SSN] DROP VALUE (ENCRYPTED_VALUE = 0x...);
        END

        -- Log rotation completion
        UPDATE governance.encryption_key_rotation_log
        SET status = 'COMPLETED', completed_at = GETUTCDATE()
        WHERE key_name = @key_name AND rotation_date = @rotation_date;

        COMMIT TRANSACTION;

        SET @msg = 'Successfully rotated encryption key: ' + @key_name;
        PRINT @msg;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        -- Log rotation failure
        INSERT INTO governance.encryption_key_rotation_log
        (key_name, rotation_date, status, error_message, initiated_by)
        VALUES (@key_name, @rotation_date, 'FAILED', ERROR_MESSAGE(), SYSTEM_USER);

        THROW;
    END CATCH
END
GO

-- ============================================================================
-- Step 10: Monitoring and Compliance Queries
-- ============================================================================

-- Query to check encrypted columns
SELECT
    t.name AS table_name,
    c.name AS column_name,
    c.encryption_type_desc,
    cek.name AS encryption_key_name,
    cmk.name AS master_key_name
FROM sys.columns c
INNER JOIN sys.tables t ON c.object_id = t.object_id
LEFT JOIN sys.column_encryption_keys cek ON c.column_encryption_key_id = cek.column_encryption_key_id
LEFT JOIN sys.column_master_keys cmk ON cek.column_master_key_id = cmk.column_master_key_id
WHERE c.encryption_type IS NOT NULL
ORDER BY t.name, c.name;
GO

-- Query to check data masking
SELECT
    t.name AS table_name,
    c.name AS column_name,
    c.masking_function
FROM sys.masked_columns c
INNER JOIN sys.tables t ON c.object_id = t.object_id
ORDER BY t.name, c.name;
GO

PRINT 'Always Encrypted setup complete!';
PRINT 'Next steps:';
PRINT '1. Configure client applications with Column Encryption Setting=Enabled';
PRINT '2. Grant appropriate permissions to service principals';
PRINT '3. Test encryption/decryption with authorized and unauthorized users';
PRINT '4. Set up regular key rotation schedule';
PRINT '5. Monitor access through audit logs';
GO
