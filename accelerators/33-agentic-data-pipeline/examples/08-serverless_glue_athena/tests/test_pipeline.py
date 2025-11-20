"""
Unit tests for Serverless Glue + Athena pipeline.
"""

import pytest
import pandas as pd
import json
from pathlib import Path


class TestSampleData:
    """Test sample sales data."""

    def test_sample_data_exists(self):
        """Verify sample sales CSV exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "sales.csv"
        assert sample_file.exists(), "Sample sales CSV should exist"

    def test_sample_data_schema(self):
        """Verify sales CSV has correct schema."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "sales.csv"
        df = pd.read_csv(sample_file)

        expected_columns = ['order_id', 'order_date', 'customer_id', 'product_id',
                          'quantity', 'amount', 'region', 'year', 'month', 'day']
        assert list(df.columns) == expected_columns, "Should have expected columns"


class TestGlueJob:
    """Test AWS Glue ETL job."""

    def test_glue_script_exists(self):
        """Verify Glue script exists."""
        script_file = Path(__file__).parent.parent / "generated_code" / "glue" / "process_sales.py"
        assert script_file.exists(), "Glue script should exist"

    def test_glue_script_uses_pyspark(self):
        """Verify Glue script uses PySpark."""
        script_file = Path(__file__).parent.parent / "generated_code" / "glue" / "process_sales.py"
        content = script_file.read_text()

        assert "from awsglue" in content, "Should import awsglue"
        assert "GlueContext" in content, "Should use GlueContext"
        assert "DynamicFrame" in content, "Should use DynamicFrames"


class TestAthenaSQL:
    """Test Athena SQL scripts."""

    def test_athena_sql_exists(self):
        """Verify Athena SQL file exists."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "athena" / "create_tables.sql"
        assert sql_file.exists(), "Athena SQL should exist"

    def test_athena_creates_tables(self):
        """Verify Athena SQL creates tables."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "athena" / "create_tables.sql"
        content = sql_file.read_text()

        assert "CREATE EXTERNAL TABLE" in content, "Should create external tables"
        assert "PARTITIONED BY" in content, "Should create partitioned tables"
        assert "STORED AS PARQUET" in content, "Should use Parquet format"


class TestStepFunctions:
    """Test Step Functions state machine."""

    def test_state_machine_file_exists(self):
        """Verify state machine definition exists."""
        sm_file = Path(__file__).parent.parent / "generated_code" / "step_functions" / "state_machine.json"
        assert sm_file.exists(), "State machine definition should exist"

    def test_state_machine_valid_json(self):
        """Verify state machine is valid JSON."""
        sm_file = Path(__file__).parent.parent / "generated_code" / "step_functions" / "state_machine.json"
        with open(sm_file) as f:
            data = json.load(f)
        assert 'States' in data, "Should have States"
        assert 'StartAt' in data, "Should have StartAt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
