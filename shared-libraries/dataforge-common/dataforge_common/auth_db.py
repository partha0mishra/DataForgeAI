"""Production-grade database-backed authentication and authorization.

This module provides persistent authentication using PostgreSQL for user storage,
Redis for token blacklisting, and comprehensive RBAC support.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from functools import wraps
import time

try:
    from jose import JWTError, jwt
    from passlib.context import CryptContext
except ImportError:
    raise ImportError(
        "Authentication requires additional dependencies. "
        "Install with: pip install python-jose[cryptography] passlib[bcrypt]"
    )

from .logging import get_logger
from .database import DatabaseManager, get_database_manager
from .repository import UserRepository, RoleRepository, SessionRepository, AuditEventRepository
from .models import UserModel, RoleModel
from .cache import Cache, get_cache

logger = get_logger(__name__)


# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Rate limiting configuration
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCKOUT_DURATION = int(os.getenv("LOGIN_LOCKOUT_DURATION", "900"))  # 15 minutes

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class TokenData:
    """Token payload data."""
    user_id: str
    username: str
    roles: List[str]
    exp: datetime
    jti: Optional[str] = None  # JWT ID for revocation


@dataclass
class AuthContext:
    """Authentication context for the current request."""
    user: UserModel
    token_data: TokenData
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class TokenBlacklist:
    """Manage token revocation using Redis."""

    def __init__(self, cache: Optional[Cache] = None):
        """Initialize token blacklist.

        Args:
            cache: Cache instance for Redis operations
        """
        self.cache = cache or get_cache()

    def revoke_token(self, jti: str, expires_at: datetime) -> None:
        """Revoke a token by adding it to blacklist.

        Args:
            jti: JWT ID (unique token identifier)
            expires_at: Token expiration time
        """
        if not jti:
            logger.warning("Attempted to revoke token without JTI")
            return

        # Calculate TTL until token would naturally expire
        ttl = int((expires_at - datetime.utcnow()).total_seconds())

        if ttl > 0:
            # Store in Redis with TTL
            self.cache.set(
                f"blacklist:{jti}",
                "revoked",
                ttl=ttl
            )
            logger.info(f"Token {jti} revoked and blacklisted for {ttl}s")

    def is_revoked(self, jti: str) -> bool:
        """Check if token is revoked.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is revoked
        """
        if not jti:
            return False

        result = self.cache.get(f"blacklist:{jti}")
        return result is not None

    def revoke_user_tokens(self, user_id: str) -> None:
        """Revoke all tokens for a user.

        Args:
            user_id: User ID
        """
        # Set a flag in cache that user's tokens are invalidated
        self.cache.set(
            f"user_revoked:{user_id}",
            str(datetime.utcnow().timestamp()),
            ttl=REFRESH_TOKEN_EXPIRE_DAYS * 86400  # 7 days
        )
        logger.info(f"All tokens revoked for user {user_id}")

    def is_user_tokens_revoked(self, user_id: str, token_issued_at: datetime) -> bool:
        """Check if all user tokens issued before a certain time are revoked.

        Args:
            user_id: User ID
            token_issued_at: When the token was issued

        Returns:
            True if user's tokens are revoked
        """
        revoked_timestamp = self.cache.get(f"user_revoked:{user_id}")
        if not revoked_timestamp:
            return False

        try:
            revoked_time = float(revoked_timestamp)
            return token_issued_at.timestamp() < revoked_time
        except (ValueError, AttributeError):
            return False


class RateLimiter:
    """Rate limiting for authentication endpoints."""

    def __init__(self, cache: Optional[Cache] = None):
        """Initialize rate limiter.

        Args:
            cache: Cache instance for Redis operations
        """
        self.cache = cache or get_cache()

    def record_login_attempt(self, identifier: str, success: bool) -> None:
        """Record a login attempt.

        Args:
            identifier: IP address or username
            success: Whether login was successful
        """
        key = f"login_attempts:{identifier}"

        if success:
            # Clear attempts on successful login
            self.cache.delete(key)
        else:
            # Increment failed attempts
            current = self.cache.get(key)
            attempts = int(current) if current else 0
            attempts += 1

            self.cache.set(key, str(attempts), ttl=LOGIN_LOCKOUT_DURATION)
            logger.warning(f"Failed login attempt {attempts}/{MAX_LOGIN_ATTEMPTS} for {identifier}")

    def is_locked_out(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """Check if identifier is locked out.

        Args:
            identifier: IP address or username

        Returns:
            Tuple of (is_locked, remaining_seconds)
        """
        key = f"login_attempts:{identifier}"
        current = self.cache.get(key)

        if not current:
            return False, None

        attempts = int(current)
        if attempts >= MAX_LOGIN_ATTEMPTS:
            # Get TTL of the key
            ttl = self.cache.ttl(key) if hasattr(self.cache, 'ttl') else LOGIN_LOCKOUT_DURATION
            return True, ttl

        return False, None


class ProductionAuthManager:
    """Production-grade authentication manager with database persistence."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        cache: Optional[Cache] = None,
    ):
        """Initialize production auth manager.

        Args:
            db_manager: Database manager instance
            cache: Cache instance for Redis
        """
        self.db_manager = db_manager or get_database_manager()
        self.cache = cache or get_cache()

        # Initialize repositories
        self.user_repo = UserRepository(self.db_manager)
        self.role_repo = RoleRepository(self.db_manager)
        self.session_repo = SessionRepository(self.db_manager)
        self.audit_repo = AuditEventRepository(self.db_manager)

        # Initialize security components
        self.token_blacklist = TokenBlacklist(self.cache)
        self.rate_limiter = RateLimiter(self.cache)

        # Ensure default roles and admin user exist
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default roles and admin user."""
        try:
            # Ensure default roles exist
            self.role_repo.ensure_default_roles()

            # Check if admin user exists
            admin = self.user_repo.get_by_username("admin")
            if not admin:
                self._create_default_admin()
                logger.info("Default admin user created")
        except Exception as e:
            logger.error(f"Failed to initialize defaults: {str(e)}")

    def _create_default_admin(self) -> None:
        """Create default admin user."""
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

        # Get admin role
        admin_role = self.role_repo.get_by_name("admin")
        user_role = self.role_repo.get_by_name("user")

        # Create admin user
        admin_user = self.user_repo.create(
            user_id=f"user_admin_{datetime.utcnow().timestamp()}",
            username="admin",
            email="admin@dataforge.ai",
            hashed_password=self.hash_password(admin_password),
            is_active=True,
            is_superuser=True,
        )

        # Add roles
        if admin_role:
            self.user_repo.add_role(admin_user.user_id, admin_role)
        if user_role:
            self.user_repo.add_role(admin_user.user_id, user_role)

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

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
        is_superuser: bool = False,
    ) -> UserModel:
        """Create new user with persistent storage.

        Args:
            username: Username
            email: Email address
            password: Plain text password
            roles: List of role names
            is_superuser: Whether user is superuser

        Returns:
            Created user model

        Raises:
            ValueError: If user already exists
        """
        # Check if user exists
        if self.user_repo.get_by_username(username):
            raise ValueError(f"User {username} already exists")

        if self.user_repo.get_by_email(email):
            raise ValueError(f"Email {email} already registered")

        # Generate user ID
        user_id = f"user_{hashlib.sha256(username.encode()).hexdigest()[:16]}_{int(datetime.utcnow().timestamp())}"

        # Create user
        user = self.user_repo.create(
            user_id=user_id,
            username=username,
            email=email,
            hashed_password=self.hash_password(password),
            is_active=True,
            is_superuser=is_superuser,
        )

        # Assign roles
        if roles:
            for role_name in roles:
                role = self.role_repo.get_by_name(role_name)
                if role:
                    self.user_repo.add_role(user.user_id, role)
                else:
                    logger.warning(f"Role {role_name} not found")

        logger.info(f"Created user: {username} ({user_id})")
        return user

    def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
    ) -> Optional[UserModel]:
        """Authenticate user with rate limiting.

        Args:
            username: Username
            password: Password
            ip_address: Client IP address for rate limiting

        Returns:
            User model if authenticated, None otherwise
        """
        # Check rate limiting
        identifier = ip_address or username
        is_locked, remaining = self.rate_limiter.is_locked_out(identifier)

        if is_locked:
            logger.warning(f"Login attempt blocked - account locked for {remaining}s: {identifier}")
            return None

        # Get user from database
        user = self.user_repo.get_by_username(username)

        if not user:
            logger.warning(f"Authentication failed: User {username} not found")
            self.rate_limiter.record_login_attempt(identifier, success=False)
            return None

        if not user.is_active:
            logger.warning(f"Authentication failed: User {username} is inactive")
            return None

        if not self.verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for {username}")
            self.rate_limiter.record_login_attempt(identifier, success=False)
            return None

        # Successful authentication
        self.rate_limiter.record_login_attempt(identifier, success=True)
        self.user_repo.update_last_login(user.user_id)

        logger.info(f"User authenticated: {username}")
        return user

    def create_access_token(
        self,
        user: UserModel,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create JWT access token with JTI for revocation support.

        Args:
            user: User model
            expires_delta: Token expiration delta

        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # Generate unique token ID for revocation support
        jti = secrets.token_urlsafe(32)

        # Get user roles
        role_names = [role.name for role in user.roles]

        to_encode = {
            "sub": user.user_id,
            "username": user.username,
            "roles": role_names,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": jti,
        }

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Created access token for {user.username} (JTI: {jti})")

        return encoded_jwt

    def create_refresh_token(self, user: UserModel) -> str:
        """Create JWT refresh token and store in database.

        Args:
            user: User model

        Returns:
            JWT refresh token
        """
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        jti = secrets.token_urlsafe(32)

        to_encode = {
            "sub": user.user_id,
            "username": user.username,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": jti,
        }

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        # Store session in database
        session_id = f"session_{secrets.token_urlsafe(16)}"
        self.session_repo.create(
            session_id=session_id,
            user_id=user.user_id,
            refresh_token=encoded_jwt,
            expires_at=expire,
            is_active=True,
        )

        logger.info(f"Created refresh token for {user.username} (JTI: {jti})")
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token with revocation check.

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
            iat: int = payload.get("iat")
            jti: str = payload.get("jti")

            if user_id is None or username is None:
                logger.warning("Token missing required fields")
                return None

            # Check if token is blacklisted
            if jti and self.token_blacklist.is_revoked(jti):
                logger.warning(f"Token {jti} is blacklisted")
                return None

            # Check if all user tokens are revoked
            if iat and self.token_blacklist.is_user_tokens_revoked(
                user_id, datetime.fromtimestamp(iat)
            ):
                logger.warning(f"All tokens revoked for user {user_id}")
                return None

            token_data = TokenData(
                user_id=user_id,
                username=username,
                roles=roles,
                exp=datetime.fromtimestamp(exp),
                jti=jti,
            )

            return token_data

        except JWTError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            return None

    def revoke_token(self, token: str) -> bool:
        """Revoke a specific token.

        Args:
            token: JWT token to revoke

        Returns:
            True if revoked successfully
        """
        token_data = self.verify_token(token)
        if not token_data or not token_data.jti:
            return False

        self.token_blacklist.revoke_token(token_data.jti, token_data.exp)
        return True

    def revoke_user_tokens(self, user_id: str) -> None:
        """Revoke all tokens for a user.

        Args:
            user_id: User ID
        """
        self.token_blacklist.revoke_user_tokens(user_id)
        self.session_repo.invalidate_user_sessions(user_id)
        logger.info(f"Revoked all tokens and sessions for user {user_id}")

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token or None
        """
        # Verify refresh token
        token_data = self.verify_token(refresh_token)
        if not token_data:
            return None

        # Check if session exists and is active
        session = self.session_repo.get_by_refresh_token(refresh_token)
        if not session or not session.is_active:
            logger.warning("Refresh token session not found or inactive")
            return None

        # Get user
        user = self.user_repo.get_by_id(token_data.user_id)
        if not user or not user.is_active:
            logger.warning("User not found or inactive")
            return None

        # Create new access token
        access_token = self.create_access_token(user)
        logger.info(f"Access token refreshed for {user.username}")

        return access_token

    def has_role(self, user: UserModel, role: str) -> bool:
        """Check if user has a specific role.

        Args:
            user: User model
            role: Role name

        Returns:
            True if user has role
        """
        if user.is_superuser:
            return True

        return any(r.name == role for r in user.roles)

    def has_any_role(self, user: UserModel, roles: List[str]) -> bool:
        """Check if user has any of the specified roles.

        Args:
            user: User model
            roles: List of role names

        Returns:
            True if user has any role
        """
        if user.is_superuser:
            return True

        return any(self.has_role(user, role) for role in roles)

    def require_roles(self, user: UserModel, required_roles: List[str]) -> bool:
        """Check if user has all required roles.

        Args:
            user: User model
            required_roles: List of required role names

        Returns:
            True if user has all required roles
        """
        if user.is_superuser:
            return True

        return all(self.has_role(user, role) for role in required_roles)

    def log_audit_event(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str = "success",
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an audit event.

        Args:
            user_id: User ID
            action: Action performed
            resource_type: Type of resource accessed
            resource_id: Resource identifier
            status: Event status (success/failure)
            error_message: Error message if failed
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional metadata
        """
        event_id = f"audit_{secrets.token_urlsafe(16)}"

        try:
            self.audit_repo.create(
                event_id=event_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")


# Global production auth manager
_prod_auth_manager: Optional[ProductionAuthManager] = None


def get_prod_auth_manager() -> ProductionAuthManager:
    """Get global production auth manager.

    Returns:
        Production auth manager instance
    """
    global _prod_auth_manager
    if _prod_auth_manager is None:
        _prod_auth_manager = ProductionAuthManager()
    return _prod_auth_manager


def init_prod_auth(
    db_manager: Optional[DatabaseManager] = None,
    cache: Optional[Cache] = None,
):
    """Initialize production authentication system.

    Args:
        db_manager: Database manager instance
        cache: Cache instance
    """
    global _prod_auth_manager
    _prod_auth_manager = ProductionAuthManager(db_manager, cache)
    logger.info("Production authentication system initialized")


# FastAPI dependency helper
async def get_current_user(
    token: str,
    auth_manager: Optional[ProductionAuthManager] = None,
) -> UserModel:
    """FastAPI dependency to get current user from token.

    Args:
        token: JWT token from Authorization header
        auth_manager: Auth manager instance

    Returns:
        Current user model

    Raises:
        HTTPException: If authentication fails
    """
    manager = auth_manager or get_prod_auth_manager()

    token_data = manager.verify_token(token)
    if not token_data:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = manager.user_repo.get_by_id(token_data.user_id)
    if not user or not user.is_active:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def require_role(required_role: str):
    """Decorator to require specific role for endpoint.

    Args:
        required_role: Required role name

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (injected by FastAPI dependency)
            user = kwargs.get('current_user')
            if not user:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            manager = get_prod_auth_manager()
            if not manager.has_role(user, required_role):
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{required_role}' required",
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
