"""Tests for configuration module."""

import os

import pytest
from dataforge_common.config import Environment, Settings, get_settings, reload_settings


def test_settings_defaults():
    """Test default configuration values."""
    settings = Settings()

    assert settings.dataforge_env == Environment.DEVELOPMENT
    assert settings.log_level == "INFO"
    assert settings.postgres_port == 5432


def test_settings_from_env(monkeypatch):
    """Test loading settings from environment variables."""
    monkeypatch.setenv("POSTGRES_HOST", "testhost")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.postgres_host == "testhost"
    assert settings.postgres_port == 5433
    assert settings.log_level == "DEBUG"


def test_database_url():
    """Test database URL generation."""
    settings = Settings(
        postgres_user="testuser",
        postgres_password="testpass",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="testdb",
    )

    expected = "postgresql://testuser:testpass@localhost:5432/testdb"
    assert settings.database_url == expected


def test_redis_url():
    """Test Redis URL generation."""
    settings = Settings(
        redis_host="localhost",
        redis_port=6379,
        redis_password="secret",
    )

    assert settings.redis_url == "redis://:secret@localhost:6379/0"


def test_invalid_log_level():
    """Test validation of invalid log level."""
    with pytest.raises(ValueError, match="log_level must be one of"):
        Settings(log_level="INVALID")


def test_singleton_settings():
    """Test settings singleton pattern."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2
