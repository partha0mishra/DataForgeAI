"""
Unit tests for Feature Store churn prediction pipeline.
"""

import pytest
import pandas as pd
import json
from pathlib import Path


class TestSampleData:
    """Test sample data."""

    def test_activity_csv_exists(self):
        """Verify user activity CSV exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "user_activity.csv"
        assert sample_file.exists(), "User activity CSV should exist"

    def test_text_data_exists(self):
        """Verify text data JSON exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "user_text_data.json"
        assert sample_file.exists(), "Text data JSON should exist"

    def test_activity_has_features(self):
        """Verify activity data has ML features."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "user_activity.csv"
        df = pd.read_csv(sample_file)

        assert 'churned' in df.columns, "Should have target variable"
        assert 'total_logins_30d' in df.columns, "Should have behavioral features"
        assert 'avg_transaction_amount' in df.columns, "Should have transaction features"


class TestNotebooks:
    """Test ML notebooks."""

    def test_feature_creation_notebook_exists(self):
        """Verify feature creation notebook exists."""
        notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "create_feature_tables.py"
        assert notebook.exists(), "Feature creation notebook should exist"

    def test_training_notebook_exists(self):
        """Verify training notebook exists."""
        notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "train_churn_model.py"
        assert notebook.exists(), "Training notebook should exist"

    def test_notebooks_use_feature_store(self):
        """Verify notebooks use Databricks Feature Store."""
        notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "train_churn_model.py"
        content = notebook.read_text()

        assert "feature_store" in content, "Should use feature store"
        assert "FeatureLookup" in content, "Should define feature lookups"
        assert "mlflow" in content, "Should use MLflow"

    def test_notebooks_use_embeddings(self):
        """Verify notebooks generate text embeddings."""
        notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "create_feature_tables.py"
        content = notebook.read_text()

        assert "embedding" in content.lower(), "Should create embeddings"
        assert "sentence" in content.lower() or "transformer" in content.lower(), \
            "Should use transformer model"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
