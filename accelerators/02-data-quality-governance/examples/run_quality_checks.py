"""Example: Run quality checks on sample data."""

import pandas as pd
from pathlib import Path

from src.quality_checker import DataQualityChecker
from governance.pii_detection.detector import PIIDetector
from governance.audit_logger.logger import AuditLogger


def create_sample_data():
    """Create sample dataset with quality issues and PII."""
    data = {
        "customer_id": [1, 2, 3, 4, 5, None, 7, 8, 9, 10],
        "name": [
            "John Doe",
            "Jane Smith",
            "Bob Johnson",
            None,
            "Alice Williams",
            "Charlie Brown",
            "Eve Davis",
            "Frank Miller",
            "Grace Lee",
            "Henry Wilson",
        ],
        "email": [
            "john.doe@email.com",
            "jane.smith@email.com",
            "bob.j@email.com",
            "invalid-email",
            "alice.w@email.com",
            "charlie.b@email.com",
            "eve.d@email.com",
            "frank.m@email.com",
            None,
            "henry.w@email.com",
        ],
        "phone": [
            "555-123-4567",
            "555-234-5678",
            "555-345-6789",
            "555-456-7890",
            None,
            "555-567-8901",
            "555-678-9012",
            "555-789-0123",
            "555-890-1234",
            "555-901-2345",
        ],
        "ssn": [
            "123-45-6789",
            None,
            "234-56-7890",
            "345-67-8901",
            "456-78-9012",
            "567-89-0123",
            None,
            "678-90-1234",
            "789-01-2345",
            "890-12-3456",
        ],
        "amount": [100.0, 200.0, 150.0, 300.0, 250.0, 175.0, None, 225.0, 275.0, 325.0],
    }

    return pd.DataFrame(data)


def main():
    """Run quality checks example."""
    print("=" * 60)
    print("DataForge Quality & Governance - Example")
    print("=" * 60)
    print()

    # Create sample data
    print("1. Creating sample dataset...")
    df = create_sample_data()
    print(f"   Created dataset with {len(df)} rows, {len(df.columns)} columns")
    print()

    # Run quality checks
    print("2. Running quality checks...")
    checker = DataQualityChecker()
    quality_report = checker.validate_dataframe(
        df=df,
        expectation_suite_name="sample_suite",
        batch_identifier="sample_data_v1",
    )

    print(f"   Overall Status: {quality_report.overall_status.value.upper()}")
    print(f"   Total Checks: {quality_report.metrics.total_checks}")
    print(f"   Passed: {quality_report.metrics.passed_checks}")
    print(f"   Failed: {quality_report.metrics.failed_checks}")
    print(f"   Warnings: {quality_report.metrics.warnings}")
    print()

    # Show failed checks
    failed_checks = [c for c in quality_report.checks if c.status.value == "failed"]
    if failed_checks:
        print("   Failed Checks:")
        for check in failed_checks:
            print(f"     - {check.check_name}: {check.message}")
        print()

    # Save quality report
    output_dir = Path("quality_reports")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"{quality_report.report_id}.json"
    checker.save_report(quality_report, str(report_path))
    print(f"   Quality report saved: {report_path}")
    print()

    # Detect PII
    print("3. Detecting PII...")
    detector = PIIDetector()
    pii_found = detector.detect_in_dataframe(df)

    print(f"   Columns with PII: {len(pii_found)}")
    for column, pii_types in pii_found.items():
        print(f"     - {column}: {', '.join(f'{k} ({v})' for k, v in pii_types.items())}")
    print()

    # Generate PII report
    pii_report = detector.generate_report(df)
    print("   PII Report Summary:")
    print(f"     Total PII instances: {pii_report['pii_summary']['total_pii_instances']}")
    print()

    if pii_report["recommendations"]:
        print("   Recommendations:")
        for rec in pii_report["recommendations"]:
            print(f"     - {rec}")
        print()

    # Mask PII
    print("4. Masking PII...")
    masked_df = detector.mask_pii(df, preserve_format=True)
    print("   Original vs Masked data (first 3 rows):")
    print()
    print("   Original:")
    print(df[["name", "email", "phone", "ssn"]].head(3))
    print()
    print("   Masked:")
    print(masked_df[["name", "email", "phone", "ssn"]].head(3))
    print()

    # Audit logging
    print("5. Logging to audit trail...")
    audit = AuditLogger(storage_type="file")

    # Log quality check
    audit.log_quality_check(
        dataset="sample_data",
        status=quality_report.overall_status.value,
        metrics=quality_report.metrics.model_dump(),
        suite="sample_suite",
    )

    # Log PII detection
    audit.log_pii_detection(
        dataset="sample_data",
        pii_found=pii_found,
        action_taken="masked",
    )

    print("   Audit logs written")
    print()

    print("=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
