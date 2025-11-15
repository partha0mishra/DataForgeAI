"""Authentication and authorization utilities for DataForge platform."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import jwt
from cryptography.fernet import Fernet
from pydantic import BaseModel


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    user_id: str
    roles: List[str] = []
    email: Optional[str] = None
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None


class JWTManager:
    """
    JWT token management for authentication.

    Example:
        manager = JWTManager(secret_key="your-secret")
        token = manager.create_token(user_id="user123", roles=["admin"])
        payload = manager.verify_token(token)
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        expiration_hours: int = 24,
    ):
        """
        Initialize JWT manager.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            expiration_hours: Token expiration time in hours
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours

    def create_token(
        self,
        user_id: str,
        roles: Optional[List[str]] = None,
        email: Optional[str] = None,
        custom_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new JWT token.

        Args:
            user_id: Unique user identifier
            roles: List of user roles
            email: User email address
            custom_claims: Additional custom claims

        Returns:
            str: Encoded JWT token
        """
        now = datetime.utcnow()
        exp = now + timedelta(hours=self.expiration_hours)

        payload = {
            "user_id": user_id,
            "roles": roles or [],
            "exp": exp,
            "iat": now,
        }

        if email:
            payload["email"] = email

        if custom_claims:
            payload.update(custom_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token: str) -> TokenPayload:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenPayload: Decoded token payload

        Raises:
            jwt.InvalidTokenError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    def refresh_token(self, token: str) -> str:
        """
        Refresh an existing token (extend expiration).

        Args:
            token: Existing JWT token

        Returns:
            str: New token with extended expiration
        """
        payload = self.verify_token(token)
        return self.create_token(
            user_id=payload.user_id,
            roles=payload.roles,
            email=payload.email,
        )


def verify_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> Dict[str, Any]:
    """
    Verify JWT token (standalone function).

    Args:
        token: JWT token string
        secret_key: Secret key for verification
        algorithm: JWT algorithm

    Returns:
        dict: Decoded token payload

    Example:
        payload = verify_token(token, "your-secret")
        user_id = payload["user_id"]
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Token verification failed: {str(e)}")


class PermissionChecker:
    """
    Role-based access control (RBAC) helper.

    Example:
        checker = PermissionChecker()
        if checker.has_permission(user_roles, required_roles=["admin"]):
            # Allow access
    """

    @staticmethod
    def has_role(user_roles: List[str], required_role: str) -> bool:
        """
        Check if user has a specific role.

        Args:
            user_roles: List of roles assigned to user
            required_role: Role to check for

        Returns:
            bool: True if user has the role
        """
        return required_role in user_roles

    @staticmethod
    def has_any_role(user_roles: List[str], required_roles: List[str]) -> bool:
        """
        Check if user has any of the required roles.

        Args:
            user_roles: List of roles assigned to user
            required_roles: List of acceptable roles

        Returns:
            bool: True if user has at least one role
        """
        return bool(set(user_roles) & set(required_roles))

    @staticmethod
    def has_all_roles(user_roles: List[str], required_roles: List[str]) -> bool:
        """
        Check if user has all required roles.

        Args:
            user_roles: List of roles assigned to user
            required_roles: List of required roles

        Returns:
            bool: True if user has all roles
        """
        return set(required_roles).issubset(set(user_roles))


class EncryptionManager:
    """
    Data encryption/decryption using Fernet (symmetric encryption).

    Example:
        manager = EncryptionManager(key="your-key")
        encrypted = manager.encrypt("sensitive data")
        decrypted = manager.decrypt(encrypted)
    """

    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryption manager.

        Args:
            key: Encryption key (base64 encoded). If None, generates new key.
        """
        if key:
            self.key = key.encode() if isinstance(key, str) else key
        else:
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> str:
        """
        Encrypt string data.

        Args:
            data: String to encrypt

        Returns:
            str: Encrypted data (base64 encoded)
        """
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data.

        Args:
            encrypted_data: Encrypted string

        Returns:
            str: Decrypted original data
        """
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.

        Returns:
            str: Base64 encoded encryption key
        """
        return Fernet.generate_key().decode()


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash password using SHA-256 with salt.

    Args:
        password: Plain text password
        salt: Salt for hashing (generated if not provided)

    Returns:
        tuple: (hashed_password, salt)

    Example:
        hashed, salt = hash_password("mypassword")
    """
    if not salt:
        salt = secrets.token_hex(16)

    pwd_bytes = password.encode()
    salt_bytes = salt.encode()
    hashed = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100000)
    return hashed.hex(), salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify password against hash.

    Args:
        password: Plain text password to verify
        hashed_password: Stored password hash
        salt: Salt used in hashing

    Returns:
        bool: True if password matches

    Example:
        is_valid = verify_password("mypassword", stored_hash, stored_salt)
    """
    test_hash, _ = hash_password(password, salt)
    return test_hash == hashed_password


def generate_api_key(prefix: str = "dfai", length: int = 32) -> str:
    """
    Generate a random API key.

    Args:
        prefix: Prefix for the API key
        length: Length of random portion

    Returns:
        str: Generated API key

    Example:
        api_key = generate_api_key(prefix="dfai")
        # Returns: "dfai_a1b2c3d4e5f6..."
    """
    random_part = secrets.token_urlsafe(length)
    return f"{prefix}_{random_part}"
