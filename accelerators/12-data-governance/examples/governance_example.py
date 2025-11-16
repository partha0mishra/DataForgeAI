"""Example: Data Governance workflow."""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pii.detector import PIIDetector
from classification.classifier import DataClassifier
from compliance.checker import ComplianceChecker
from audit.trail import AuditTrail


def create_sample_data():
    """Create sample customer data with PII."""
    np.random.seed(42)

    data = {
        "customer_id": range(1, 101),
        "name": [f"Customer {i}" for i in range(1, 101)],
        "email": [f"customer{i}@example.com" for i in range(1, 101)],
        "phone": [f"555-{np.random.randint(100,999)}-{np.random.randint(1000,9999)}" for _ in range(100)],
        "ssn": [f"{np.random.randint(100,999)}-{np.random.randint(10,99)}-{np.random.randint(1000,9999)}" for _ in range(100)],
        "address": [f"{np.random.randint(100,9999)} Main St" for _ in range(100)],
        "purchase_amount": np.random.uniform(10, 1000, 100).round(2),
        "signup_date": pd.date_range("2024-01-01", periods=100, freq="D"),
    }

    df = pd.DataFrame(data)
    df.to_csv("sample_customer_data.csv", index=False)

    return df


def main():
    """Run data governance example."""
    print("=" * 80)
    print(" DataForge Data Governance - Example")
    print("=" * 80)

    # Create sample data
    print("\n1. Creating Sample Customer Data...")
    df = create_sample_data()
    print(f"✓ Created {len(df)} customer records with PII")

    # PII Detection
    print("\n2. PII Detection...")
    pii_detector = PIIDetector()
    pii_report = pii_detector.scan_dataframe(df)

    print(f"  Total Rows: {pii_report.total_rows}")
    print(f"  Total Columns: {pii_report.total_columns}")
    print(f"  PII Columns Found: {len(pii_report.pii_columns)}")
    print(f"  Columns: {', '.join(pii_report.pii_columns)}")
    print(f"\n  PII Summary:")
    for pii_type, count in pii_report.summary.items():
        print(f"    {pii_type}: {count} instances")

    # PII Masking
    print("\n3. PII Masking...")
    masked_df = pii_detector.mask_dataframe(df, strategy="hash")
    print(f"✓ Masked {len(pii_report.pii_columns)} columns")
    print(f"\n  Original data sample:")
    print(df[["email", "phone", "ssn"]].head(3).to_string(index=False))
    print(f"\n  Masked data sample:")
    print(masked_df[["email", "phone", "ssn"]].head(3).to_string(index=False))

    # Data Classification
    print("\n4. Data Classification...")
    classifier = DataClassifier()
    classifications = classifier.classify_dataframe(df)

    print(f"  Column Classifications:")
    for column, classification in classifications.items():
        print(f"    {column}: {classification.value.upper()}")

    # Compliance Check
    print("\n5. GDPR Compliance Check...")
    compliance_checker = ComplianceChecker()

    # Check without consent
    report1 = compliance_checker.check_gdpr(df, has_consent=False)
    print(f"  Without Consent:")
    print(f"    Compliant: {report1.compliant}")
    print(f"    Checks: {report1.passed_checks}/{report1.checks_performed} passed")
    print(f"    Violations: {len(report1.violations)}")

    if report1.violations:
        print(f"\n  Violations Found:")
        for v in report1.violations:
            print(f"    [{v.severity.upper()}] {v.rule}")
            print(f"      {v.description}")
            print(f"      Remediation: {v.remediation}")

    # Check with consent
    report2 = compliance_checker.check_gdpr(df, has_consent=True, retention_days=90, data_age_days=30)
    print(f"\n  With Consent (retention 90 days, age 30 days):")
    print(f"    Compliant: {report2.compliant}")
    print(f"    Checks: {report2.passed_checks}/{report2.checks_performed} passed")

    # Audit Trail
    print("\n6. Audit Trail...")
    audit = AuditTrail()

    # Log some access events
    audit.log_access("user_001", "read", "customer_data", "customer_123")
    audit.log_access("user_002", "export", "customer_data", "customer_456", ip_address="192.168.1.1")
    audit.log_access("user_001", "delete", "customer_data", "customer_789")

    events = audit.get_events()
    print(f"  Total Events: {len(events)}")
    print(f"\n  Recent Events:")
    for event in events:
        print(f"    [{event.timestamp.strftime('%H:%M:%S')}] {event.user_id} {event.action} {event.resource_id}")

    # Summary
    print("\n" + "=" * 80)
    print(" Governance Example Complete!")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  ✓ Detected PII in {len(pii_report.pii_columns)} columns")
    print(f"  ✓ Classified {len(classifications)} columns")
    print(f"  ✓ Performed {report1.checks_performed} compliance checks")
    print(f"  ✓ Logged {len(events)} audit events")
    print(f"\nNext steps:")
    print(f"  1. Start API: uvicorn src.api.main:app --port 8012")
    print(f"  2. Upload data files for PII scanning")
    print(f"  3. Implement data retention policies")
    print(f"  4. Set up compliance monitoring")


if __name__ == "__main__":
    main()
