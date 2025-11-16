"""Tests for configuration module."""

import pytest
from dataforge_common.config import Config


def test_config_get():
    """Test config get."""
    config = Config()
    config.set("database", "host", value="localhost")

    assert config.get("database", "host") == "localhost"


def test_config_default():
    """Test default values."""
    config = Config()

    assert config.get("nonexistent", "key", default="default_value") == "default_value"


def test_nested_config():
    """Test nested configuration."""
    config = Config()
    config.set("app", "database", "host", value="localhost")

    assert config.get("app", "database", "host") == "localhost"
