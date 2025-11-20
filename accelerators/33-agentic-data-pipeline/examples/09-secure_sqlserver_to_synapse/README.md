# Secure SQL Server to Azure Synapse - Enterprise Pipeline

## Overview
Zero-trust security pipeline from on-premises SQL Server to Azure Synapse with comprehensive governance.

## Use Case
Enterprise migrations requiring SOC2/HIPAA/GDPR compliance.

## Key Features
- ✅ Azure AD passthrough authentication (no passwords)
- ✅ Column-level encryption (Always Encrypted)
- ✅ Row-level security
- ✅ Full audit logging to Azure Purview
- ✅ Private endpoints (no public internet)
- ✅ Customer-managed encryption keys

## Tech Stack
- Source: SQL Server (on-prem or Azure SQL)
- Target: Azure Synapse Analytics
- Orchestration: Synapse Pipelines
- Governance: Microsoft Purview
- Security: Azure AD, Key Vault

## Estimated Cost
~$800-1200/month (Synapse dedicated pool + Purview + Private Link)

## Example Prompt
```
Secure pipeline from on-prem SQL Server → Synapse: use Azure AD passthrough,
column-level encryption, row-level security, full audit logging to Purview.
```
