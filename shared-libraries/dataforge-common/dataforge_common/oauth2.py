"""OAuth2 integration for DataForge AI with Auth0 and Keycloak support.

This module provides OAuth2/OIDC authentication with support for popular
identity providers like Auth0, Keycloak, Okta, and Azure AD.
"""

import os
import json
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

try:
    from fastapi import HTTPException, Security, status
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2AuthorizationCodeBearer
    from jose import jwt, JWTError, jwk
    from jose.utils import base64url_decode
except ImportError:
    raise ImportError(
        "OAuth2 requires additional dependencies. "
        "Install with: pip install fastapi python-jose[cryptography] httpx"
    )

from .logging import get_logger
from .cache import get_cache
from .settings import get_settings

logger = get_logger(__name__)


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""
    AUTH0 = "auth0"
    KEYCLOAK = "keycloak"
    OKTA = "okta"
    AZURE_AD = "azure_ad"
    GOOGLE = "google"
    CUSTOM = "custom"


@dataclass
class OAuthConfig:
    """OAuth provider configuration."""
    provider: OAuthProvider
    domain: str
    client_id: str
    client_secret: Optional[str] = None
    audience: Optional[str] = None
    issuer: Optional[str] = None
    jwks_uri: Optional[str] = None
    algorithm: str = "RS256"
    cache_jwks: bool = True
    jwks_ttl: int = 3600  # 1 hour


class JWKSClient:
    """Client for fetching and caching JWKS (JSON Web Key Set)."""

    def __init__(self, jwks_uri: str, cache_ttl: int = 3600):
        """Initialize JWKS client.

        Args:
            jwks_uri: URI to fetch JWKS from
            cache_ttl: Cache TTL in seconds
        """
        self.jwks_uri = jwks_uri
        self.cache_ttl = cache_ttl
        self.cache = get_cache()

    async def get_signing_key(self, kid: str) -> Dict[str, Any]:
        """Get signing key by key ID.

        Args:
            kid: Key ID from JWT header

        Returns:
            Signing key as dictionary

        Raises:
            HTTPException: If key not found
        """
        # Try cache first
        cache_key = f"jwks:key:{kid}"
        cached_key = self.cache.get(cache_key)
        if cached_key:
            logger.debug(f"JWKS key {kid} found in cache")
            return json.loads(cached_key)

        # Fetch JWKS
        jwks = await self._fetch_jwks()

        # Find key by kid
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                # Cache the key
                self.cache.set(cache_key, json.dumps(key), ttl=self.cache_ttl)
                logger.info(f"JWKS key {kid} fetched and cached")
                return key

        logger.error(f"JWKS key {kid} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unable to find signing key with kid: {kid}",
        )

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from provider.

        Returns:
            JWKS dictionary
        """
        # Try cache first
        cache_key = "jwks:full"
        cached_jwks = self.cache.get(cache_key)
        if cached_jwks:
            logger.debug("JWKS found in cache")
            return json.loads(cached_jwks)

        # Fetch from provider
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri, timeout=10.0)
                response.raise_for_status()
                jwks = response.json()

                # Cache JWKS
                self.cache.set(cache_key, json.dumps(jwks), ttl=self.cache_ttl)
                logger.info(f"JWKS fetched from {self.jwks_uri}")

                return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch signing keys from identity provider",
            )


class OAuth2Manager:
    """Manage OAuth2/OIDC authentication."""

    def __init__(self, config: OAuthConfig):
        """Initialize OAuth2 manager.

        Args:
            config: OAuth provider configuration
        """
        self.config = config
        self._setup_provider()

        # Initialize JWKS client for RS256 tokens
        if config.algorithm.startswith("RS") and config.jwks_uri:
            self.jwks_client = JWKSClient(config.jwks_uri, config.jwks_ttl)
        else:
            self.jwks_client = None

    def _setup_provider(self):
        """Setup provider-specific configuration."""
        if self.config.provider == OAuthProvider.AUTH0:
            self.config.issuer = self.config.issuer or f"https://{self.config.domain}/"
            self.config.jwks_uri = self.config.jwks_uri or f"https://{self.config.domain}/.well-known/jwks.json"

        elif self.config.provider == OAuthProvider.KEYCLOAK:
            # Keycloak URL format: https://{domain}/realms/{realm}
            self.config.issuer = self.config.issuer or f"{self.config.domain}"
            self.config.jwks_uri = self.config.jwks_uri or f"{self.config.domain}/protocol/openid-connect/certs"

        elif self.config.provider == OAuthProvider.OKTA:
            self.config.issuer = self.config.issuer or f"https://{self.config.domain}"
            self.config.jwks_uri = self.config.jwks_uri or f"https://{self.config.domain}/oauth2/v1/keys"

        elif self.config.provider == OAuthProvider.AZURE_AD:
            # Azure AD URL format: https://login.microsoftonline.com/{tenant}/v2.0
            self.config.issuer = self.config.issuer or f"https://login.microsoftonline.com/{self.config.domain}/v2.0"
            self.config.jwks_uri = self.config.jwks_uri or \
                f"https://login.microsoftonline.com/{self.config.domain}/discovery/v2.0/keys"

        elif self.config.provider == OAuthProvider.GOOGLE:
            self.config.issuer = self.config.issuer or "https://accounts.google.com"
            self.config.jwks_uri = self.config.jwks_uri or "https://www.googleapis.com/oauth2/v3/certs"

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode OAuth2/OIDC token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if self.config.algorithm.startswith("RS"):
                # RS256/RS384/RS512 - Get signing key from JWKS
                if not self.jwks_client or not kid:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token header",
                    )

                # Get signing key
                signing_key = await self.jwks_client.get_signing_key(kid)

                # Convert JWK to PEM format
                public_key = jwk.construct(signing_key).to_pem()

                # Verify and decode token
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=[self.config.algorithm],
                    audience=self.config.audience,
                    issuer=self.config.issuer,
                )

            else:
                # HS256 - Use client secret
                if not self.config.client_secret:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Client secret not configured for HS256",
                    )

                payload = jwt.decode(
                    token,
                    self.config.client_secret,
                    algorithms=[self.config.algorithm],
                    audience=self.config.audience,
                    issuer=self.config.issuer,
                )

            # Additional validation
            self._validate_payload(payload)

            logger.info(f"Token verified for subject: {payload.get('sub')}")
            return payload

        except JWTError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _validate_payload(self, payload: Dict[str, Any]):
        """Validate token payload.

        Args:
            payload: Decoded token payload

        Raises:
            HTTPException: If validation fails
        """
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )

        # Check not before
        nbf = payload.get("nbf")
        if nbf and datetime.fromtimestamp(nbf) > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not yet valid",
            )

        # Check required claims
        required_claims = ["sub"]
        for claim in required_claims:
            if claim not in payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Missing required claim: {claim}",
                )

    def extract_roles(self, payload: Dict[str, Any]) -> List[str]:
        """Extract roles from token payload.

        Different providers store roles in different places:
        - Auth0: permissions array or custom namespace
        - Keycloak: realm_access.roles or resource_access
        - Azure AD: roles array
        - Custom: configurable claim

        Args:
            payload: Decoded token payload

        Returns:
            List of role names
        """
        roles = []

        # Try common locations
        if self.config.provider == OAuthProvider.AUTH0:
            # Auth0 can use permissions or custom claim
            roles = payload.get("permissions", [])
            if not roles:
                # Check custom namespace (e.g., https://myapp.com/roles)
                for key, value in payload.items():
                    if "roles" in key and isinstance(value, list):
                        roles = value
                        break

        elif self.config.provider == OAuthProvider.KEYCLOAK:
            # Keycloak realm roles
            realm_access = payload.get("realm_access", {})
            roles = realm_access.get("roles", [])

            # Add resource/client roles
            resource_access = payload.get("resource_access", {})
            for client, access in resource_access.items():
                roles.extend(access.get("roles", []))

        elif self.config.provider == OAuthProvider.AZURE_AD:
            # Azure AD roles claim
            roles = payload.get("roles", [])

        else:
            # Generic - check common claim names
            roles = (
                payload.get("roles", []) or
                payload.get("permissions", []) or
                payload.get("groups", [])
            )

        return roles if isinstance(roles, list) else []


# FastAPI Security Dependency
security = HTTPBearer()


def create_oauth2_dependency(oauth_manager: OAuth2Manager):
    """Create FastAPI dependency for OAuth2 authentication.

    Args:
        oauth_manager: Configured OAuth2 manager

    Returns:
        FastAPI dependency function
    """
    async def verify_oauth2_token(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict[str, Any]:
        """Verify OAuth2 token and return payload.

        Args:
            credentials: HTTP credentials from Authorization header

        Returns:
            Token payload with user info and roles
        """
        token = credentials.credentials
        payload = await oauth_manager.verify_token(token)

        # Extract roles
        roles = oauth_manager.extract_roles(payload)
        payload["roles"] = roles

        return payload

    return verify_oauth2_token


def create_role_dependency(required_roles: List[str]):
    """Create FastAPI dependency for role-based access control.

    Args:
        required_roles: List of required role names

    Returns:
        FastAPI dependency function
    """
    def check_roles(token_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Check if user has required roles.

        Args:
            token_payload: Decoded token payload with roles

        Returns:
            Token payload if authorized

        Raises:
            HTTPException: If user doesn't have required roles
        """
        user_roles = token_payload.get("roles", [])

        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            logger.warning(
                f"Access denied: User {token_payload.get('sub')} "
                f"requires roles {required_roles}, has {user_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}",
            )

        return token_payload

    return check_roles


# Helper function to initialize OAuth2 from environment
def init_oauth2_from_env() -> Optional[OAuth2Manager]:
    """Initialize OAuth2 manager from environment variables.

    Environment variables:
        OAUTH2_PROVIDER: Provider name (auth0, keycloak, etc.)
        OAUTH2_DOMAIN: Provider domain
        OAUTH2_CLIENT_ID: OAuth client ID
        OAUTH2_CLIENT_SECRET: OAuth client secret (optional)
        OAUTH2_AUDIENCE: Expected audience (optional)
        OAUTH2_ISSUER: Token issuer URL (optional)
        OAUTH2_JWKS_URI: JWKS endpoint (optional)

    Returns:
        Configured OAuth2 manager or None if not configured
    """
    provider_str = os.getenv("OAUTH2_PROVIDER")
    if not provider_str:
        logger.info("OAuth2 not configured (OAUTH2_PROVIDER not set)")
        return None

    try:
        provider = OAuthProvider(provider_str.lower())
    except ValueError:
        logger.error(f"Invalid OAuth2 provider: {provider_str}")
        return None

    domain = os.getenv("OAUTH2_DOMAIN")
    client_id = os.getenv("OAUTH2_CLIENT_ID")

    if not domain or not client_id:
        logger.error("OAuth2 configuration incomplete (missing OAUTH2_DOMAIN or OAUTH2_CLIENT_ID)")
        return None

    config = OAuthConfig(
        provider=provider,
        domain=domain,
        client_id=client_id,
        client_secret=os.getenv("OAUTH2_CLIENT_SECRET"),
        audience=os.getenv("OAUTH2_AUDIENCE"),
        issuer=os.getenv("OAUTH2_ISSUER"),
        jwks_uri=os.getenv("OAUTH2_JWKS_URI"),
        algorithm=os.getenv("OAUTH2_ALGORITHM", "RS256"),
    )

    manager = OAuth2Manager(config)
    logger.info(f"OAuth2 initialized with provider: {provider}")

    return manager
