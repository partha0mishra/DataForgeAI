"""Database initialization utilities."""

import os
from datetime import datetime
from typing import Optional

from .database import DatabaseManager, get_database_manager
from .models import Base, UserModel, RoleModel, user_roles
from .repository import UserRepository, RoleRepository
from .auth import pwd_context
from .logging import get_logger

logger = get_logger(__name__)


def create_tables(db_manager: Optional[DatabaseManager] = None) -> None:
    """Create all database tables.

    Args:
        db_manager: Database manager instance
    """
    db_manager = db_manager or get_database_manager()

    try:
        Base.metadata.create_all(db_manager.engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def drop_tables(db_manager: Optional[DatabaseManager] = None) -> None:
    """Drop all database tables.

    WARNING: This will delete all data!

    Args:
        db_manager: Database manager instance
    """
    db_manager = db_manager or get_database_manager()

    try:
        Base.metadata.drop_all(db_manager.engine)
        logger.warning("Database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def init_default_roles(role_repo: Optional[RoleRepository] = None) -> None:
    """Initialize default roles.

    Args:
        role_repo: Role repository instance
    """
    role_repo = role_repo or RoleRepository()

    default_roles = [
        {
            "role_id": "role_user",
            "name": "user",
            "description": "Standard user with basic access",
        },
        {
            "role_id": "role_admin",
            "name": "admin",
            "description": "Administrator with full access",
        },
        {
            "role_id": "role_analyst",
            "name": "analyst",
            "description": "Data analyst with analytics access",
        },
        {
            "role_id": "role_developer",
            "name": "developer",
            "description": "Developer with API and pipeline access",
        },
    ]

    for role_data in default_roles:
        existing = role_repo.get_by_name(role_data["name"])
        if not existing:
            role_repo.create(**role_data)
            logger.info(f"Created role: {role_data['name']}")
        else:
            logger.debug(f"Role already exists: {role_data['name']}")


def init_default_admin(user_repo: Optional[UserRepository] = None, role_repo: Optional[RoleRepository] = None) -> None:
    """Initialize default admin user.

    Args:
        user_repo: User repository instance
        role_repo: Role repository instance
    """
    user_repo = user_repo or UserRepository()
    role_repo = role_repo or RoleRepository()

    # Get admin password from environment or use default
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    # Check if admin already exists
    existing_admin = user_repo.get_by_username("admin")
    if existing_admin:
        logger.debug("Admin user already exists")
        return

    # Create admin user
    admin_user = user_repo.create(
        user_id="admin_001",
        username="admin",
        email="admin@dataforge.ai",
        hashed_password=pwd_context.hash(admin_password),
        is_active=True,
        is_superuser=True,
        created_at=datetime.utcnow(),
    )

    # Add admin and user roles
    admin_role = role_repo.get_by_name("admin")
    user_role = role_repo.get_by_name("user")

    if admin_role:
        user_repo.add_role(admin_user.user_id, admin_role)
    if user_role:
        user_repo.add_role(admin_user.user_id, user_role)

    logger.info(f"Created default admin user (password: {admin_password})")
    if admin_password == "admin123":
        logger.warning("Using default admin password! Change it immediately in production!")


def initialize_database(
    connection_string: Optional[str] = None,
    drop_existing: bool = False,
) -> DatabaseManager:
    """Initialize database with tables and default data.

    Args:
        connection_string: Database connection string
        drop_existing: Whether to drop existing tables first

    Returns:
        Initialized database manager
    """
    # Get connection string from environment if not provided
    if not connection_string:
        connection_string = os.getenv(
            "DATABASE_URL",
            "sqlite:///./dataforge.db"  # Default to SQLite
        )

    logger.info(f"Initializing database: {connection_string.split('@')[-1]}")  # Don't log credentials

    # Create database manager
    db_manager = DatabaseManager(connection_string)

    # Drop tables if requested
    if drop_existing:
        logger.warning("Dropping existing tables...")
        drop_tables(db_manager)

    # Create tables
    create_tables(db_manager)

    # Initialize default roles
    init_default_roles()

    # Initialize default admin user
    init_default_admin()

    logger.info("Database initialization complete")

    return db_manager


def check_database_connection(db_manager: Optional[DatabaseManager] = None) -> bool:
    """Check if database connection is working.

    Args:
        db_manager: Database manager instance

    Returns:
        True if connection is successful
    """
    db_manager = db_manager or get_database_manager()

    try:
        with db_manager.session() as session:
            session.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_database_info(db_manager: Optional[DatabaseManager] = None) -> dict:
    """Get database information.

    Args:
        db_manager: Database manager instance

    Returns:
        Dictionary with database info
    """
    db_manager = db_manager or get_database_manager()
    user_repo = UserRepository(db_manager)
    role_repo = RoleRepository(db_manager)

    return {
        "connection_string": str(db_manager.engine.url),
        "driver": db_manager.engine.dialect.name,
        "pool_size": db_manager.engine.pool.size(),
        "total_users": user_repo.count(),
        "active_users": user_repo.count(is_active=True),
        "total_roles": role_repo.count(),
        "tables": list(Base.metadata.tables.keys()),
    }


if __name__ == "__main__":
    """Run database initialization from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize DataForge database")
    parser.add_argument(
        "--connection-string",
        help="Database connection string (or set DATABASE_URL env var)",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing tables before creating (WARNING: deletes all data!)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check database connection",
    )

    args = parser.parse_args()

    if args.check_only:
        if check_database_connection():
            print("✓ Database connection successful")
            info = get_database_info()
            print("\nDatabase Info:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print("✗ Database connection failed")
            exit(1)
    else:
        initialize_database(
            connection_string=args.connection_string,
            drop_existing=args.drop_existing,
        )
        print("✓ Database initialized successfully")
