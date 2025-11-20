"""
Unit tests for Multi-source Medallion Architecture pipeline.
"""

import pytest
import json
import pandas as pd
from pathlib import Path


class TestSampleData:
    """Test sample data quality."""

    def test_kafka_events_exist(self):
        """Verify Kafka events sample file exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "kafka_events.json"
        assert sample_file.exists(), "Kafka events file should exist"

    def test_kafka_events_valid_json(self):
        """Verify Kafka events are valid JSON."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "kafka_events.json"
        with open(sample_file) as f:
            data = json.load(f)
        assert isinstance(data, list), "Kafka events should be a list"
        assert len(data) > 0, "Should have sample events"

    def test_kafka_event_structure(self):
        """Verify Kafka events have correct structure."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "kafka_events.json"
        with open(sample_file) as f:
            events = json.load(f)

        event = events[0]
        assert 'topic' in event, "Event should have topic"
        assert 'key' in event, "Event should have key"
        assert 'value' in event, "Event should have value"
        assert 'timestamp' in event, "Event should have timestamp"

    def test_postgres_users_csv_exists(self):
        """Verify PostgreSQL users CSV exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "postgres_users.csv"
        assert sample_file.exists(), "Users CSV should exist"

    def test_postgres_users_schema(self):
        """Verify users CSV has correct schema."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "postgres_users.csv"
        df = pd.read_csv(sample_file)

        expected_columns = ['user_id', 'email', 'first_name', 'last_name', 'signup_date', 'country', 'subscription_tier', 'updated_at']
        assert list(df.columns) == expected_columns, "Users should have expected columns"

    def test_postgres_products_csv_exists(self):
        """Verify PostgreSQL products CSV exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "postgres_products.csv"
        assert sample_file.exists(), "Products CSV should exist"

    def test_postgres_products_schema(self):
        """Verify products CSV has correct schema."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "postgres_products.csv"
        df = pd.read_csv(sample_file)

        expected_columns = ['product_id', 'product_name', 'category', 'price', 'stock_quantity', 'supplier_id', 'updated_at']
        assert list(df.columns) == expected_columns, "Products should have expected columns"

    def test_data_quality(self):
        """Verify data quality in CSV files."""
        users_file = Path(__file__).parent.parent / "sample_data" / "postgres_users.csv"
        users_df = pd.read_csv(users_file)

        # Check no null user IDs
        assert users_df['user_id'].notna().all(), "User IDs should not be null"

        # Check valid emails
        assert users_df['email'].str.contains('@').all(), "Emails should be valid"

        products_file = Path(__file__).parent.parent / "sample_data" / "postgres_products.csv"
        products_df = pd.read_csv(products_file)

        # Check positive prices
        assert (products_df['price'] > 0).all(), "Prices should be positive"


class TestNotebooks:
    """Test Databricks notebooks."""

    def test_bronze_streaming_exists(self):
        """Verify bronze streaming notebook exists."""
        notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "bronze_streaming.py"
        assert notebook.exists(), "Bronze streaming notebook should exist"

    def test_bronze_batch_exists(self):
        """Verify bronze batch notebook exists."""
        notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "bronze_batch.py"
        assert notebook.exists(), "Bronze batch notebook should exist"

    def test_silver_transformations_exists(self):
        """Verify silver transformations notebook exists."""
        notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "silver_transformations.py"
        assert notebook.exists(), "Silver transformations notebook should exist"

    def test_gold_aggregations_exists(self):
        """Verify gold aggregations notebook exists."""
        notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "gold_aggregations.py"
        assert notebook.exists(), "Gold aggregations notebook should exist"

    def test_notebooks_have_medallion_layers(self):
        """Verify notebooks implement medallion architecture."""
        silver_notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "silver_transformations.py"
        content = silver_notebook.read_text()

        assert "bronze" in content.lower(), "Should reference bronze layer"
        assert "silver" in content.lower(), "Should reference silver layer"

        gold_notebook = Path(__file__).parent.parent / "generated_code" / "notebooks" / "gold_aggregations.py"
        content = gold_notebook.read_text()

        assert "gold" in content.lower(), "Should reference gold layer"


class TestDAG:
    """Test Airflow DAG."""

    def test_dag_file_exists(self):
        """Verify DAG file exists."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "medallion_orchestration_dag.py"
        assert dag_file.exists(), "DAG file should exist"

    def test_dag_has_databricks_operators(self):
        """Verify DAG uses Databricks operators."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "medallion_orchestration_dag.py"
        content = dag_file.read_text()

        assert "DatabricksSubmitRunOperator" in content or "DatabricksRunNowOperator" in content, "Should use Databricks operators"

    def test_dag_orchestrates_medallion(self):
        """Verify DAG orchestrates medallion layers."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "medallion_orchestration_dag.py"
        content = dag_file.read_text()

        assert "bronze" in content.lower(), "Should orchestrate bronze layer"
        assert "silver" in content.lower(), "Should orchestrate silver layer"
        assert "gold" in content.lower(), "Should orchestrate gold layer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
