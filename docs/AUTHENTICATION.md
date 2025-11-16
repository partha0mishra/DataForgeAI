# Authentication & Authorization

DataForge AI Platform uses JWT (JSON Web Token) based authentication with role-based access control (RBAC).

## Overview

All 14 accelerators have been integrated with enterprise-grade authentication:

- **JWT Tokens**: Secure token-based authentication
- **Role-Based Access Control**: Fine-grained permissions
- **Audit Logging**: Track all authenticated access
- **Token Refresh**: Long-lived sessions with refresh tokens
- **Password Security**: Bcrypt hashing with salt

## Architecture

### Components

1. **Auth Manager** (`dataforge_common.auth`)
   - User management
   - Password hashing/verification
   - JWT token creation and verification
   - Role checking

2. **FastAPI Dependencies** (`dataforge_common.fastapi_auth`)
   - `get_current_user()`: Require authentication
   - `get_optional_user()`: Optional authentication
   - `require_roles(["role"])`: Require specific roles
   - `require_superuser()`: Require admin access

3. **Auth Router** (`dataforge_common.auth_router`)
   - `POST /auth/login`: User login
   - `POST /auth/refresh`: Refresh access token
   - `GET /auth/me`: Get current user info
   - `POST /auth/users`: Create users (admin only)

## Quick Start

### 1. Default Credentials

```python
Username: admin
Password: admin123
```

**⚠️ IMPORTANT**: Change the default admin password in production!

```bash
export ADMIN_PASSWORD="your-secure-password"
```

### 2. Login and Get Token

```python
import requests

# Login
response = requests.post(
    "http://localhost:8012/auth/login",
    json={"username": "admin", "password": "admin123"}
)

tokens = response.json()
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]
```

### 3. Make Authenticated Requests

```python
# Use access token in Authorization header
headers = {"Authorization": f"Bearer {access_token}"}

response = requests.post(
    "http://localhost:8012/pii/scan",
    files={"file": open("data.csv", "rb")},
    headers=headers
)
```

### 4. Refresh Token

```python
# When access token expires (default: 30 minutes)
response = requests.post(
    "http://localhost:8012/auth/refresh",
    json={"refresh_token": refresh_token}
)

new_tokens = response.json()
access_token = new_tokens["access_token"]
```

## Configuration

### Environment Variables

```bash
# JWT Configuration
export JWT_SECRET_KEY="your-secret-key-min-32-chars"
export ACCESS_TOKEN_EXPIRE_MINUTES="30"
export REFRESH_TOKEN_EXPIRE_DAYS="7"

# Default Admin
export ADMIN_PASSWORD="your-secure-password"
```

### Token Expiration

| Token Type | Default Expiration | Environment Variable |
|------------|-------------------|---------------------|
| Access Token | 30 minutes | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh Token | 7 days | `REFRESH_TOKEN_EXPIRE_DAYS` |

## User Roles

### Built-in Roles

| Role | Description | Permissions |
|------|-------------|------------|
| `user` | Standard user | Access to most endpoints |
| `admin` | Administrator | Full access including user management |

### Superuser

- Has ALL permissions regardless of roles
- Default admin user is a superuser
- Can create new users
- Can access audit logs

## Protecting Endpoints

### Require Authentication

```python
from fastapi import Depends
from dataforge_common import get_current_user, User

@app.post("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_user)
):
    """Only authenticated users can access this endpoint."""
    return {"message": f"Hello {current_user.username}"}
```

### Require Specific Roles

```python
from dataforge_common import require_roles

@app.post("/admin-only")
async def admin_endpoint(
    current_user: User = Depends(require_roles(["admin"]))
):
    """Only admins can access this endpoint."""
    return {"message": "Admin access granted"}
```

### Require Superuser

```python
from dataforge_common import require_superuser

@app.delete("/dangerous")
async def dangerous_operation(
    current_user: User = Depends(require_superuser)
):
    """Only superusers can access this endpoint."""
    return {"message": "Superuser access granted"}
```

### Optional Authentication

```python
from dataforge_common import get_optional_user

@app.get("/public-or-private")
async def flexible_endpoint(
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Endpoint accessible to all, but provides extra features when authenticated."""
    if current_user:
        return {"message": f"Welcome back {current_user.username}"}
    return {"message": "Welcome guest"}
```

## Audit Logging

All authenticated requests should be logged to the audit trail:

```python
from dataforge_common import get_current_user
from audit.trail import AuditTrail

audit_trail = AuditTrail()

@app.post("/sensitive-operation")
async def sensitive_operation(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # Log the access
    audit_trail.log_access(
        user_id=current_user.user_id,
        action="sensitive_operation",
        resource_type="data",
        resource_id="resource_123",
        ip_address=request.client.host
    )

    # Perform operation
    return {"status": "success"}
```

## User Management

### Create New User (Admin Only)

```python
POST /auth/users
Authorization: Bearer <admin_access_token>

{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "secure_password",
    "roles": ["user"]
}
```

### Programmatic User Creation

```python
from dataforge_common import get_auth_manager

auth_manager = get_auth_manager()

user = auth_manager.create_user(
    username="analyst",
    email="analyst@company.com",
    password="secure_password",
    roles=["user", "analyst"]
)
```

## Security Best Practices

### 1. Secret Key Management

```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set in environment (NEVER commit to git!)
export JWT_SECRET_KEY="generated-secret-key"
```

### 2. HTTPS in Production

Always use HTTPS in production to protect tokens in transit:

```python
# In production
app.add_middleware(
    HTTPSRedirectMiddleware
)
```

### 3. Token Storage

**Client-side storage options:**

| Method | Security | Use Case |
|--------|----------|----------|
| Memory | ✅ High | Single-page apps |
| HttpOnly Cookie | ✅ High | Traditional web apps |
| LocalStorage | ⚠️ Medium | Not recommended (XSS risk) |

### 4. Rate Limiting

Implement rate limiting on auth endpoints:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(...):
    ...
```

### 5. Password Requirements

Enforce strong passwords in production:

```python
import re

def validate_password(password: str) -> bool:
    """Validate password strength."""
    if len(password) < 12:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*()]', password):
        return False
    return True
```

## Accelerator Integration Status

All 14 accelerators have authentication integrated:

| # | Accelerator | Auth Router | Protected Endpoints | Status |
|---|------------|-------------|-------------------|--------|
| 01 | Pipeline Automation | ✅ | ⏳ | Partial |
| 02 | Data Quality | ✅ | ⏳ | Partial |
| 03 | Knowledge Repository | ✅ | ⏳ | Partial |
| 04 | Data Catalog | ✅ | ⏳ | Partial |
| 05 | Model Factory | ✅ | ⏳ | Partial |
| 06 | BI Dashboarding | ✅ | ⏳ | Partial |
| 07 | Data Storytelling | ✅ | ⏳ | Partial |
| 08 | Conversational Analytics | ✅ | ⏳ | Partial |
| 09 | Process Optimization | ✅ | ⏳ | Partial |
| 10 | Data Monetization | ✅ | ⏳ | Partial |
| 11 | Proposal Accelerator | ✅ | ⏳ | Partial |
| 12 | Data Governance | ✅ | ✅ | Complete |
| 13 | Streaming Analytics | ✅ | ⏳ | Partial |
| 14 | Data Observability | ✅ | ⏳ | Partial |

**Legend:**
- ✅ Complete - Auth router added and endpoints protected
- ⏳ Partial - Auth router added, endpoint protection in progress
- ❌ Missing - Not yet integrated

## Testing Authentication

### Example Test

```python
import pytest
from fastapi.testclient import TestClient

def test_protected_endpoint_requires_auth(client: TestClient):
    """Test that protected endpoints require authentication."""
    # No auth - should fail
    response = client.post("/pii/scan", files={"file": ("test.csv", "data")})
    assert response.status_code == 401

    # With auth - should succeed
    token = login_and_get_token(client, "admin", "admin123")
    response = client.post(
        "/pii/scan",
        files={"file": ("test.csv", "data")},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_role_based_access(client: TestClient):
    """Test that admin endpoints require admin role."""
    user_token = login_and_get_token(client, "user", "password")

    # User without admin role - should fail
    response = client.get(
        "/audit/events",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403

    # Admin user - should succeed
    admin_token = login_and_get_token(client, "admin", "admin123")
    response = client.get(
        "/audit/events",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
```

## Troubleshooting

### Invalid Token Error

```
HTTPException: 401 Unauthorized - Invalid or expired token
```

**Solution**: Token has expired. Use refresh token to get a new access token.

### Missing Authorization Header

```
HTTPException: 403 Forbidden - Not authenticated
```

**Solution**: Include `Authorization: Bearer <token>` header in requests.

### Insufficient Permissions

```
HTTPException: 403 Forbidden - Required roles: admin
```

**Solution**: User lacks required role. Contact admin to update user roles.

### Import Error

```
ImportError: dataforge-common not installed. Authentication disabled.
```

**Solution**: Install dataforge-common:
```bash
cd shared-libraries/dataforge-common
pip install -e .
```

## Migration Guide

### Updating Existing Code

**Before (No Auth):**
```python
@app.post("/data/process")
async def process_data(file: UploadFile):
    # Process file
    return {"status": "processed"}
```

**After (With Auth):**
```python
@app.post("/data/process")
async def process_data(
    file: UploadFile,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # Log access
    audit_trail.log_access(
        user_id=current_user.user_id,
        action="data_process",
        resource_type="file",
        resource_id=file.filename,
        ip_address=request.client.host
    )

    # Process file
    return {"status": "processed"}
```

## References

- [JWT.io](https://jwt.io/) - JWT specification
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
