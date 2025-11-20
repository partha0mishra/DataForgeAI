"""
Unit tests for Oracle CDC to Snowflake pipeline.
"""

import pytest
import json
from pathlib import Path


class TestSampleData:
    """Test sample CDC event data quality."""

    def test_sample_data_exists(self):
        """Verify sample CDC events file exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "oracle_cdc_events.json"
        assert sample_file.exists(), "Sample data file should exist"

    def test_sample_data_valid_json(self):
        """Verify sample data is valid JSON."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "oracle_cdc_events.json"
        with open(sample_file) as f:
            data = json.load(f)
        assert isinstance(data, list), "Sample data should be a list"
        assert len(data) > 0, "Sample data should not be empty"

    def test_cdc_event_schema(self):
        """Verify CDC events have correct Debezium schema."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "oracle_cdc_events.json"
        with open(sample_file) as f:
            events = json.load(f)

        # Check first event has required Debezium fields
        event = events[0]
        required_fields = ['before', 'after', 'source', 'op', 'ts_ms']
        for field in required_fields:
            assert field in event, f"CDC event should have {field} field"

    def test_cdc_operations(self):
        """Verify CDC events contain create, update, and delete operations."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "oracle_cdc_events.json"
        with open(sample_file) as f:
            events = json.load(f)

        operations = {event['op'] for event in events}

        # Should have all CDC operation types
        assert 'c' in operations, "Should have create operations"
        assert 'u' in operations, "Should have update operations"
        assert 'd' in operations, "Should have delete operations"

    def test_source_metadata(self):
        """Verify source metadata contains Oracle-specific fields."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "oracle_cdc_events.json"
        with open(sample_file) as f:
            events = json.load(f)

        for event in events:
            source = event['source']
            assert source['connector'] == 'oracle', "Connector should be oracle"
            assert 'scn' in source, "Should have SCN (System Change Number)"
            assert 'schema' in source, "Should have schema name"
            assert 'table' in source, "Should have table name"


class TestDAGStructure:
    """Test Airflow DAG structure."""

    def test_dag_file_exists(self):
        """Verify DAG file exists."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "oracle_cdc_dag.py"
        assert dag_file.exists(), "DAG file should exist"

    def test_dag_imports(self):
        """Verify DAG has required imports."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "oracle_cdc_dag.py"
        content = dag_file.read_text()

        assert "from airflow import DAG" in content, "Should import DAG"
        assert "SnowflakeOperator" in content or "snowflake" in content.lower(), "Should have Snowflake integration"
        assert "kafka" in content.lower(), "Should have Kafka integration"

    def test_dag_has_cdc_logic(self):
        """Verify DAG contains CDC processing logic."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "oracle_cdc_dag.py"
        content = dag_file.read_text()

        assert "MERGE" in content, "Should use MERGE for CDC upserts"
        assert "cdc" in content.lower(), "Should reference CDC"


class TestDebeziumConfig:
    """Test Debezium connector configuration."""

    def test_debezium_config_exists(self):
        """Verify Debezium config file exists."""
        config_file = Path(__file__).parent.parent / "generated_code" / "debezium" / "connector_config.json"
        assert config_file.exists(), "Debezium config should exist"

    def test_debezium_config_valid_json(self):
        """Verify Debezium config is valid JSON."""
        config_file = Path(__file__).parent.parent / "generated_code" / "debezium" / "connector_config.json"
        with open(config_file) as f:
            config = json.load(f)

        assert 'name' in config, "Config should have name"
        assert 'config' in config, "Config should have config section"

    def test_debezium_oracle_connector(self):
        """Verify Debezium is configured for Oracle."""
        config_file = Path(__file__).parent.parent / "generated_code" / "debezium" / "connector_config.json"
        with open(config_file) as f:
            config = json.load(f)

        connector_config = config['config']
        assert 'OracleConnector' in connector_config['connector.class'], "Should use Oracle connector"
        assert 'log.mining' in str(connector_config), "Should use Oracle LogMiner"


class TestConfiguration:
    """Test pipeline configuration."""

    def test_config_file_exists(self):
        """Verify config.yaml exists."""
        config_file = Path(__file__).parent.parent / "config.yaml"
        assert config_file.exists(), "config.yaml should exist"

    def test_config_has_required_sections(self):
        """Verify config has all required sections."""
        config_file = Path(__file__).parent.parent / "config.yaml"
        content = config_file.read_text()

        assert 'oracle:' in content, "Should have Oracle configuration"
        assert 'debezium:' in content, "Should have Debezium configuration"
        assert 'kafka:' in content, "Should have Kafka configuration"
        assert 'snowflake:' in content, "Should have Snowflake configuration"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
