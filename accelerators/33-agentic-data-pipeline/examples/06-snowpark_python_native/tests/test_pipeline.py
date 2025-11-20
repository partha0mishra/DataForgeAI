"""
Unit tests for Snowpark Python native pipeline.
"""

import pytest
import pandas as pd
from pathlib import Path


class TestSampleData:
    """Test sample sales data."""

    def test_sample_data_exists(self):
        """Verify sample sales CSV exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "sales_data.csv"
        assert sample_file.exists(), "Sample sales CSV should exist"

    def test_sample_data_schema(self):
        """Verify sales CSV has correct schema."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "sales_data.csv"
        df = pd.read_csv(sample_file)

        expected_columns = ['sale_id', 'sale_date', 'customer_id', 'product_id', 'quantity',
                          'unit_price', 'total_amount', 'region', 'store_id', 'payment_method']
        assert list(df.columns) == expected_columns, "Columns should match expected schema"

    def test_sample_data_quality(self):
        """Verify sample data quality."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "sales_data.csv"
        df = pd.read_csv(sample_file)

        # Check no null IDs
        assert df['sale_id'].notna().all(), "Sale IDs should not be null"
        assert df['customer_id'].notna().all(), "Customer IDs should not be null"

        # Check positive amounts
        assert (df['total_amount'] > 0).all(), "Amounts should be positive"
        assert (df['quantity'] > 0).all(), "Quantities should be positive"


class TestSnowparkProcedures:
    """Test Snowpark stored procedures."""

    def test_ingest_procedure_exists(self):
        """Verify ingest procedure file exists."""
        proc_file = Path(__file__).parent.parent / "generated_code" / "procedures" / "ingest_sales_data.py"
        assert proc_file.exists(), "Ingest procedure should exist"

    def test_transform_procedure_exists(self):
        """Verify transform procedure file exists."""
        proc_file = Path(__file__).parent.parent / "generated_code" / "procedures" / "transform_sales_data.py"
        assert proc_file.exists(), "Transform procedure should exist"

    def test_aggregate_procedure_exists(self):
        """Verify aggregate procedure file exists."""
        proc_file = Path(__file__).parent.parent / "generated_code" / "procedures" / "aggregate_metrics.py"
        assert proc_file.exists(), "Aggregate procedure should exist"

    def test_procedures_use_snowpark(self):
        """Verify procedures use Snowpark API."""
        proc_file = Path(__file__).parent.parent / "generated_code" / "procedures" / "transform_sales_data.py"
        content = proc_file.read_text()

        assert "from snowflake.snowpark" in content, "Should import Snowpark"
        assert "Session" in content, "Should use Snowpark Session"
        assert "DataFrame" in content or "session.table" in content, "Should use Snowpark DataFrames"

    def test_transform_has_data_quality(self):
        """Verify transform procedure has data quality checks."""
        proc_file = Path(__file__).parent.parent / "generated_code" / "procedures" / "transform_sales_data.py"
        content = proc_file.read_text()

        assert "quality" in content.lower(), "Should have quality checks"
        assert "filter" in content.lower() or "where" in content.lower(), "Should filter data"

    def test_aggregate_has_metrics(self):
        """Verify aggregate procedure calculates metrics."""
        proc_file = Path(__file__).parent.parent / "generated_code" / "procedures" / "aggregate_metrics.py"
        content = proc_file.read_text()

        assert "agg" in content.lower() or "aggregate" in content.lower(), "Should aggregate data"
        assert "sum" in content.lower() or "count" in content.lower(), "Should calculate metrics"


class TestSetupSQL:
    """Test Snowflake setup SQL."""

    def test_setup_sql_exists(self):
        """Verify setup SQL file exists."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "setup.sql"
        assert sql_file.exists(), "Setup SQL should exist"

    def test_setup_creates_database(self):
        """Verify setup creates database and schemas."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "setup.sql"
        content = sql_file.read_text()

        assert "CREATE DATABASE" in content, "Should create database"
        assert "CREATE SCHEMA" in content, "Should create schemas"

    def test_setup_creates_tables(self):
        """Verify setup creates required tables."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "setup.sql"
        content = sql_file.read_text()

        assert "CREATE TABLE" in content or "CREATE OR REPLACE TABLE" in content, "Should create tables"
        assert "RAW.SALES" in content, "Should create raw sales table"
        assert "CLEAN.SALES" in content, "Should create clean sales table"
        assert "METRICS" in content, "Should create metrics tables"

    def test_setup_creates_procedures(self):
        """Verify setup creates stored procedures."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "setup.sql"
        content = sql_file.read_text()

        assert "CREATE PROCEDURE" in content or "CREATE OR REPLACE PROCEDURE" in content, \
            "Should create procedures"
        assert "LANGUAGE PYTHON" in content, "Should use Python language"
        assert "RUNTIME_VERSION" in content, "Should specify Python runtime"

    def test_setup_creates_tasks(self):
        """Verify setup creates Snowflake tasks."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "setup.sql"
        content = sql_file.read_text()

        assert "CREATE TASK" in content or "CREATE OR REPLACE TASK" in content, "Should create tasks"
        assert "SCHEDULE" in content or "AFTER" in content, "Should schedule tasks"
        assert "CALL" in content, "Tasks should call procedures"


class TestConfiguration:
    """Test pipeline configuration."""

    def test_config_file_exists(self):
        """Verify config.yaml exists."""
        config_file = Path(__file__).parent.parent / "config.yaml"
        assert config_file.exists(), "config.yaml should exist"

    def test_config_has_snowflake_section(self):
        """Verify config has Snowflake configuration."""
        config_file = Path(__file__).parent.parent / "config.yaml"
        content = config_file.read_text()

        assert "snowflake:" in content, "Should have Snowflake config"
        assert "snowpark:" in content, "Should have Snowpark config"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
