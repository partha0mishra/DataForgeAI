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
from .cache import Cache, InMemoryCache, RedisCache, get_cache, cached, cache_clear
from .models import (
    Base, UserModel, RoleModel, AuditEventModel, SessionModel, APIKeyModel,
    CacheEntryModel, ConfigModel
)
from .repository import (
    BaseRepository, UserRepository, RoleRepository, AuditEventRepository, SessionRepository
)
from .db_init import (
    create_tables, drop_tables, initialize_database, check_database_connection, get_database_info
)

__all__ = [
    # Logging
    "get_logger",
    # Monitoring
    "MetricsCollector",
    "get_metrics_collector",
    # Config
    "Config",
    "get_config",
    # Database
    "DatabaseManager",
    "get_database_manager",
    # Auth
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
    # Cache
    "Cache",
    "InMemoryCache",
    "RedisCache",
    "get_cache",
    "cached",
    "cache_clear",
    # Models
    "Base",
    "UserModel",
    "RoleModel",
    "AuditEventModel",
    "SessionModel",
    "APIKeyModel",
    "CacheEntryModel",
    "ConfigModel",
    # Repository
    "BaseRepository",
    "UserRepository",
    "RoleRepository",
    "AuditEventRepository",
    "SessionRepository",
    # DB Init
    "create_tables",
    "drop_tables",
    "initialize_database",
    "check_database_connection",
    "get_database_info",
]
