# DataForge AI Platform - Test Suite

Comprehensive integration and unit tests for the DataForge AI Platform.

## Overview

The test suite includes:
- **Integration Tests**: End-to-end tests across multiple components
- **API Tests**: REST API endpoint validation
- **Authentication Tests**: JWT and RBAC functionality
- **Database Tests**: Repository and ORM operations
- **Cache Tests**: Redis and in-memory caching
- **Performance Tests**: Load and concurrency testing

## Quick Start

### Install Dependencies

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Install shared libraries
cd shared-libraries/dataforge-common
pip install -e .
cd ../dataforge-ai-core
pip install -e .
cd ../..
```

### Run All Tests

```bash
# Simple run
pytest tests/

# Or use the test runner script
./scripts/run_tests.sh
```

### Run Specific Test Categories

```bash
# Integration tests only
./scripts/run_tests.sh --integration

# Fast tests only (exclude slow tests)
./scripts/run_tests.sh --fast

# With coverage report
./scripts/run_tests.sh --coverage

# Verbose output
./scripts/run_tests.sh --verbose
```

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── integration/
│   ├── test_auth_integration.py   # Authentication system tests
│   ├── test_api_integration.py    # API endpoint tests
│   └── test_workflows.py          # Cross-accelerator workflows
└── README.md                      # This file
```

## Test Markers

Tests are marked with pytest markers for selective execution:

| Marker | Description | Usage |
|--------|-------------|-------|
| `integration` | Integration tests | `pytest -m integration` |
| `slow` | Slow tests (>1s) | `pytest -m "not slow"` |
| `api` | API endpoint tests | `pytest -m api` |
| `auth` | Authentication tests | `pytest -m auth` |
| `db` | Database tests | `pytest -m db` |
| `cache` | Caching tests | `pytest -m cache` |
| `requires_redis` | Requires Redis | Skip if Redis unavailable |
| `requires_postgres` | Requires PostgreSQL | Skip if PostgreSQL unavailable |
| `requires_kafka` | Requires Kafka | Skip if Kafka unavailable |

### Examples

```bash
# Run only authentication tests
pytest -m auth

# Run integration tests but exclude slow tests
pytest -m "integration and not slow"

# Run all tests except those requiring Redis
pytest -m "not requires_redis"
```

## Fixtures

Common fixtures are defined in `conftest.py`:

### Database Fixtures

- `db_manager`: In-memory SQLite database
- `test_database`: Initialized database with default data
- `user_repo`: User repository
- `role_repo`: Role repository
- `audit_repo`: Audit event repository

### Authentication Fixtures

- `auth_manager`: Authentication manager instance
- `test_user`: Standard test user
- `admin_user`: Admin test user
- `test_tokens`: JWT tokens for test user
- `admin_tokens`: JWT tokens for admin user

### Test Data Fixtures

- `sample_csv_data`: Sample CSV data
- `sample_pii_data`: Sample data with PII
- `temp_dir`: Temporary directory for test files

### API Fixtures

- `governance_client`: Test client for Data Governance API

## Writing Tests

### Example Integration Test

```python
import pytest

@pytest.mark.integration
def test_user_authentication(auth_manager, test_user):
    """Test user authentication flow."""
    # Authenticate user
    authenticated = auth_manager.authenticate_user(
        test_user.username,
        "testpassword"
    )

    assert authenticated is not None
    assert authenticated.username == test_user.username
```

### Example API Test

```python
@pytest.mark.api
def test_login_endpoint(governance_client, test_database):
    """Test login API endpoint."""
    response = governance_client.post(
        "/auth/login",
        json={"username": "admin", "password": "test_admin_password"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
```

### Example Performance Test

```python
@pytest.mark.slow
def test_bulk_operations(user_repo):
    """Test creating many users."""
    for i in range(100):
        user_repo.create(
            user_id=f"user_{i}",
            username=f"user{i}",
            email=f"user{i}@test.com",
            hashed_password="hashed",
        )

    assert user_repo.count() >= 100
```

## Configuration

Test configuration is in `pytest.ini`:

```ini
[pytest]
testpaths = tests
markers =
    integration: Integration tests
    slow: Slow tests
    api: API tests
```

## Environment Variables

Tests use the following environment variables:

```bash
# Set by conftest.py automatically
export TESTING=true
export DATABASE_URL=sqlite:///:memory:
export JWT_SECRET_KEY=test-secret-key-for-testing-only
export ADMIN_PASSWORD=test_admin_password

# Override if needed
export REDIS_HOST=localhost
export REDIS_PORT=6379
export POSTGRES_URL=postgresql://user:pass@localhost:5432/testdb
```

## Coverage Reports

Generate coverage reports with:

```bash
# HTML report
pytest --cov=shared-libraries --cov=accelerators --cov-report=html

# Terminal report
pytest --cov=shared-libraries --cov=accelerators --cov-report=term

# Both
./scripts/run_tests.sh --coverage
```

View HTML coverage report:
```bash
open htmlcov/index.html
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install pytest pytest-cov
          cd shared-libraries/dataforge-common && pip install -e .
          cd ../dataforge-ai-core && pip install -e .

      - name: Run tests
        run: pytest tests/ --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests Fail with Import Errors

Ensure shared libraries are installed:
```bash
cd shared-libraries/dataforge-common && pip install -e .
cd ../dataforge-ai-core && pip install -e .
```

### Database Connection Errors

Tests use in-memory SQLite by default. If you see database errors:
```bash
# Check DATABASE_URL is not set to external database
unset DATABASE_URL

# Or explicitly set to in-memory
export DATABASE_URL=sqlite:///:memory:
```

### Redis Connection Errors

Tests fallback to in-memory cache if Redis is unavailable. To skip Redis tests:
```bash
pytest -m "not requires_redis"
```

### Slow Tests

Run only fast tests:
```bash
pytest -m "not slow"
./scripts/run_tests.sh --fast
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Fixtures**: Use fixtures for common setup
3. **Markers**: Mark tests appropriately
4. **Cleanup**: Tests should clean up after themselves (fixtures handle this)
5. **Documentation**: Document complex test scenarios
6. **Performance**: Mark slow tests with `@pytest.mark.slow`
7. **Database**: Always use in-memory database for tests
8. **Mocking**: Mock external services when appropriate

## Test Coverage Goals

Target coverage by component:

| Component | Target | Current |
|-----------|--------|---------|
| Authentication | 90% | TBD |
| Database | 85% | TBD |
| Caching | 80% | TBD |
| API Endpoints | 85% | TBD |
| Accelerators | 75% | TBD |

## Next Steps

- [ ] Add unit tests for each accelerator
- [ ] Add performance benchmarks
- [ ] Add load testing with Locust
- [ ] Add contract tests for APIs
- [ ] Add security testing
- [ ] Set up CI/CD pipeline
- [ ] Achieve 80%+ code coverage
