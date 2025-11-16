"""Pytest configuration and shared fixtures for integration tests."""

import os
import pytest
import tempfile
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ADMIN_PASSWORD"] = "test_admin_password"

from dataforge_common import (
    DatabaseManager,
    Base,
    UserRepository,
    RoleRepository,
    AuditEventRepository,
    get_auth_manager,
    initialize_database,
    get_cache,
    InMemoryCache,
)


@pytest.fixture(scope="session")
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture(scope="function")
def db_manager():
    """Create test database manager with in-memory SQLite."""
    # Create in-memory database
    db = DatabaseManager("sqlite:///:memory:")

    # Create all tables
    Base.metadata.create_all(db.engine)

    yield db

    # Cleanup
    Base.metadata.drop_all(db.engine)
    db.engine.dispose()


@pytest.fixture(scope="function")
def user_repo(db_manager):
    """User repository with test database."""
    return UserRepository(db_manager)


@pytest.fixture(scope="function")
def role_repo(db_manager):
    """Role repository with test database."""
    return RoleRepository(db_manager)


@pytest.fixture(scope="function")
def audit_repo(db_manager):
    """Audit event repository with test database."""
    return AuditEventRepository(db_manager)


@pytest.fixture(scope="function")
def test_database():
    """Initialize test database with default data."""
    db = initialize_database(
        connection_string="sqlite:///:memory:",
        drop_existing=True,
    )

    yield db

    # Cleanup
    Base.metadata.drop_all(db.engine)
    db.engine.dispose()


@pytest.fixture(scope="function")
def test_cache():
    """Test cache instance (in-memory)."""
    cache = InMemoryCache()
    yield cache
    cache.clear()


@pytest.fixture(scope="function")
def auth_manager(test_database):
    """Auth manager with test database."""
    return get_auth_manager()


@pytest.fixture(scope="function")
def test_user(user_repo, role_repo):
    """Create a test user."""
    from dataforge_common.auth import pwd_context

    # Ensure user role exists
    user_role = role_repo.get_by_name("user")
    if not user_role:
        user_role = role_repo.create(
            role_id="role_user",
            name="user",
            description="Standard user",
        )

    # Create test user
    user = user_repo.create(
        user_id="test_user_001",
        username="testuser",
        email="test@example.com",
        hashed_password=pwd_context.hash("testpassword"),
        is_active=True,
        is_superuser=False,
    )

    # Add user role
    user_repo.add_role(user.user_id, user_role)

    return user


@pytest.fixture(scope="function")
def admin_user(user_repo, role_repo):
    """Create a test admin user."""
    from dataforge_common.auth import pwd_context

    # Ensure admin role exists
    admin_role = role_repo.get_by_name("admin")
    if not admin_role:
        admin_role = role_repo.create(
            role_id="role_admin",
            name="admin",
            description="Administrator",
        )

    user_role = role_repo.get_by_name("user")
    if not user_role:
        user_role = role_repo.create(
            role_id="role_user",
            name="user",
            description="Standard user",
        )

    # Create admin user
    user = user_repo.create(
        user_id="admin_user_001",
        username="adminuser",
        email="admin@example.com",
        hashed_password=pwd_context.hash("adminpassword"),
        is_active=True,
        is_superuser=True,
    )

    # Add roles
    user_repo.add_role(user.user_id, admin_role)
    user_repo.add_role(user.user_id, user_role)

    return user


@pytest.fixture(scope="function")
def test_tokens(auth_manager, test_user):
    """Generate test JWT tokens."""
    from dataforge_common.auth import User

    # Convert UserModel to User dataclass for auth manager
    user = User(
        user_id=test_user.user_id,
        username=test_user.username,
        email=test_user.email,
        hashed_password=test_user.hashed_password,
        is_active=test_user.is_active,
        is_superuser=test_user.is_superuser,
        roles=[r.name for r in test_user.roles],
    )

    access_token = auth_manager.create_access_token(user)
    refresh_token = auth_manager.create_refresh_token(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }


@pytest.fixture(scope="function")
def admin_tokens(auth_manager, admin_user):
    """Generate admin JWT tokens."""
    from dataforge_common.auth import User

    # Convert UserModel to User dataclass
    user = User(
        user_id=admin_user.user_id,
        username=admin_user.username,
        email=admin_user.email,
        hashed_password=admin_user.hashed_password,
        is_active=admin_user.is_active,
        is_superuser=admin_user.is_superuser,
        roles=[r.name for r in admin_user.roles],
    )

    access_token = auth_manager.create_access_token(user)
    refresh_token = auth_manager.create_refresh_token(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }


@pytest.fixture(scope="function")
def sample_csv_data():
    """Sample CSV data for testing."""
    return """name,email,phone,age,department
John Doe,john.doe@example.com,555-123-4567,30,Engineering
Jane Smith,jane.smith@example.com,555-987-6543,25,Marketing
Bob Johnson,bob.johnson@example.com,555-555-5555,35,Sales
Alice Williams,alice.williams@example.com,555-111-2222,28,Engineering
Charlie Brown,charlie.brown@example.com,555-333-4444,32,Marketing"""


@pytest.fixture(scope="function")
def sample_pii_data():
    """Sample data with PII for testing."""
    return """name,email,ssn,credit_card,address
John Doe,john@example.com,123-45-6789,4532-1234-5678-9010,123 Main St
Jane Smith,jane@example.com,987-65-4321,5425-2345-6789-0123,456 Oak Ave"""


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "requires_redis: mark test as requiring Redis"
    )
    config.addinivalue_line(
        "markers", "requires_postgres: mark test as requiring PostgreSQL"
    )
    config.addinivalue_line(
        "markers", "requires_kafka: mark test as requiring Kafka"
    )
