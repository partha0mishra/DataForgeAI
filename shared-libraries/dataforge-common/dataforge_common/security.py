"""FastAPI security middleware and dependencies for DataForge AI.

This module provides comprehensive security middleware including:
- JWT authentication (database-backed)
- OAuth2/OIDC authentication
- Role-based access control (RBAC)
- Rate limiting
- Audit logging
- Request validation
"""

from typing import Optional, List, Callable, Dict, Any
from datetime import datetime
from functools import wraps

try:
    from fastapi import Request, HTTPException, status, Depends
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response, JSONResponse
except ImportError:
    raise ImportError("Security middleware requires fastapi. Install with: pip install fastapi")

from .logging import get_logger
from .auth_db import ProductionAuthManager, get_prod_auth_manager
from .oauth2 import OAuth2Manager, init_oauth2_from_env
from .models import UserModel

logger = get_logger(__name__)

# Security scheme
security_scheme = HTTPBearer()


class AuthenticationMode:
    """Authentication modes."""
    DATABASE = "database"  # Database-backed JWT
    OAUTH2 = "oauth2"  # OAuth2/OIDC
    BOTH = "both"  # Try both methods


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for FastAPI applications."""

    def __init__(
        self,
        app,
        auth_manager: Optional[ProductionAuthManager] = None,
        oauth_manager: Optional[OAuth2Manager] = None,
        exempt_paths: Optional[List[str]] = None,
        enable_audit: bool = True,
    ):
        """Initialize security middleware.

        Args:
            app: FastAPI application
            auth_manager: Database auth manager
            oauth_manager: OAuth2 manager
            exempt_paths: Paths to exempt from authentication
            enable_audit: Enable audit logging
        """
        super().__init__(app)
        self.auth_manager = auth_manager or get_prod_auth_manager()
        self.oauth_manager = oauth_manager or init_oauth2_from_env()
        self.exempt_paths = exempt_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        self.enable_audit = enable_audit

    async def dispatch(self, request: Request, call_next):
        """Process request through security middleware."""
        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Add request ID for tracing
        request.state.request_id = self._generate_request_id()

        # Extract client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Store in request state
        request.state.client_ip = client_ip
        request.state.user_agent = user_agent

        try:
            # Process request
            response = await call_next(request)

            # Log audit event if enabled
            if self.enable_audit and hasattr(request.state, "user"):
                await self._log_audit_event(
                    request=request,
                    response=response,
                    status="success"
                )

            return response

        except Exception as e:
            logger.error(f"Request processing error: {str(e)}")

            # Log failed audit event
            if self.enable_audit and hasattr(request.state, "user"):
                await self._log_audit_event(
                    request=request,
                    response=None,
                    status="failure",
                    error_message=str(e)
                )

            raise

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import secrets
        return f"req_{secrets.token_hex(8)}"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check X-Forwarded-For header (behind proxy)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    async def _log_audit_event(
        self,
        request: Request,
        response: Optional[Response],
        status: str,
        error_message: Optional[str] = None,
    ):
        """Log audit event."""
        try:
            user = getattr(request.state, "user", None)
            if not user:
                return

            user_id = user.user_id if isinstance(user, UserModel) else user.get("sub", "unknown")

            self.auth_manager.log_audit_event(
                user_id=user_id,
                action=request.method,
                resource_type="api",
                resource_id=request.url.path,
                status=status,
                error_message=error_message,
                ip_address=getattr(request.state, "client_ip", None),
                user_agent=getattr(request.state, "user_agent", None),
                metadata={
                    "request_id": getattr(request.state, "request_id", None),
                    "status_code": response.status_code if response else None,
                }
            )
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ):
        """Initialize rate limit middleware.

        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute
            burst_size: Burst allowance
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting."""
        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit (implement using Redis or in-memory)
        # For now, pass through - implement based on your needs

        response = await call_next(request)
        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Prefer authenticated user
        if hasattr(request.state, "user"):
            user = request.state.user
            if isinstance(user, UserModel):
                return f"user:{user.user_id}"
            elif isinstance(user, dict):
                return f"user:{user.get('sub', 'unknown')}"

        # Fallback to IP address
        if request.client:
            return f"ip:{request.client.host}"

        return "unknown"


# FastAPI Dependencies

async def get_current_user_db(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    auth_manager: ProductionAuthManager = Depends(get_prod_auth_manager),
) -> UserModel:
    """Get current user from database JWT token.

    Args:
        credentials: Bearer token credentials
        auth_manager: Authentication manager

    Returns:
        Current user model

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    # Verify token
    token_data = auth_manager.verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = auth_manager.user_repo.get_by_id(token_data.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_oauth(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> Dict[str, Any]:
    """Get current user from OAuth2 token.

    Args:
        credentials: Bearer token credentials

    Returns:
        Token payload with user info

    Raises:
        HTTPException: If OAuth2 not configured or authentication fails
    """
    oauth_manager = init_oauth2_from_env()
    if not oauth_manager:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth2 authentication not configured",
        )

    token = credentials.credentials
    payload = await oauth_manager.verify_token(token)

    # Extract roles
    payload["roles"] = oauth_manager.extract_roles(payload)

    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    mode: str = AuthenticationMode.DATABASE,
) -> Any:
    """Get current user with flexible authentication mode.

    Args:
        credentials: Bearer token credentials
        mode: Authentication mode (database, oauth2, or both)

    Returns:
        User (UserModel or OAuth payload)

    Raises:
        HTTPException: If authentication fails
    """
    if mode == AuthenticationMode.DATABASE:
        return await get_current_user_db(credentials)

    elif mode == AuthenticationMode.OAUTH2:
        return await get_current_user_oauth(credentials)

    elif mode == AuthenticationMode.BOTH:
        # Try database first, then OAuth2
        try:
            return await get_current_user_db(credentials)
        except HTTPException:
            return await get_current_user_oauth(credentials)

    else:
        raise ValueError(f"Invalid authentication mode: {mode}")


def require_roles(required_roles: List[str]):
    """Dependency to require specific roles.

    Args:
        required_roles: List of required role names

    Returns:
        FastAPI dependency
    """
    async def check_roles(
        current_user: Any = Depends(get_current_user)
    ) -> Any:
        """Check if user has required roles."""
        # Handle UserModel
        if isinstance(current_user, UserModel):
            user_roles = [role.name for role in current_user.roles]
            is_superuser = current_user.is_superuser
        # Handle OAuth payload
        elif isinstance(current_user, dict):
            user_roles = current_user.get("roles", [])
            is_superuser = "admin" in user_roles
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid user object",
            )

        # Superusers have all permissions
        if is_superuser:
            return current_user

        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            logger.warning(
                f"Access denied: User requires roles {required_roles}, has {user_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}",
            )

        return current_user

    return check_roles


def require_any_role(required_roles: List[str]):
    """Dependency to require any of the specified roles (alias for require_roles)."""
    return require_roles(required_roles)


def require_all_roles(required_roles: List[str]):
    """Dependency to require all specified roles.

    Args:
        required_roles: List of required role names

    Returns:
        FastAPI dependency
    """
    async def check_all_roles(
        current_user: Any = Depends(get_current_user)
    ) -> Any:
        """Check if user has all required roles."""
        # Handle UserModel
        if isinstance(current_user, UserModel):
            user_roles = [role.name for role in current_user.roles]
            is_superuser = current_user.is_superuser
        # Handle OAuth payload
        elif isinstance(current_user, dict):
            user_roles = current_user.get("roles", [])
            is_superuser = "admin" in user_roles
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid user object",
            )

        # Superusers have all permissions
        if is_superuser:
            return current_user

        # Check if user has ALL required roles
        if not all(role in user_roles for role in required_roles):
            missing = [r for r in required_roles if r not in user_roles]
            logger.warning(
                f"Access denied: User missing roles {missing}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {missing}",
            )

        return current_user

    return check_all_roles


# Convenience dependencies for common roles
RequireAdmin = require_roles(["admin"])
RequireAnalyst = require_roles(["analyst"])
RequireDeveloper = require_roles(["developer"])
RequireUser = require_roles(["user"])


# Optional user dependency (doesn't raise if not authenticated)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[Any]:
    """Get current user if authenticated, None otherwise.

    Args:
        credentials: Optional bearer token credentials

    Returns:
        User if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# Decorator for endpoint-level authorization
def authorize(required_roles: Optional[List[str]] = None):
    """Decorator for endpoint authorization.

    Args:
        required_roles: List of required role names

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (injected by FastAPI)
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            if required_roles:
                # Check roles
                if isinstance(current_user, UserModel):
                    user_roles = [role.name for role in current_user.roles]
                    is_superuser = current_user.is_superuser
                elif isinstance(current_user, dict):
                    user_roles = current_user.get("roles", [])
                    is_superuser = "admin" in user_roles
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Invalid user object",
                    )

                if not is_superuser and not any(role in user_roles for role in required_roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required roles: {required_roles}",
                    )

            return await func(*args, **kwargs)

        return wrapper
    return decorator
