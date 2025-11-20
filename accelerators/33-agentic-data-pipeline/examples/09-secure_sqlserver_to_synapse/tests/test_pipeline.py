"""
Unit tests for Secure SQL Server to Synapse pipeline.
"""

import pytest
import json
from pathlib import Path


class TestConfiguration:
    """Test pipeline configuration."""

    def test_config_has_security_section(self):
        """Verify config has comprehensive security settings."""
        config_file = Path(__file__).parent.parent / "config.yaml"
        content = config_file.read_text()

        assert "security:" in content, "Should have security configuration"
        assert "encryption:" in content, "Should specify encryption"
        assert "row_level_security:" in content, "Should configure RLS"
        assert "azure_ad" in content.lower(), "Should use Azure AD"


class TestSecuritySQL:
    """Test security SQL scripts."""

    def test_security_sql_exists(self):
        """Verify security setup SQL exists."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "synapse" / "setup_security.sql"
        assert sql_file.exists(), "Security SQL should exist"

    def test_sql_has_encryption(self):
        """Verify SQL implements column encryption."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "synapse" / "setup_security.sql"
        content = sql_file.read_text()

        assert "ENCRYPTED WITH" in content, "Should encrypt columns"
        assert "COLUMN_ENCRYPTION_KEY" in content, "Should use encryption keys"

    def test_sql_has_rls(self):
        """Verify SQL implements row-level security."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "synapse" / "setup_security.sql"
        content = sql_file.read_text()

        assert "SECURITY POLICY" in content, "Should create security policy"
        assert "FILTER PREDICATE" in content, "Should define filter predicate"

    def test_sql_has_masking(self):
        """Verify SQL implements dynamic data masking."""
        sql_file = Path(__file__).parent.parent / "generated_code" / "synapse" / "setup_security.sql"
        content = sql_file.read_text()

        assert "ADD MASKED WITH" in content, "Should add data masking"


class TestPipeline:
    """Test Synapse pipeline definition."""

    def test_pipeline_file_exists(self):
        """Verify pipeline definition exists."""
        pipeline_file = Path(__file__).parent.parent / "generated_code" / "synapse" / "incremental_load_pipeline.json"
        assert pipeline_file.exists(), "Pipeline definition should exist"

    def test_pipeline_valid_json(self):
        """Verify pipeline is valid JSON."""
        pipeline_file = Path(__file__).parent.parent / "generated_code" / "synapse" / "incremental_load_pipeline.json"
        with open(pipeline_file) as f:
            data = json.load(f)
        assert 'name' in data, "Should have pipeline name"
        assert 'properties' in data, "Should have properties"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
