"""
Unit tests for S3 CSV to Snowflake dbt pipeline.
"""

import pytest
import pandas as pd
from pathlib import Path


class TestSampleData:
    """Test sample data quality."""

    def test_sample_data_exists(self):
        """Verify sample data file exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "sales_2025-01-01.csv"
        assert sample_file.exists(), "Sample data file should exist"

    def test_sample_data_schema(self):
        """Verify sample data has correct schema."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "sales_2025-01-01.csv"
        df = pd.read_csv(sample_file)

        expected_columns = ['sale_id', 'sale_date', 'customer_id', 'product_id', 'quantity', 'amount', 'region']
        assert list(df.columns) == expected_columns, "Columns should match expected schema"

    def test_sample_data_quality(self):
        """Verify sample data quality."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "sales_2025-01-01.csv"
        df = pd.read_csv(sample_file)

        # Check for nulls in key fields
        assert df['sale_id'].notna().all(), "sale_id should not have nulls"
        assert df['sale_date'].notna().all(), "sale_date should not have nulls"
        assert df['amount'].notna().all(), "amount should not have nulls"

        # Check amount is positive
        assert (df['amount'] > 0).all(), "All amounts should be positive"

        # Check row count
        assert len(df) == 10, "Sample should have 10 rows"


class TestDAGStructure:
    """Test Airflow DAG structure."""

    def test_dag_file_exists(self):
        """Verify DAG file exists."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "s3_to_snowflake_dag.py"
        assert dag_file.exists(), "DAG file should exist"

    def test_dag_imports(self):
        """Verify DAG has required imports."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "s3_to_snowflake_dag.py"
        content = dag_file.read_text()

        assert "from airflow import DAG" in content, "Should import DAG"
        assert "SnowflakeOperator" in content, "Should import SnowflakeOperator"
        assert "S3KeySensor" in content, "Should import S3KeySensor"


class TestDBTModel:
    """Test dbt model."""

    def test_dbt_model_exists(self):
        """Verify dbt model file exists."""
        dbt_file = Path(__file__).parent.parent / "generated_code" / "dbt" / "models" / "silver" / "sales_clean.sql"
        assert dbt_file.exists(), "dbt model file should exist"

    def test_dbt_model_has_incremental_config(self):
        """Verify dbt model has incremental materialization."""
        dbt_file = Path(__file__).parent.parent / "generated_code" / "dbt" / "models" / "silver" / "sales_clean.sql"
        content = dbt_file.read_text()

        assert "materialized='incremental'" in content, "Should use incremental materialization"
        assert "unique_key='sale_id'" in content, "Should have unique key"
        assert "is_incremental()" in content, "Should check for incremental mode"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
