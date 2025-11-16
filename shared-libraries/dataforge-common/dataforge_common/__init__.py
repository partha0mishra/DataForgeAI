"""DataForge Common - Shared utilities and infrastructure."""

__version__ = "0.1.0"

# Export key components
from .logging import get_logger
from .monitoring import MetricsCollector, get_metrics_collector
from .config import Config, get_config
from .database import DatabaseManager, get_database_manager
from .auth import AuthManager, get_auth_manager, User, TokenData, init_auth
from .fastapi_auth import get_current_user, get_optional_user, require_roles, require_superuser
from .auth_router import create_auth_router

__all__ = [
    "get_logger",
    "MetricsCollector",
    "get_metrics_collector",
    "Config",
    "get_config",
    "DatabaseManager",
    "get_database_manager",
    "AuthManager",
    "get_auth_manager",
    "User",
    "TokenData",
    "init_auth",
    "get_current_user",
    "get_optional_user",
    "require_roles",
    "require_superuser",
    "create_auth_router",
]
