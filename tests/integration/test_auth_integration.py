"""Integration tests for authentication system."""

import pytest
from datetime import datetime, timedelta


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Test authentication system integration."""

    def test_user_creation_and_authentication(self, user_repo, role_repo):
        """Test creating a user and authenticating."""
        from dataforge_common.auth import pwd_context, get_auth_manager

        # Create role
        user_role = role_repo.create(
            role_id="role_test_user",
            name="test_user",
            description="Test user role",
        )

        # Create user
        user = user_repo.create(
            user_id="user_123",
            username="integration_test_user",
            email="integration@test.com",
            hashed_password=pwd_context.hash("secure_password"),
            is_active=True,
        )

        user_repo.add_role(user.user_id, user_role)

        # Verify user was created
        assert user_repo.get_by_username("integration_test_user") is not None
        assert user_repo.get_by_email("integration@test.com") is not None

        # Test password verification
        assert pwd_context.verify("secure_password", user.hashed_password)
        assert not pwd_context.verify("wrong_password", user.hashed_password)

    def test_jwt_token_flow(self, auth_manager, test_user):
        """Test complete JWT token flow."""
        from dataforge_common.auth import User

        # Convert to User dataclass
        user = User(
            user_id=test_user.user_id,
            username=test_user.username,
            email=test_user.email,
            hashed_password=test_user.hashed_password,
            is_active=test_user.is_active,
            is_superuser=test_user.is_superuser,
            roles=[r.name for r in test_user.roles],
        )

        # Create access token
        access_token = auth_manager.create_access_token(user)
        assert access_token is not None
        assert len(access_token) > 0

        # Verify token
        token_data = auth_manager.verify_token(access_token)
        assert token_data is not None
        assert token_data.username == user.username
        assert token_data.user_id == user.user_id

        # Create refresh token
        refresh_token = auth_manager.create_refresh_token(user)
        assert refresh_token is not None
        assert refresh_token != access_token

        # Verify refresh token
        refresh_data = auth_manager.verify_token(refresh_token)
        assert refresh_data is not None
        assert refresh_data.username == user.username

    def test_role_based_access_control(self, user_repo, role_repo, admin_user, test_user):
        """Test RBAC functionality."""
        from dataforge_common import get_auth_manager

        auth_manager = get_auth_manager()

        # Admin should have admin role
        admin_roles = [r.name for r in admin_user.roles]
        assert "admin" in admin_roles

        # Test user should only have user role
        test_roles = [r.name for r in test_user.roles]
        assert "user" in test_roles
        assert "admin" not in test_roles

        # Superuser should bypass role checks
        assert admin_user.is_superuser

    def test_token_expiration(self, auth_manager, test_user):
        """Test token expiration handling."""
        from dataforge_common.auth import User

        user = User(
            user_id=test_user.user_id,
            username=test_user.username,
            email=test_user.email,
            hashed_password=test_user.hashed_password,
            is_active=test_user.is_active,
            is_superuser=test_user.is_superuser,
            roles=[r.name for r in test_user.roles],
        )

        # Create token with very short expiration (negative delta = expired)
        expired_delta = timedelta(seconds=-1)
        expired_token = auth_manager.create_access_token(user, expires_delta=expired_delta)

        # Expired token should fail verification
        token_data = auth_manager.verify_token(expired_token)
        assert token_data is None

    def test_inactive_user_authentication(self, user_repo, role_repo):
        """Test that inactive users cannot authenticate."""
        from dataforge_common.auth import pwd_context, get_auth_manager

        auth_manager = get_auth_manager()

        # Create inactive user
        user = user_repo.create(
            user_id="inactive_user",
            username="inactive",
            email="inactive@test.com",
            hashed_password=pwd_context.hash("password"),
            is_active=False,
        )

        # Attempt authentication should fail
        authenticated = auth_manager.authenticate_user("inactive", "password")
        assert authenticated is None

    def test_audit_trail_integration(self, audit_repo, test_user):
        """Test audit trail logging."""
        # Log audit event
        event = audit_repo.create(
            event_id="evt_001",
            user_id=test_user.user_id,
            action="test_action",
            resource_type="test_resource",
            resource_id="res_001",
            ip_address="127.0.0.1",
            status="success",
        )

        assert event is not None

        # Retrieve by user
        user_events = audit_repo.get_by_user(test_user.user_id)
        assert len(user_events) == 1
        assert user_events[0].action == "test_action"

        # Retrieve by resource
        resource_events = audit_repo.get_by_resource("test_resource", "res_001")
        assert len(resource_events) == 1
        assert resource_events[0].user_id == test_user.user_id


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database operations integration."""

    def test_database_initialization(self, test_database):
        """Test database is properly initialized."""
        from dataforge_common import UserRepository, RoleRepository

        user_repo = UserRepository(test_database)
        role_repo = RoleRepository(test_database)

        # Should have default admin user
        admin = user_repo.get_by_username("admin")
        assert admin is not None
        assert admin.is_superuser

        # Should have default roles
        user_role = role_repo.get_by_name("user")
        admin_role = role_repo.get_by_name("admin")
        assert user_role is not None
        assert admin_role is not None

    def test_user_role_relationship(self, user_repo, role_repo):
        """Test many-to-many user-role relationship."""
        # Create roles
        role1 = role_repo.create(
            role_id="role_1",
            name="analyst",
            description="Data analyst",
        )
        role2 = role_repo.create(
            role_id="role_2",
            name="developer",
            description="Developer",
        )

        # Create user
        from dataforge_common.auth import pwd_context

        user = user_repo.create(
            user_id="multi_role_user",
            username="multirole",
            email="multi@test.com",
            hashed_password=pwd_context.hash("password"),
        )

        # Add multiple roles
        user_repo.add_role(user.user_id, role1)
        user_repo.add_role(user.user_id, role2)

        # Verify roles
        updated_user = user_repo.get_by_id(user.user_id)
        role_names = [r.name for r in updated_user.roles]
        assert "analyst" in role_names
        assert "developer" in role_names

        # Remove role
        user_repo.remove_role(user.user_id, role1)

        updated_user = user_repo.get_by_id(user.user_id)
        role_names = [r.name for r in updated_user.roles]
        assert "analyst" not in role_names
        assert "developer" in role_names

    def test_repository_crud_operations(self, user_repo):
        """Test repository CRUD operations."""
        from dataforge_common.auth import pwd_context

        # Create
        user = user_repo.create(
            user_id="crud_user",
            username="cruduser",
            email="crud@test.com",
            hashed_password=pwd_context.hash("password"),
        )
        assert user.username == "cruduser"

        # Read
        fetched = user_repo.get_by_id("crud_user")
        assert fetched.username == "cruduser"

        # Update
        updated = user_repo.update("crud_user", email="updated@test.com")
        assert updated.email == "updated@test.com"

        # Delete
        deleted = user_repo.delete("crud_user")
        assert deleted is True

        # Verify deletion
        assert user_repo.get_by_id("crud_user") is None

    def test_filter_and_count_operations(self, user_repo):
        """Test repository filter and count operations."""
        from dataforge_common.auth import pwd_context

        # Create multiple users
        for i in range(5):
            user_repo.create(
                user_id=f"user_{i}",
                username=f"user{i}",
                email=f"user{i}@test.com",
                hashed_password=pwd_context.hash("password"),
                is_active=(i % 2 == 0),  # Alternate active/inactive
            )

        # Count all users
        total = user_repo.count()
        assert total >= 5

        # Count active users
        active = user_repo.count(is_active=True)
        assert active >= 3

        # Filter active users
        active_users = user_repo.filter_by(is_active=True)
        assert len(active_users) >= 3


@pytest.mark.integration
class TestCacheIntegration:
    """Test caching system integration."""

    def test_cache_set_get(self, test_cache):
        """Test basic cache operations."""
        # Set value
        test_cache.set("key1", "value1")
        assert test_cache.get("key1") == "value1"

        # Set with TTL (won't expire in test)
        test_cache.set("key2", "value2", ttl=300)
        assert test_cache.get("key2") == "value2"

        # Non-existent key
        assert test_cache.get("nonexistent") is None

    def test_cache_delete_and_clear(self, test_cache):
        """Test cache deletion operations."""
        # Set multiple values
        test_cache.set("key1", "value1")
        test_cache.set("key2", "value2")
        test_cache.set("key3", "value3")

        # Delete specific key
        assert test_cache.delete("key1") is True
        assert test_cache.get("key1") is None
        assert test_cache.get("key2") == "value2"

        # Clear all
        test_cache.clear()
        assert test_cache.get("key2") is None
        assert test_cache.get("key3") is None

    def test_cache_complex_objects(self, test_cache):
        """Test caching complex Python objects."""
        # Dictionary
        data = {"name": "John", "age": 30, "roles": ["user", "admin"]}
        test_cache.set("user_data", data)
        cached = test_cache.get("user_data")
        assert cached == data

        # List
        items = [1, 2, 3, "four", {"five": 5}]
        test_cache.set("items", items)
        assert test_cache.get("items") == items

    def test_cache_increment(self, test_cache):
        """Test cache counter operations."""
        # Increment from zero
        assert test_cache.increment("counter") == 1
        assert test_cache.increment("counter") == 2
        assert test_cache.increment("counter", amount=5) == 7

    def test_cache_batch_operations(self, test_cache):
        """Test batch get/set operations."""
        # Set many
        data = {"key1": "val1", "key2": "val2", "key3": "val3"}
        test_cache.set_many(data)

        # Get many
        results = test_cache.get_many(["key1", "key2", "key3"])
        assert results == data

    def test_cached_decorator(self):
        """Test @cached decorator."""
        from dataforge_common import cached

        call_count = {"value": 0}

        @cached(ttl=300, key_prefix="test:")
        def expensive_function(x):
            call_count["value"] += 1
            return x * 2

        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count["value"] == 1

        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count["value"] == 1  # Not incremented

        # Different argument should execute function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count["value"] == 2
