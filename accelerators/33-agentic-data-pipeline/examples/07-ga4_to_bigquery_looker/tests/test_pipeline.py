"""
Unit tests for GA4 to BigQuery with Looker pipeline.
"""

import pytest
import json
from pathlib import Path


class TestSampleData:
    """Test sample GA4 events data."""

    def test_sample_data_exists(self):
        """Verify sample GA4 events file exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "ga4_events.json"
        assert sample_file.exists(), "Sample GA4 events should exist"

    def test_sample_data_valid_json(self):
        """Verify sample data is valid JSON."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "ga4_events.json"
        with open(sample_file) as f:
            data = json.load(f)
        assert isinstance(data, list), "Sample data should be a list"

    def test_ga4_event_schema(self):
        """Verify GA4 events have correct schema."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "ga4_events.json"
        with open(sample_file) as f:
            events = json.load(f)

        event = events[0]
        required_fields = ['event_date', 'event_timestamp', 'event_name', 'event_params', 'user_pseudo_id']
        for field in required_fields:
            assert field in event, f"Event should have {field} field"


class TestDAG:
    """Test Cloud Composer/Airflow DAG."""

    def test_dag_file_exists(self):
        """Verify DAG file exists."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "ga4_processing_dag.py"
        assert dag_file.exists(), "DAG file should exist"

    def test_dag_uses_bigquery_operators(self):
        """Verify DAG uses BigQuery operators."""
        dag_file = Path(__file__).parent.parent / "generated_code" / "dags" / "ga4_processing_dag.py"
        content = dag_file.read_text()

        assert "BigQueryInsertJobOperator" in content or "BigQueryOperator" in content, \
            "Should use BigQuery operators"


class TestLookML:
    """Test Looker LookML files."""

    def test_model_file_exists(self):
        """Verify LookML model file exists."""
        model_file = Path(__file__).parent.parent / "generated_code" / "lookml" / "web_analytics.model.lkml"
        assert model_file.exists(), "LookML model should exist"

    def test_view_file_exists(self):
        """Verify LookML view file exists."""
        view_file = Path(__file__).parent.parent / "generated_code" / "lookml" / "views" / "user_sessions.view.lkml"
        assert view_file.exists(), "LookML view should exist"

    def test_model_has_explores(self):
        """Verify model defines explores."""
        model_file = Path(__file__).parent.parent / "generated_code" / "lookml" / "web_analytics.model.lkml"
        content = model_file.read_text()

        assert "explore:" in content, "Should define explores"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
