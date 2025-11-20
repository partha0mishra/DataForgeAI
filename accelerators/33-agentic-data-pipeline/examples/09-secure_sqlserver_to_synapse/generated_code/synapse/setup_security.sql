-- Synapse Security Setup
-- Column-level encryption, row-level security, and dynamic data masking

-- Enable Always Encrypted for sensitive columns
CREATE COLUMN MASTER KEY [CMK_Auto1]
WITH (
    KEY_STORE_PROVIDER_NAME = 'AZURE_KEY_VAULT',
    KEY_PATH = 'https://your-keyvault.vault.azure.net/keys/synapse-cmk/version'
);

CREATE COLUMN ENCRYPTION KEY [CEK_Auto1]
WITH VALUES (
    COLUMN_MASTER_KEY = [CMK_Auto1],
    ALGORITHM = 'RSA_OAEP',
    ENCRYPTED_VALUE = 0x...
);

-- Create Customers table with encrypted columns
CREATE TABLE dbo.Customers (
    CustomerID VARCHAR(50) NOT NULL,
    FirstName NVARCHAR(100),
    LastName NVARCHAR(100),
    Email NVARCHAR(256) ENCRYPTED WITH (
        COLUMN_ENCRYPTION_KEY = [CEK_Auto1],
        ENCRYPTION_TYPE = Deterministic,
        ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
    ),
    Phone NVARCHAR(20) ENCRYPTED WITH (
        COLUMN_ENCRYPTION_KEY = [CEK_Auto1],
        ENCRYPTION_TYPE = Deterministic,
        ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
    ),
    SSN NVARCHAR(11) ENCRYPTED WITH (
        COLUMN_ENCRYPTION_KEY = [CEK_Auto1],
        ENCRYPTION_TYPE = Randomized,
        ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
    ),
    Region NVARCHAR(50),
    ModifiedDate DATETIME2,
    PRIMARY KEY (CustomerID)
);

-- Create Orders table
CREATE TABLE dbo.Orders (
    OrderID VARCHAR(50) NOT NULL,
    CustomerID VARCHAR(50),
    OrderDate DATETIME2,
    Amount DECIMAL(18,2),
    ModifiedDate DATETIME2,
    PRIMARY KEY (OrderID)
);

-- Row-Level Security
CREATE SCHEMA Security;
GO

CREATE FUNCTION Security.fn_RegionPredicate(@Region AS NVARCHAR(50))
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN SELECT 1 AS fn_RegionPredicate_result
WHERE @Region = USER_NAME() OR IS_MEMBER('DataEngineers') = 1;
GO

CREATE SECURITY POLICY RegionFilter
ADD FILTER PREDICATE Security.fn_RegionPredicate(Region)
ON dbo.Customers
WITH (STATE = ON);

-- Dynamic Data Masking
ALTER TABLE dbo.Customers
ALTER COLUMN Email ADD MASKED WITH (FUNCTION = 'email()');

ALTER TABLE dbo.Customers
ALTER COLUMN SSN ADD MASKED WITH (FUNCTION = 'default()');

-- Create roles and grant permissions
CREATE ROLE DataEngineers;
CREATE ROLE DataAnalysts;

GRANT SELECT, INSERT, UPDATE ON dbo.Customers TO DataEngineers;
GRANT SELECT, INSERT, UPDATE ON dbo.Orders TO DataEngineers;

GRANT SELECT ON dbo.Customers TO DataAnalysts;
GRANT SELECT ON dbo.Orders TO DataAnalysts;

-- Unmask permission for engineers
GRANT UNMASK TO DataEngineers;
