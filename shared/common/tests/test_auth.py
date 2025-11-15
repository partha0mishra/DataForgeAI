"""Tests for authentication module."""

import pytest
from dataforge_common.auth import (
    EncryptionManager,
    JWTManager,
    PermissionChecker,
    generate_api_key,
    hash_password,
    verify_password,
)


def test_jwt_create_and_verify():
    """Test JWT token creation and verification."""
    manager = JWTManager(secret_key="test-secret")

    # Create token
    token = manager.create_token(user_id="user123", roles=["admin", "user"])

    # Verify token
    payload = manager.verify_token(token)

    assert payload.user_id == "user123"
    assert "admin" in payload.roles
    assert "user" in payload.roles


def test_jwt_invalid_token():
    """Test JWT verification with invalid token."""
    manager = JWTManager(secret_key="test-secret")

    with pytest.raises(ValueError, match="Invalid token"):
        manager.verify_token("invalid.token.here")


def test_permission_checker():
    """Test role-based access control."""
    checker = PermissionChecker()

    user_roles = ["user", "editor"]

    assert checker.has_role(user_roles, "user")
    assert not checker.has_role(user_roles, "admin")
    assert checker.has_any_role(user_roles, ["admin", "editor"])
    assert not checker.has_all_roles(user_roles, ["user", "admin"])


def test_password_hashing():
    """Test password hashing and verification."""
    password = "mySecurePassword123"

    # Hash password
    hashed, salt = hash_password(password)

    # Verify correct password
    assert verify_password(password, hashed, salt)

    # Verify incorrect password
    assert not verify_password("wrongPassword", hashed, salt)


def test_encryption():
    """Test data encryption and decryption."""
    manager = EncryptionManager()

    original_data = "sensitive information"
    encrypted = manager.encrypt(original_data)
    decrypted = manager.decrypt(encrypted)

    assert decrypted == original_data
    assert encrypted != original_data


def test_api_key_generation():
    """Test API key generation."""
    api_key = generate_api_key(prefix="test", length=16)

    assert api_key.startswith("test_")
    assert len(api_key) > 20
