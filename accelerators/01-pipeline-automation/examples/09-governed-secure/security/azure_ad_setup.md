# Azure AD Setup for Secure Synapse Pipeline

This guide provides step-by-step instructions for setting up Azure Active Directory authentication, managed identities, and Key Vault integration for the secure Synapse ETL pipeline.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Create Service Principal](#create-service-principal)
3. [Configure Managed Identity](#configure-managed-identity)
4. [Set Up Azure Key Vault](#set-up-azure-key-vault)
5. [Configure Private Endpoints](#configure-private-endpoints)
6. [Grant Permissions](#grant-permissions)
7. [Test Authentication](#test-authentication)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- Azure subscription with Owner or Contributor role
- Azure CLI installed (`az --version`)
- PowerShell 7+ (optional, for PowerShell commands)
- Access to Azure Portal
- Permissions to create Azure AD applications and service principals

---

## 1. Create Service Principal

### Option A: Using Azure CLI

```bash
# Login to Azure
az login

# Set subscription context
az account set --subscription "your-subscription-id"

# Create service principal for Airflow
az ad sp create-for-rbac \
  --name "sp-airflow-synapse-etl" \
  --role "Contributor" \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group-name}

# Output will include:
# - appId (Client ID)
# - password (Client Secret)
# - tenant (Tenant ID)
#
# IMPORTANT: Save these values securely - the password cannot be retrieved later!
```

### Option B: Using Azure Portal

1. Navigate to **Azure Active Directory** > **App registrations**
2. Click **New registration**
3. Configure:
   - Name: `sp-airflow-synapse-etl`
   - Supported account types: **Single tenant**
   - Redirect URI: Leave blank
4. Click **Register**
5. Note the **Application (client) ID** and **Directory (tenant) ID**
6. Go to **Certificates & secrets** > **New client secret**
   - Description: `Airflow ETL Secret`
   - Expires: Choose appropriate expiration (e.g., 24 months)
7. Click **Add** and immediately **copy the secret value**

### Assign Permissions to Service Principal

```bash
# Get the service principal object ID
SP_OBJECT_ID=$(az ad sp show --id <appId> --query objectId -o tsv)

# Grant SQL Database Contributor role
az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "SQL DB Contributor" \
  --scope /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Sql/servers/{synapse-workspace}

# Grant Storage Blob Data Contributor (if accessing ADLS Gen2)
az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Storage/storageAccounts/{storage-account}
```

---

## 2. Configure Managed Identity

Managed identities eliminate the need for credentials in code by using Azure AD authentication.

### Create System-Assigned Managed Identity for Azure VM/AKS

If running Airflow on Azure VM or AKS:

```bash
# For Azure VM
az vm identity assign \
  --name airflow-vm \
  --resource-group your-resource-group

# For AKS (pod identity)
az aks pod-identity add \
  --cluster-name airflow-aks-cluster \
  --resource-group your-resource-group \
  --namespace airflow \
  --name airflow-identity \
  --identity-resource-id /subscriptions/{sub-id}/resourcegroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/airflow-identity
```

### Create User-Assigned Managed Identity

```bash
# Create user-assigned managed identity
az identity create \
  --name airflow-managed-identity \
  --resource-group your-resource-group \
  --location eastus

# Get the identity details
IDENTITY_CLIENT_ID=$(az identity show \
  --name airflow-managed-identity \
  --resource-group your-resource-group \
  --query clientId -o tsv)

IDENTITY_PRINCIPAL_ID=$(az identity show \
  --name airflow-managed-identity \
  --resource-group your-resource-group \
  --query principalId -o tsv)

echo "Client ID: $IDENTITY_CLIENT_ID"
echo "Principal ID: $IDENTITY_PRINCIPAL_ID"
```

### Assign Managed Identity to Azure Resources

```bash
# Assign to Azure VM
az vm identity assign \
  --name airflow-vm \
  --resource-group your-resource-group \
  --identities /subscriptions/{sub-id}/resourcegroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/airflow-managed-identity

# Assign to App Service (if using Azure App Service for Airflow)
az webapp identity assign \
  --name airflow-webapp \
  --resource-group your-resource-group \
  --identities /subscriptions/{sub-id}/resourcegroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/airflow-managed-identity
```

---

## 3. Set Up Azure Key Vault

Azure Key Vault stores sensitive credentials, connection strings, and encryption keys.

### Create Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name kv-airflow-synapse-prod \
  --resource-group your-resource-group \
  --location eastus \
  --enable-soft-delete true \
  --enable-purge-protection true \
  --enable-rbac-authorization false

# Enable network access (optional - configure based on security requirements)
az keyvault network-rule add \
  --name kv-airflow-synapse-prod \
  --resource-group your-resource-group \
  --ip-address <your-ip-address>
```

### Grant Access to Managed Identity

```bash
# Grant Key Vault Secrets User role to managed identity
az role assignment create \
  --assignee $IDENTITY_PRINCIPAL_ID \
  --role "Key Vault Secrets User" \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/kv-airflow-synapse-prod

# Or use access policies (legacy method)
az keyvault set-policy \
  --name kv-airflow-synapse-prod \
  --object-id $IDENTITY_PRINCIPAL_ID \
  --secret-permissions get list \
  --key-permissions get list \
  --certificate-permissions get list
```

### Store Secrets in Key Vault

```bash
# Store on-premises SQL Server connection string
az keyvault secret set \
  --vault-name kv-airflow-synapse-prod \
  --name "sql-onprem-sqlserver-connection" \
  --value "Driver={ODBC Driver 18 for SQL Server};Server=onprem-sql.company.com;Database=Production;UID=etl_user;PWD=<password>;Encrypt=yes;TrustServerCertificate=no;"

# Store Synapse connection details (if using SQL auth)
az keyvault secret set \
  --vault-name kv-airflow-synapse-prod \
  --name "synapse-server" \
  --value "your-synapse.sql.azuresynapse.net"

az keyvault secret set \
  --vault-name kv-airflow-synapse-prod \
  --name "synapse-database" \
  --value "analytics"

# Store Application Insights instrumentation key
az keyvault secret set \
  --vault-name kv-airflow-synapse-prod \
  --name "appinsights-instrumentation-key" \
  --value "<your-instrumentation-key>"
```

### Create Encryption Keys for Always Encrypted

```bash
# Create key for PII encryption
az keyvault key create \
  --vault-name kv-airflow-synapse-prod \
  --name SynapsePIIKey \
  --kty RSA \
  --size 2048 \
  --ops encrypt decrypt wrapKey unwrapKey

# Get the key identifier (use in SQL Server Always Encrypted setup)
az keyvault key show \
  --vault-name kv-airflow-synapse-prod \
  --name SynapsePIIKey \
  --query key.kid -o tsv
```

---

## 4. Configure Private Endpoints

Private endpoints ensure all traffic stays within the Azure backbone network.

### Create Private Endpoint for Synapse

```bash
# Create virtual network and subnet (if not exists)
az network vnet create \
  --name vnet-data-platform \
  --resource-group your-resource-group \
  --address-prefix 10.0.0.0/16 \
  --subnet-name subnet-private-endpoints \
  --subnet-prefix 10.0.1.0/24

# Disable private endpoint network policies
az network vnet subnet update \
  --name subnet-private-endpoints \
  --resource-group your-resource-group \
  --vnet-name vnet-data-platform \
  --disable-private-endpoint-network-policies true

# Create private endpoint for Synapse SQL
az network private-endpoint create \
  --name pe-synapse-sql \
  --resource-group your-resource-group \
  --vnet-name vnet-data-platform \
  --subnet subnet-private-endpoints \
  --private-connection-resource-id /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Synapse/workspaces/your-synapse-workspace \
  --group-id Sql \
  --connection-name synapse-sql-connection

# Create private DNS zone
az network private-dns zone create \
  --resource-group your-resource-group \
  --name privatelink.sql.azuresynapse.net

# Link DNS zone to VNet
az network private-dns link vnet create \
  --resource-group your-resource-group \
  --zone-name privatelink.sql.azuresynapse.net \
  --name synapse-dns-link \
  --virtual-network vnet-data-platform \
  --registration-enabled false

# Create DNS zone group
az network private-endpoint dns-zone-group create \
  --resource-group your-resource-group \
  --endpoint-name pe-synapse-sql \
  --name synapse-dns-zone-group \
  --private-dns-zone privatelink.sql.azuresynapse.net \
  --zone-name sql
```

### Create Private Endpoint for Key Vault

```bash
# Create private endpoint for Key Vault
az network private-endpoint create \
  --name pe-keyvault \
  --resource-group your-resource-group \
  --vnet-name vnet-data-platform \
  --subnet subnet-private-endpoints \
  --private-connection-resource-id /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/kv-airflow-synapse-prod \
  --group-id vault \
  --connection-name keyvault-connection

# Create private DNS zone for Key Vault
az network private-dns zone create \
  --resource-group your-resource-group \
  --name privatelink.vaultcore.azure.net

az network private-dns link vnet create \
  --resource-group your-resource-group \
  --zone-name privatelink.vaultcore.azure.net \
  --name keyvault-dns-link \
  --virtual-network vnet-data-platform \
  --registration-enabled false

az network private-endpoint dns-zone-group create \
  --resource-group your-resource-group \
  --endpoint-name pe-keyvault \
  --name keyvault-dns-zone-group \
  --private-dns-zone privatelink.vaultcore.azure.net \
  --zone-name vault
```

### Configure On-Premises VPN/ExpressRoute

For on-premises SQL Server connectivity:

```bash
# Create VPN Gateway (or use ExpressRoute)
az network vnet-gateway create \
  --name vpn-gateway-onprem \
  --resource-group your-resource-group \
  --vnet vnet-data-platform \
  --gateway-type Vpn \
  --vpn-type RouteBased \
  --sku VpnGw1 \
  --public-ip-address vpn-gateway-ip

# Create local network gateway (represents on-premises network)
az network local-gateway create \
  --name lng-onprem-datacenter \
  --resource-group your-resource-group \
  --gateway-ip-address <on-prem-public-ip> \
  --local-address-prefixes 192.168.0.0/16

# Create VPN connection
az network vpn-connection create \
  --name vpn-connection-onprem \
  --resource-group your-resource-group \
  --vnet-gateway1 vpn-gateway-onprem \
  --local-gateway2 lng-onprem-datacenter \
  --shared-key <pre-shared-key>
```

---

## 5. Grant Permissions

### Grant Synapse SQL Permissions to Managed Identity

Connect to Synapse SQL using SQL Server Management Studio (SSMS) or Azure Data Studio:

```sql
-- Create user from managed identity
CREATE USER [airflow-managed-identity] FROM EXTERNAL PROVIDER;

-- Grant database permissions
ALTER ROLE db_datareader ADD MEMBER [airflow-managed-identity];
ALTER ROLE db_datawriter ADD MEMBER [airflow-managed-identity];
ALTER ROLE db_ddladmin ADD MEMBER [airflow-managed-identity];

-- Grant schema permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::staging TO [airflow-managed-identity];
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::production TO [airflow-managed-identity];
GRANT SELECT ON SCHEMA::governance TO [airflow-managed-identity];

-- Grant specific table permissions for encrypted columns
GRANT VIEW ANY COLUMN MASTER KEY DEFINITION TO [airflow-managed-identity];
GRANT VIEW ANY COLUMN ENCRYPTION KEY DEFINITION TO [airflow-managed-identity];

-- Grant RLS bypass (if needed for ETL processes)
GRANT SELECT ON security.user_tenant_access TO [airflow-managed-identity];
```

### Grant Azure RBAC Permissions

```bash
# Storage permissions (for data lake access)
az role assignment create \
  --assignee $IDENTITY_PRINCIPAL_ID \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage-account}

# Synapse Administrator (if needed)
az role assignment create \
  --assignee $IDENTITY_PRINCIPAL_ID \
  --role "Synapse Administrator" \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Synapse/workspaces/your-synapse-workspace

# Log Analytics Reader (for audit logs)
az role assignment create \
  --assignee $IDENTITY_PRINCIPAL_ID \
  --role "Log Analytics Reader" \
  --scope /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces/log-analytics-workspace
```

---

## 6. Test Authentication

### Test Managed Identity from Python

```python
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
import pyodbc
import struct

# Test Key Vault access
credential = DefaultAzureCredential()
kv_url = "https://kv-airflow-synapse-prod.vault.azure.net/"
client = SecretClient(vault_url=kv_url, credential=credential)

try:
    secret = client.get_secret("synapse-server")
    print(f"✓ Key Vault access successful: {secret.value}")
except Exception as e:
    print(f"✗ Key Vault access failed: {e}")

# Test Synapse connection with Azure AD token
try:
    token = credential.get_token("https://database.windows.net/.default")
    token_bytes = token.token.encode('UTF-16-LE')
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)

    conn_str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        "Server=tcp:your-synapse.sql.azuresynapse.net,1433;"
        "Database=analytics;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    conn = pyodbc.connect(conn_str, attrs_before={1256: token_struct})
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    print(f"✓ Synapse connection successful: {cursor.fetchone()[0][:50]}")
    conn.close()
except Exception as e:
    print(f"✗ Synapse connection failed: {e}")
```

### Test with Azure CLI

```bash
# Test Key Vault access
az keyvault secret show \
  --vault-name kv-airflow-synapse-prod \
  --name synapse-server \
  --query value -o tsv

# Test Synapse access (requires Azure CLI with SQL extension)
az synapse sql pool list \
  --workspace-name your-synapse-workspace \
  --resource-group your-resource-group
```

---

## 7. Configure Airflow Connections

### Option A: Using Environment Variables

```bash
export AZURE_CLIENT_ID="<managed-identity-client-id>"
export AZURE_TENANT_ID="<your-tenant-id>"
export AZURE_KEYVAULT_URL="https://kv-airflow-synapse-prod.vault.azure.net/"
```

### Option B: Using Airflow Connections UI

1. Navigate to **Admin** > **Connections**
2. Add new connection:
   - Connection ID: `azure_synapse_default`
   - Connection Type: `Microsoft SQL Server`
   - Host: `your-synapse.sql.azuresynapse.net`
   - Schema: `analytics`
   - Login: Leave blank (using managed identity)
   - Password: Leave blank
   - Port: `1433`
   - Extra:
     ```json
     {
       "authentication": "ActiveDirectoryMsi",
       "driver": "ODBC Driver 18 for SQL Server",
       "Encrypt": "yes",
       "TrustServerCertificate": "no"
     }
     ```

---

## 8. Troubleshooting

### Common Issues and Solutions

#### Issue: "Login failed for user '<token-identified principal>'"

**Solution:**
```sql
-- Ensure user exists in Synapse
SELECT name, type_desc FROM sys.database_principals WHERE name = 'airflow-managed-identity';

-- If not exists, create it
CREATE USER [airflow-managed-identity] FROM EXTERNAL PROVIDER;
```

#### Issue: "AADSTS700016: Application not found in directory"

**Solution:**
- Verify the service principal still exists in Azure AD
- Check the client ID is correct
- Ensure the SP hasn't been deleted

```bash
az ad sp show --id <client-id>
```

#### Issue: "Key Vault access denied"

**Solution:**
```bash
# Check current access policies
az keyvault show --name kv-airflow-synapse-prod --query properties.accessPolicies

# Grant access if missing
az keyvault set-policy \
  --name kv-airflow-synapse-prod \
  --object-id $IDENTITY_PRINCIPAL_ID \
  --secret-permissions get list
```

#### Issue: "Cannot connect through private endpoint"

**Solution:**
- Verify DNS resolution:
  ```bash
  nslookup your-synapse.sql.azuresynapse.net
  # Should resolve to private IP (10.x.x.x)
  ```
- Check NSG rules allow traffic
- Verify subnet has privateEndpointNetworkPolicies disabled

#### Issue: "Token audience validation failed"

**Solution:**
- Ensure token audience is correct:
  ```python
  token = credential.get_token("https://database.windows.net/.default")
  # NOT "https://management.azure.com/.default"
  ```

### Enable Diagnostic Logging

```bash
# Enable Key Vault diagnostics
az monitor diagnostic-settings create \
  --name keyvault-diagnostics \
  --resource /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/kv-airflow-synapse-prod \
  --logs '[{"category": "AuditEvent", "enabled": true}]' \
  --workspace /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces/log-analytics-workspace

# Enable Synapse diagnostics
az synapse workspace audit-policy update \
  --workspace-name your-synapse-workspace \
  --resource-group your-resource-group \
  --state Enabled \
  --blob-storage-target-state Enabled \
  --storage-account /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage-account}
```

---

## Security Best Practices

1. **Use Managed Identities**: Eliminate credentials from code and configuration
2. **Enable Private Endpoints**: Keep traffic within Azure network
3. **Rotate Secrets**: Set expiration on service principal secrets (if used)
4. **Least Privilege**: Grant only necessary permissions
5. **Monitor Access**: Enable audit logging and review regularly
6. **Network Isolation**: Use VNets and NSGs to restrict access
7. **Conditional Access**: Configure Azure AD conditional access policies
8. **MFA**: Require multi-factor authentication for admin accounts

---

## Next Steps

1. Review and test all authentication flows
2. Configure monitoring and alerting
3. Document the architecture and access patterns
4. Set up automated secret rotation
5. Conduct security assessment and penetration testing
6. Create runbooks for common operational tasks

---

## Additional Resources

- [Azure AD Authentication Overview](https://docs.microsoft.com/azure/active-directory/authentication/)
- [Managed Identities for Azure Resources](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [Azure Key Vault Documentation](https://docs.microsoft.com/azure/key-vault/)
- [Azure Synapse Security](https://docs.microsoft.com/azure/synapse-analytics/security/)
- [Private Endpoints](https://docs.microsoft.com/azure/private-link/private-endpoint-overview)
