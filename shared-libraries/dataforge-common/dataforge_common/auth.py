"""Authentication and authorization utilities."""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import hashlib
import secrets

try:
    from jose import JWTError, jwt
    from passlib.context import CryptContext
except ImportError:
    raise ImportError(
        "Authentication requires additional dependencies. "
        "Install with: pip install python-jose[cryptography] passlib[bcrypt]"
    )

from .logging import get_logger

logger = get_logger(__name__)


# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class User:
    """User model."""
    user_id: str
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    roles: List[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class TokenData:
    """Token payload data."""
    user_id: str
    username: str
    roles: List[str]
    exp: datetime


class AuthManager:
    """Manage authentication and authorization."""

    def __init__(self):
        """Initialize auth manager."""
        self.users: Dict[str, User] = {}
        self._create_default_users()

    def _create_default_users(self):
        """Create default admin user."""
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

        admin = User(
            user_id="admin_001",
            username="admin",
            email="admin@dataforge.ai",
            hashed_password=self.hash_password(admin_password),
            is_superuser=True,
            roles=["admin", "user"],
        )
        self.users["admin"] = admin

        logger.info("Default admin user created")

    def hash_password(self, password: str) -> str:
        """Hash a password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: Optional[List[str]] = None,
    ) -> User:
        """Create new user.

        Args:
            username: Username
            email: Email address
            password: Plain text password
            roles: User roles

        Returns:
            Created user
        """
        if username in self.users:
            raise ValueError(f"User {username} already exists")

        user_id = f"user_{len(self.users) + 1}_{datetime.utcnow().timestamp()}"

        user = User(
            user_id=user_id,
            username=username,
            email=email,
            hashed_password=self.hash_password(password),
            roles=roles or ["user"],
        )

        self.users[username] = user
        logger.info(f"Created user: {username}")

        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password.

        Args:
            username: Username
            password: Password

        Returns:
            User if authenticated, None otherwise
        """
        user = self.users.get(username)

        if not user:
            logger.warning(f"Authentication failed: User {username} not found")
            return None

        if not user.is_active:
            logger.warning(f"Authentication failed: User {username} is inactive")
            return None

        if not self.verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for {username}")
            return None

        logger.info(f"User authenticated: {username}")
        return user

    def create_access_token(
        self,
        user: User,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create JWT access token.

        Args:
            user: User to create token for
            expires_delta: Token expiration delta

        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "sub": user.user_id,
            "username": user.username,
            "roles": user.roles,
            "exp": expire,
            "type": "access",
        }

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Created access token for {user.username}")

        return encoded_jwt

    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token.

        Args:
            user: User to create token for

        Returns:
            JWT refresh token
        """
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode = {
            "sub": user.user_id,
            "username": user.username,
            "exp": expire,
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Created refresh token for {user.username}")

        return encoded_jwt

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            roles: List[str] = payload.get("roles", [])
            exp: int = payload.get("exp")

            if user_id is None or username is None:
                return None

            token_data = TokenData(
                user_id=user_id,
                username=username,
                roles=roles,
                exp=datetime.fromtimestamp(exp),
            )

            return token_data

        except JWTError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            return None

    def get_user(self, username: str) -> Optional[User]:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User if found, None otherwise
        """
        return self.users.get(username)

    def has_role(self, user: User, role: str) -> bool:
        """Check if user has role.

        Args:
            user: User to check
            role: Role name

        Returns:
            True if user has role
        """
        return role in user.roles or user.is_superuser

    def require_roles(self, user: User, required_roles: List[str]) -> bool:
        """Check if user has all required roles.

        Args:
            user: User to check
            required_roles: List of required roles

        Returns:
            True if user has all required roles
        """
        if user.is_superuser:
            return True

        return all(role in user.roles for role in required_roles)


# Global auth manager
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get global auth manager.

    Returns:
        Global auth manager instance
    """
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def init_auth(secret_key: Optional[str] = None):
    """Initialize authentication system.

    Args:
        secret_key: Optional custom secret key
    """
    global SECRET_KEY
    if secret_key:
        SECRET_KEY = secret_key

    global _auth_manager
    _auth_manager = AuthManager()

    logger.info("Authentication system initialized")
