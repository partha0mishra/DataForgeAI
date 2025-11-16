"""FastAPI authentication router."""

from datetime import timedelta
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status

from .auth import get_auth_manager, User, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from .fastapi_auth import get_current_user
from .logging import get_logger

logger = get_logger(__name__)


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class UserCreateRequest(BaseModel):
    """User creation request."""
    username: str
    email: EmailStr
    password: str
    roles: Optional[List[str]] = None


class UserResponse(BaseModel):
    """User response."""
    user_id: str
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    roles: List[str]

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        """Create response from user."""
        return cls(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            roles=user.roles,
        )


def create_auth_router() -> APIRouter:
    """Create authentication router.

    Returns:
        Configured authentication router
    """
    router = APIRouter(prefix="/auth", tags=["authentication"])

    @router.post("/login", response_model=TokenResponse)
    async def login(request: LoginRequest):
        """Authenticate user and return tokens.

        Args:
            request: Login credentials

        Returns:
            Access and refresh tokens

        Raises:
            HTTPException: If authentication fails
        """
        auth_manager = get_auth_manager()

        user = auth_manager.authenticate_user(request.username, request.password)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create tokens
        access_token = auth_manager.create_access_token(user)
        refresh_token = auth_manager.create_refresh_token(user)

        logger.info(f"User logged in: {user.username}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @router.post("/refresh", response_model=TokenResponse)
    async def refresh(request: RefreshRequest):
        """Refresh access token.

        Args:
            request: Refresh token

        Returns:
            New access and refresh tokens

        Raises:
            HTTPException: If refresh token is invalid
        """
        auth_manager = get_auth_manager()

        # Verify refresh token
        token_data = auth_manager.verify_token(request.refresh_token)

        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user
        user = auth_manager.get_user(token_data.username)

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create new tokens
        access_token = auth_manager.create_access_token(user)
        refresh_token = auth_manager.create_refresh_token(user)

        logger.info(f"Token refreshed for user: {user.username}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @router.get("/me", response_model=UserResponse)
    async def get_me(current_user: User = Depends(get_current_user)):
        """Get current user information.

        Args:
            current_user: Authenticated user

        Returns:
            User information
        """
        return UserResponse.from_user(current_user)

    @router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    async def create_user(
        request: UserCreateRequest,
        current_user: User = Depends(get_current_user),
    ):
        """Create new user (admin only).

        Args:
            request: User creation request
            current_user: Authenticated admin user

        Returns:
            Created user

        Raises:
            HTTPException: If user lacks permissions or username exists
        """
        auth_manager = get_auth_manager()

        # Check if current user is admin
        if not auth_manager.has_role(current_user, "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required to create users",
            )

        try:
            user = auth_manager.create_user(
                username=request.username,
                email=request.email,
                password=request.password,
                roles=request.roles,
            )

            logger.info(f"User created: {user.username} by {current_user.username}")

            return UserResponse.from_user(user)

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    return router
