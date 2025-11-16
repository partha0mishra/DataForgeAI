"""Configuration management utilities."""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path


class Config:
    """Configuration manager."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_file: Optional path to YAML config file
        """
        self.config: Dict[str, Any] = {}

        # Load from file if provided
        if config_file and Path(config_file).exists():
            with open(config_file, "r") as f:
                self.config = yaml.safe_load(f) or {}

        # Override with environment variables
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Common environment variables
        env_mappings = {
            "LOG_LEVEL": ("logging", "level"),
            "LOG_FORMAT": ("logging", "format"),
            "METRICS_ENABLED": ("monitoring", "enabled"),
            "DATABASE_URL": ("database", "url"),
            "REDIS_URL": ("redis", "url"),
            "OPENAI_API_KEY": ("llm", "api_key"),
            "OPENAI_MODEL": ("llm", "model"),
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested(config_path, value)

    def _set_nested(self, path: tuple, value: Any):
        """Set nested configuration value.

        Args:
            path: Tuple of keys for nested access
            value: Value to set
        """
        current = self.config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def get(self, *path: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            *path: Configuration path (e.g., 'database', 'url')
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        current = self.config
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current

    def set(self, *path: str, value: Any):
        """Set configuration value.

        Args:
            *path: Configuration path
            value: Value to set
        """
        self._set_nested(path, value)

    def to_dict(self) -> Dict[str, Any]:
        """Get all configuration as dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self.config.copy()


# Global configuration instance
_config = Config()


def get_config() -> Config:
    """Get global configuration instance.

    Returns:
        Global configuration instance
    """
    return _config


def load_config(config_file: str):
    """Load configuration from file.

    Args:
        config_file: Path to YAML config file
    """
    global _config
    _config = Config(config_file)
