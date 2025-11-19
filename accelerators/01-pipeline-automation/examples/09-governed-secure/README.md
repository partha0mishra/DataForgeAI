# Example 09: Governed + Secure (Zero-Trust Ready)

**Pass the security audit**

## Overview

Secure pipeline from on-prem SQL Server → Azure Synapse: use Azure AD passthrough authentication, column-level encryption, row-level security, and full audit logging to Microsoft Purview.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ SQL Server      │────▶│ Secure Gateway  │────▶│ Azure Synapse    │
│ (On-prem)       │     │ - AD Auth       │     │ - Column Encrypt │
│                 │     │ - TLS 1.3       │     │ - Row-level Sec  │
└─────────────────┘     └─────────────────┘     └──────────────────┘
                                                          │
                                                          ▼
                                                 ┌──────────────────┐
                                                 │ Microsoft Purview│
                                                 │ (Audit Logs)     │
                                                 └──────────────────┘
```

## Use Case

Enterprise security requirements. Shows:
- Azure AD authentication (no passwords in code)
- Column-level encryption for PII
- Row-level security (RLS) for multi-tenancy
- Audit logging to Purview
- Private endpoints (no public internet)
- Zero-trust architecture

## Prerequisites

- **SQL Server:** On-premises or Azure VM
- **Azure Synapse:** Workspace created
- **Microsoft Purview:** Account configured
- **Azure AD:** Service principal with permissions

## Quick Start

```bash
# Configure Azure AD authentication
az ad sp create-for-rbac --name data-pipeline-sp

# Deploy Synapse workspace with private endpoints
cd terraform/
terraform apply -var="enable_private_endpoints=true"

# Set up column encryption
sqlcmd -S synapse-workspace.sql.azuresynapse.net \
  -d analytics -i security/column_encryption.sql

# Configure RLS policies
sqlcmd -S synapse-workspace.sql.azuresynapse.net \
  -d analytics -i security/rls_policies.sql
```

## Expected Results

- Zero passwords stored in code (all Azure AD)
- PII columns encrypted at rest
- Users only see rows they're authorized for
- All access logged to Purview
- Compliance reports available

## What You'll Learn

- ✅ Azure AD integrated authentication
- ✅ Managed identities for services
- ✅ Column-level encryption (Always Encrypted)
- ✅ Row-level security policies
- ✅ Private endpoints configuration
- ✅ Audit logging to Purview
- ✅ Data classification and lineage

## File Structure

```
09-governed-secure/
├── README.md
├── config.yaml
├── airflow/
│   └── secure_synapse_dag.py         # Secure pipeline
├── security/
│   ├── azure_ad_setup.md             # AD configuration guide
│   ├── encryption_config.yaml        # Column encryption config
│   ├── column_encryption.sql         # Encryption DDL
│   └── rls_policies.sql              # Row-level security
└── compliance/
    └── audit_log_queries.sql         # Audit queries for reports
```

## Configuration

```yaml
azure:
  tenant_id: ${AZURE_TENANT_ID}
  subscription_id: ${AZURE_SUBSCRIPTION_ID}

synapse:
  workspace: mycompany-synapse
  sql_pool: analytics_pool
  authentication: azure_ad
  managed_identity: data-pipeline-sp

security:
  encryption:
    enabled: true
    key_vault: mycompany-kv
    columns:
      - table: customers
        column: ssn
        encryption_type: deterministic
      - table: customers
        column: credit_card
        encryption_type: randomized

  row_level_security:
    enabled: true
    policies:
      - table: sales
        predicate: user_region = CURRENT_USER_REGION()
      - table: customers
        predicate: tenant_id = CURRENT_TENANT_ID()

purview:
  account: mycompany-purview
  collection: data-platform
  scan_frequency: daily
```

## Security Features

### 1. Azure AD Authentication

```python
# No passwords in code!
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
synapse_client = SynapseClient(
    credential=credential,
    workspace_url="https://mycompany-synapse.sql.azuresynapse.net"
)
```

### 2. Column-Level Encryption

```sql
-- Encrypt SSN column
ALTER TABLE customers
ALTER COLUMN ssn ADD MASKED WITH (FUNCTION = 'partial(0,"XXX-XX-",4)');

-- Always Encrypted (application-level)
CREATE COLUMN MASTER KEY MyCMK
WITH (
  KEY_STORE_PROVIDER_NAME = 'AZURE_KEY_VAULT',
  KEY_PATH = 'https://mycompany-kv.vault.azure.net/keys/column-key'
);
```

### 3. Row-Level Security

```sql
-- Create security predicate
CREATE FUNCTION dbo.fn_security_predicate(@tenant_id int)
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN SELECT 1 AS result
WHERE @tenant_id = CAST(SESSION_CONTEXT(N'tenant_id') AS int);

-- Apply to table
CREATE SECURITY POLICY tenant_filter
ADD FILTER PREDICATE dbo.fn_security_predicate(tenant_id) ON dbo.sales;
```

### 4. Audit Logging

```sql
-- Query audit logs in Purview
SELECT
  event_time,
  user_principal_name,
  operation_name,
  target_resource,
  result_status
FROM audit_logs
WHERE event_time > DATEADD(day, -7, GETDATE())
ORDER BY event_time DESC;
```

## Implementation Status

🚧 **Coming Soon** - This example is under development.

**Planned components:**
- [ ] Azure AD integration scripts
- [ ] Column encryption setup automation
- [ ] RLS policy templates
- [ ] Purview scan configuration
- [ ] Private endpoint deployment
- [ ] Compliance checklist
- [ ] Security assessment report

## Security Checklist

- [ ] All authentication via Azure AD (no SQL auth)
- [ ] Managed identities for service-to-service
- [ ] TLS 1.3 for all connections
- [ ] PII columns encrypted
- [ ] RLS policies applied to multi-tenant tables
- [ ] Private endpoints (no public internet)
- [ ] Firewall rules configured
- [ ] Audit logging enabled
- [ ] Data classification applied
- [ ] Regular security scans

## Compliance Reports

```sql
-- PII Data Discovery
SELECT
  schema_name,
  table_name,
  column_name,
  sensitivity_label,
  information_type
FROM sys.sensitivity_classifications;

-- Access Audit (last 30 days)
SELECT
  user_name,
  COUNT(*) as access_count,
  MAX(event_time) as last_access
FROM audit_logs
WHERE event_time > DATEADD(day, -30, GETDATE())
  AND operation_name = 'SELECT'
GROUP BY user_name;
```

## Troubleshooting

### Azure AD Authentication Failed

```bash
# Verify service principal
az ad sp show --id <service-principal-id>

# Check role assignments
az role assignment list --assignee <service-principal-id>

# Grant Synapse permissions
az synapse role assignment create \
  --workspace-name mycompany-synapse \
  --role "Synapse SQL Administrator" \
  --assignee <service-principal-id>
```

### RLS Not Working

```sql
-- Check if policy is enabled
SELECT * FROM sys.security_policies WHERE name = 'tenant_filter';

-- Verify session context
SELECT SESSION_CONTEXT(N'tenant_id');

-- Set session context for testing
EXEC sp_set_session_context @key = N'tenant_id', @value = 123;
```

## Next Steps

- Try **Example 10** for AI/ML pipelines
- Implement **Data Catalog** with Accelerator 04
- Add **Cost Monitoring** from Example 08

## Resources

- [Azure Synapse Security](https://docs.microsoft.com/azure/synapse-analytics/security/synapse-workspace-synapse-rbac)
- [Microsoft Purview](https://docs.microsoft.com/azure/purview/)
- [Row-Level Security](https://docs.microsoft.com/sql/relational-databases/security/row-level-security)
- [Always Encrypted](https://docs.microsoft.com/sql/relational-databases/security/encryption/always-encrypted-database-engine)
