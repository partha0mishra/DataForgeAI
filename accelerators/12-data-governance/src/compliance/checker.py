"""GDPR and compliance checking."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ComplianceViolation:
    """A compliance violation."""
    rule: str
    severity: str  # critical, high, medium, low
    description: str
    affected_data: str
    remediation: str


@dataclass
class ComplianceReport:
    """Compliance check report."""
    compliant: bool
    violations: List[ComplianceViolation] = field(default_factory=list)
    checks_performed: int = 0
    passed_checks: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ComplianceChecker:
    """Check data compliance with regulations."""

    def check_gdpr(
        self,
        df: pd.DataFrame,
        has_consent: bool = False,
        retention_days: Optional[int] = None,
        data_age_days: Optional[int] = None,
    ) -> ComplianceReport:
        """Check GDPR compliance.

        Args:
            df: DataFrame to check
            has_consent: Whether user consent exists
            retention_days: Data retention policy in days
            data_age_days: Age of data in days

        Returns:
            Compliance report
        """
        logger.info("Performing GDPR compliance check")

        violations = []
        checks = 0
        passed = 0

        # Check 1: PII must have consent
        checks += 1
        from ..pii.detector import PIIDetector
        pii_detector = PIIDetector()
        pii_report = pii_detector.scan_dataframe(df, sample_size=100)

        if pii_report.pii_columns and not has_consent:
            violations.append(ComplianceViolation(
                rule="GDPR Article 6 - Lawfulness of Processing",
                severity="critical",
                description="PII data found without user consent",
                affected_data=f"Columns: {', '.join(pii_report.pii_columns)}",
                remediation="Obtain user consent or remove PII data",
            ))
        else:
            passed += 1

        # Check 2: Data retention limits
        checks += 1
        if retention_days and data_age_days and data_age_days > retention_days:
            violations.append(ComplianceViolation(
                rule="GDPR Article 5(1)(e) - Storage Limitation",
                severity="high",
                description=f"Data retained beyond {retention_days} days policy",
                affected_data=f"Data age: {data_age_days} days",
                remediation="Delete data or renew consent",
            ))
        else:
            passed += 1

        # Check 3: Data minimization
        checks += 1
        if len(df.columns) > 50:
            violations.append(ComplianceViolation(
                rule="GDPR Article 5(1)(c) - Data Minimization",
                severity="medium",
                description=f"Large number of columns ({len(df.columns)}) may violate minimization",
                affected_data="Entire dataset",
                remediation="Review necessity of all data fields",
            ))
        else:
            passed += 1

        report = ComplianceReport(
            compliant=len(violations) == 0,
            violations=violations,
            checks_performed=checks,
            passed_checks=passed,
        )

        logger.info(f"GDPR check: {passed}/{checks} passed, {len(violations)} violations")

        return report
