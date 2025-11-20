"""
Unit tests for Shopify to Databricks Delta Live Tables pipeline.
"""

import pytest
import json
from pathlib import Path


class TestSampleData:
    """Test sample Shopify data quality."""

    def test_sample_data_exists(self):
        """Verify sample data file exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "shopify_orders_sample.json"
        assert sample_file.exists(), "Sample data file should exist"

    def test_sample_data_valid_json(self):
        """Verify sample data is valid JSON."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "shopify_orders_sample.json"
        with open(sample_file) as f:
            data = json.load(f)
        assert isinstance(data, list), "Sample data should be a list"
        assert len(data) > 0, "Sample data should not be empty"

    def test_sample_data_schema(self):
        """Verify sample data has correct Shopify order schema."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "shopify_orders_sample.json"
        with open(sample_file) as f:
            orders = json.load(f)

        # Check first order has required fields
        order = orders[0]
        required_fields = ['id', 'email', 'created_at', 'total_price', 'customer', 'line_items']
        for field in required_fields:
            assert field in order, f"Order should have {field} field"

    def test_sample_data_quality(self):
        """Verify sample data quality."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "shopify_orders_sample.json"
        with open(sample_file) as f:
            orders = json.load(f)

        for order in orders:
            # Check ID is numeric
            assert isinstance(order['id'], int), "Order ID should be integer"

            # Check email format
            assert '@' in order['email'], "Email should be valid"

            # Check price is numeric
            total_price = float(order['total_price'])
            assert total_price >= 0, "Total price should be non-negative"

            # Check customer exists
            assert 'customer' in order, "Order should have customer"
            assert 'id' in order['customer'], "Customer should have ID"

            # Check line items
            assert 'line_items' in order, "Order should have line items"
            assert len(order['line_items']) > 0, "Order should have at least one line item"


class TestPipelineCode:
    """Test Delta Live Tables pipeline code."""

    def test_pipeline_file_exists(self):
        """Verify DLT pipeline file exists."""
        pipeline_file = Path(__file__).parent.parent / "generated_code" / "notebooks" / "shopify_dlt_pipeline.py"
        assert pipeline_file.exists(), "DLT pipeline file should exist"

    def test_pipeline_has_dlt_imports(self):
        """Verify pipeline has Delta Live Tables imports."""
        pipeline_file = Path(__file__).parent.parent / "generated_code" / "notebooks" / "shopify_dlt_pipeline.py"
        content = pipeline_file.read_text()

        assert "import dlt" in content, "Should import dlt"
        assert "from pyspark.sql" in content, "Should import PySpark"

    def test_pipeline_has_bronze_layer(self):
        """Verify pipeline defines bronze layer."""
        pipeline_file = Path(__file__).parent.parent / "generated_code" / "notebooks" / "shopify_dlt_pipeline.py"
        content = pipeline_file.read_text()

        assert "@dlt.table" in content, "Should define DLT tables"
        assert "orders_bronze" in content, "Should have bronze table"

    def test_pipeline_has_silver_layer(self):
        """Verify pipeline defines silver layer with quality checks."""
        pipeline_file = Path(__file__).parent.parent / "generated_code" / "notebooks" / "shopify_dlt_pipeline.py"
        content = pipeline_file.read_text()

        assert "orders_silver" in content, "Should have silver table"
        assert "@dlt.expect" in content, "Should have data quality expectations"

    def test_pipeline_has_gold_layer(self):
        """Verify pipeline defines gold layer aggregations."""
        pipeline_file = Path(__file__).parent.parent / "generated_code" / "notebooks" / "shopify_dlt_pipeline.py"
        content = pipeline_file.read_text()

        assert "gold" in content.lower(), "Should have gold layer"
        assert "aggregate" in content.lower() or "metrics" in content.lower(), "Should have aggregations"


class TestConfiguration:
    """Test pipeline configuration."""

    def test_config_file_exists(self):
        """Verify config.yaml exists."""
        config_file = Path(__file__).parent.parent / "config.yaml"
        assert config_file.exists(), "config.yaml should exist"

    def test_dlt_config_exists(self):
        """Verify DLT pipeline config exists."""
        dlt_config = Path(__file__).parent.parent / "generated_code" / "config" / "pipeline_config.json"
        assert dlt_config.exists(), "DLT pipeline config should exist"

    def test_dlt_config_valid_json(self):
        """Verify DLT config is valid JSON."""
        dlt_config = Path(__file__).parent.parent / "generated_code" / "config" / "pipeline_config.json"
        with open(dlt_config) as f:
            config = json.load(f)

        assert 'name' in config, "Config should have name"
        assert 'target' in config, "Config should have target schema"
        assert 'continuous' in config, "Config should specify continuous mode"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
