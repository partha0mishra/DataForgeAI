"""Tests for data classifier."""

import pytest
import pandas as pd
from classification.classifier import DataClassifier, DataClassification


def test_classify_pii():
    """Test PII classification."""
    classifier = DataClassifier()
    df = pd.DataFrame({
        "ssn": ["123-45-6789"],
        "email": ["test@example.com"],
        "name": ["John"],
    })

    classifications = classifier.classify_dataframe(df)
    assert classifications["ssn"] == DataClassification.RESTRICTED
    assert classifications["email"] == DataClassification.CONFIDENTIAL


def test_classify_financial():
    """Test financial data classification."""
    classifier = DataClassifier()
    df = pd.DataFrame({
        "salary": [50000],
        "revenue": [1000000],
    })

    classifications = classifier.classify_dataframe(df)
    assert classifications["salary"] == DataClassification.CONFIDENTIAL
    assert classifications["revenue"] == DataClassification.CONFIDENTIAL
