# Accelerator 12: Data Governance & Compliance

Enterprise-grade data governance with PII detection, GDPR compliance, data classification, and audit trails.

## Features

- **PII Detection**: Automatically detect sensitive data (email, phone, SSN, credit cards, etc.)
- **PII Masking**: Redact, hash, or tokenize sensitive data
- **Data Classification**: Classify data by sensitivity (Public, Internal, Confidential, Restricted)
- **GDPR Compliance**: Check compliance with GDPR requirements
- **Audit Trail**: Track all data access for compliance reporting
- **Multi-format Support**: CSV, Parquet, JSON data files

## Quick Start

```bash
pip install -r requirements.txt
python examples/governance_example.py
```

## API

```bash
uvicorn src.api.main:app --port 8012
```

Visit http://localhost:8012/docs

## Endpoints

- `POST /pii/scan` - Scan file for PII
- `POST /pii/mask` - Mask PII in file  
- `POST /classify` - Classify data by sensitivity
- `POST /compliance/check` - Check GDPR compliance
- `POST /audit/log` - Log audit event
- `GET /audit/events` - Get audit trail

## Usage

### PII Detection

```python
from pii.detector import PIIDetector
import pandas as pd

detector = PIIDetector()
df = pd.read_csv("customer_data.csv")

# Scan for PII
report = detector.scan_dataframe(df)
print(f"PII columns: {report.pii_columns}")

# Mask PII
masked_df = detector.mask_dataframe(df, strategy="hash")
```

### Data Classification

```python
from classification.classifier import DataClassifier

classifier = DataClassifier()
classifications = classifier.classify_dataframe(df)

for column, classification in classifications.items():
    print(f"{column}: {classification.value}")
```

### Compliance Checking

```python
from compliance.checker import ComplianceChecker

checker = ComplianceChecker()
report = checker.check_gdpr(
    df=df,
    has_consent=True,
    retention_days=90,
    data_age_days=30,
)

if not report.compliant:
    for violation in report.violations:
        print(f"[{violation.severity}] {violation.rule}")
```

### Audit Trail

```python
from audit.trail import AuditTrail

audit = AuditTrail()

# Log access
audit.log_access(
    user_id="user_123",
    action="read",
    resource_type="customer_data",
    resource_id="customer_456",
)

# Query events
events = audit.get_events(user_id="user_123")
```

## Supported PII Types

- Email addresses
- Phone numbers
- Social Security Numbers (SSN)
- Credit card numbers
- IP addresses
- Names (coming soon)
- Addresses (coming soon)
- Date of birth (coming soon)

## Data Classifications

- **Public**: Non-sensitive, publicly shareable
- **Internal**: For internal use only
- **Confidential**: Sensitive business data
- **Restricted**: PII, PHI, highly sensitive

## Compliance Features

### GDPR
- Article 6: Lawfulness of processing (consent check)
- Article 5(1)(e): Storage limitation (retention policies)
- Article 5(1)(c): Data minimization

### Coming Soon
- CCPA compliance
- HIPAA compliance
- SOC 2 compliance

## License

MIT
