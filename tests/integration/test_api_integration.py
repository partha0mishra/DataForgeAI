"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO
import sys
from pathlib import Path

# Add accelerator paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "accelerators/12-data-governance/src"))


@pytest.fixture
def governance_client():
    """Create test client for Data Governance API."""
    from api.main import app
    return TestClient(app)


@pytest.mark.integration
class TestAuthenticationAPI:
    """Test authentication API endpoints."""

    def test_health_check(self, governance_client):
        """Test health check endpoint (no auth required)."""
        response = governance_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_login_success(self, governance_client, test_database):
        """Test successful login."""
        response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_invalid_credentials(self, governance_client, test_database):
        """Test login with invalid credentials."""
        response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "wrong_password"},
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_nonexistent_user(self, governance_client, test_database):
        """Test login with non-existent user."""
        response = governance_client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "password"},
        )

        assert response.status_code == 401

    def test_get_current_user(self, governance_client, test_database):
        """Test getting current user info."""
        # Login first
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = governance_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["is_superuser"] is True
        assert "admin" in data["roles"]

    def test_get_current_user_no_token(self, governance_client):
        """Test accessing protected endpoint without token."""
        response = governance_client.get("/auth/me")
        assert response.status_code == 403

    def test_get_current_user_invalid_token(self, governance_client):
        """Test accessing protected endpoint with invalid token."""
        response = governance_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    def test_token_refresh(self, governance_client, test_database):
        """Test token refresh flow."""
        # Login
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        refresh_response = governance_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_create_user_as_admin(self, governance_client, test_database):
        """Test creating user as admin."""
        # Login as admin
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        token = login_response.json()["access_token"]

        # Create new user
        response = governance_client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "secure_password",
                "roles": ["user"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@test.com"
        assert "user" in data["roles"]


@pytest.mark.integration
class TestDataGovernanceAPI:
    """Test Data Governance API endpoints."""

    def test_pii_scan_with_auth(self, governance_client, test_database, sample_pii_data):
        """Test PII scanning with authentication."""
        # Login
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        token = login_response.json()["access_token"]

        # Scan PII
        files = {"file": ("test.csv", sample_pii_data, "text/csv")}
        response = governance_client.post(
            "/pii/scan",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_rows" in data
        assert "pii_columns" in data
        assert len(data["pii_columns"]) > 0

    def test_pii_scan_without_auth(self, governance_client, sample_pii_data):
        """Test PII scanning without authentication fails."""
        files = {"file": ("test.csv", sample_pii_data, "text/csv")}
        response = governance_client.post("/pii/scan", files=files)

        # Should require authentication
        assert response.status_code == 403

    def test_pii_mask_with_auth(self, governance_client, test_database, sample_pii_data):
        """Test PII masking with authentication."""
        # Login
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        token = login_response.json()["access_token"]

        # Mask PII
        files = {"file": ("test.csv", sample_pii_data, "text/csv")}
        response = governance_client.post(
            "/pii/mask",
            files=files,
            params={"strategy": "redact"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "PII masked successfully"
        assert data["strategy"] == "redact"

    def test_data_classification(self, governance_client, test_database, sample_csv_data):
        """Test data classification."""
        # Login
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        token = login_response.json()["access_token"]

        # Classify data
        files = {"file": ("test.csv", sample_csv_data, "text/csv")}
        response = governance_client.post(
            "/classify",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "classifications" in data
        assert len(data["classifications"]) > 0

    def test_compliance_check(self, governance_client, test_database, sample_pii_data):
        """Test GDPR compliance checking."""
        # Login
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        token = login_response.json()["access_token"]

        # Check compliance
        files = {"file": ("test.csv", sample_pii_data, "text/csv")}
        response = governance_client.post(
            "/compliance/check",
            files=files,
            params={
                "has_consent": False,
                "retention_days": 365,
                "data_age_days": 400,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "compliant" in data
        assert "violations" in data

    def test_audit_log_creation(self, governance_client, test_database):
        """Test creating audit log entry."""
        # Login
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        token = login_response.json()["access_token"]

        # Log audit event
        response = governance_client.post(
            "/audit/log",
            params={
                "action": "test_action",
                "resource_type": "test_resource",
                "resource_id": "test_123",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert "timestamp" in data

    def test_audit_events_retrieval_admin_only(self, governance_client, test_database):
        """Test that audit events require admin role."""
        # Login as admin
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        token = login_response.json()["access_token"]

        # Should succeed for admin
        response = governance_client.get(
            "/audit/events",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "events" in data


@pytest.mark.integration
class TestCrossAcceleratorWorkflow:
    """Test workflows across multiple accelerators."""

    def test_end_to_end_data_governance_workflow(
        self, governance_client, test_database, sample_pii_data
    ):
        """Test complete data governance workflow."""
        # Step 1: Login
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Step 2: Scan for PII
        files = {"file": ("data.csv", sample_pii_data, "text/csv")}
        scan_response = governance_client.post(
            "/pii/scan",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert scan_response.status_code == 200
        pii_columns = scan_response.json()["pii_columns"]

        # Step 3: Classify data
        files = {"file": ("data.csv", sample_pii_data, "text/csv")}
        classify_response = governance_client.post(
            "/classify",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert classify_response.status_code == 200

        # Step 4: Check compliance
        files = {"file": ("data.csv", sample_pii_data, "text/csv")}
        compliance_response = governance_client.post(
            "/compliance/check",
            files=files,
            params={"has_consent": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert compliance_response.status_code == 200

        # Step 5: Mask PII if violations found
        if not compliance_response.json()["compliant"]:
            files = {"file": ("data.csv", sample_pii_data, "text/csv")}
            mask_response = governance_client.post(
                "/pii/mask",
                files=files,
                params={"strategy": "redact"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert mask_response.status_code == 200

        # Step 6: Check audit trail
        audit_response = governance_client.get(
            "/audit/events",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert audit_response.status_code == 200
        assert audit_response.json()["total_events"] > 0


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Performance integration tests."""

    def test_concurrent_authentication(self, governance_client, test_database):
        """Test concurrent authentication requests."""
        import concurrent.futures

        def login_request():
            response = governance_client.post(
                "/auth/login",
                json={"username": "admin", "password": "test_admin_password"},
            )
            return response.status_code == 200

        # Run 10 concurrent login requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(login_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(results)
        assert len(results) == 10

    def test_bulk_user_creation(self, governance_client, test_database):
        """Test creating multiple users."""
        # Login as admin
        login_response = governance_client.post(
            "/auth/login",
            json={"username": "admin", "password": "test_admin_password"},
        )
        token = login_response.json()["access_token"]

        # Create 20 users
        created_users = []
        for i in range(20):
            response = governance_client.post(
                "/auth/users",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "username": f"bulkuser{i}",
                    "email": f"bulkuser{i}@test.com",
                    "password": "password123",
                    "roles": ["user"],
                },
            )
            if response.status_code == 201:
                created_users.append(response.json())

        assert len(created_users) == 20
