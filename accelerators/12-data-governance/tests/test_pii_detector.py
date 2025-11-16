"""Tests for PII detector."""

import pytest
import pandas as pd
from pii.detector import PIIDetector, PIIType


def test_detect_email():
    """Test email detection."""
    detector = PIIDetector()
    df = pd.DataFrame({
        "email": ["user@example.com", "test@test.com"],
        "name": ["John", "Jane"],
    })

    report = detector.scan_dataframe(df)
    assert "email" in report.pii_columns
    assert PIIType.EMAIL.value in report.summary


def test_detect_phone():
    """Test phone number detection."""
    detector = PIIDetector()
    df = pd.DataFrame({
        "phone": ["555-123-4567", "555-987-6543"],
        "id": [1, 2],
    })

    report = detector.scan_dataframe(df)
    assert "phone" in report.pii_columns


def test_mask_dataframe():
    """Test PII masking."""
    detector = PIIDetector()
    df = pd.DataFrame({
        "email": ["user@example.com"],
        "name": ["John"],
    })

    masked = detector.mask_dataframe(df, strategy="redact")
    assert masked["email"].iloc[0] == "[REDACTED]"
    assert masked["name"].iloc[0] == "John"  # Not PII, should not be masked
