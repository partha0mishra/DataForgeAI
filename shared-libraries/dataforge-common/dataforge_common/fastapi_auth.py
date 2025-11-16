"""FastAPI authentication dependencies."""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .auth import get_auth_manager, User, TokenData
from .logging import get_logger

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current authenticated user from JWT token.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    auth_manager = get_auth_manager()

    token = credentials.credentials
    token_data = auth_manager.verify_token(token)

    if token_data is None:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_manager.get_user(token_data.username)
    if user is None:
        logger.warning(f"User not found: {token_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        auth_manager = get_auth_manager()
        token_data = auth_manager.verify_token(credentials.credentials)

        if token_data is None:
            return None

        user = auth_manager.get_user(token_data.username)
        if user and user.is_active:
            return user

        return None
    except Exception:
        return None


def require_roles(required_roles: List[str]):
    """Create dependency that requires specific roles.

    Args:
        required_roles: List of required role names

    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """Check if user has required roles.

        Args:
            current_user: Current authenticated user

        Returns:
            User if has required roles

        Raises:
            HTTPException: If user lacks required roles
        """
        auth_manager = get_auth_manager()

        if not auth_manager.require_roles(current_user, required_roles):
            logger.warning(
                f"User {current_user.username} lacks required roles: {required_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}",
            )

        return current_user

    return role_checker


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Require superuser access.

    Args:
        current_user: Current authenticated user

    Returns:
        User if superuser

    Raises:
        HTTPException: If user is not superuser
    """
    if not current_user.is_superuser:
        logger.warning(f"Non-superuser attempted admin access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )

    return current_user
