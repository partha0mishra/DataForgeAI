"""Load tests for DataForge AI Platform using Locust."""

import json
import random
from io import BytesIO
from locust import HttpUser, task, between, events
from datetime import datetime


class DataForgeUser(HttpUser):
    """Base user for DataForge load tests."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = "http://localhost:8012"  # Data Governance API

    def on_start(self):
        """Login and get token on user start."""
        self.login()

    def login(self):
        """Login and store token."""
        response = self.client.post(
            "/auth/login",
            json={
                "username": "admin",
                "password": "admin123",
            },
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def health_check(self):
        """Test health check endpoint."""
        self.client.get("/health")

    @task(1)
    def get_current_user(self):
        """Test getting current user info."""
        if self.token:
            self.client.get("/auth/me", headers=self.headers)

    @task(2)
    def scan_pii(self):
        """Test PII scanning."""
        if not self.token:
            return

        # Generate sample CSV data
        csv_data = """name,email,phone
John Doe,john@example.com,555-123-4567
Jane Smith,jane@example.com,555-987-6543"""

        files = {"file": ("test.csv", csv_data, "text/csv")}

        self.client.post(
            "/pii/scan",
            files=files,
            headers=self.headers,
        )

    @task(1)
    def mask_pii(self):
        """Test PII masking."""
        if not self.token:
            return

        csv_data = """email,ssn
test@example.com,123-45-6789"""

        files = {"file": ("test.csv", csv_data, "text/csv")}

        self.client.post(
            "/pii/mask",
            files=files,
            params={"strategy": "redact"},
            headers=self.headers,
        )

    @task(1)
    def classify_data(self):
        """Test data classification."""
        if not self.token:
            return

        csv_data = """name,age,department
John,30,Engineering
Jane,25,Marketing"""

        files = {"file": ("test.csv", csv_data, "text/csv")}

        self.client.post(
            "/classify",
            files=files,
            headers=self.headers,
        )


class AuthenticationLoadTest(HttpUser):
    """Load test for authentication endpoints."""

    wait_time = between(0.5, 2)
    host = "http://localhost:8012"

    @task(10)
    def login(self):
        """Test login endpoint."""
        self.client.post(
            "/auth/login",
            json={
                "username": "admin",
                "password": "admin123",
            },
        )

    @task(5)
    def login_with_invalid_credentials(self):
        """Test login with invalid credentials."""
        self.client.post(
            "/auth/login",
            json={
                "username": "admin",
                "password": "wrong_password",
            },
        )

    @task(3)
    def refresh_token(self):
        """Test token refresh."""
        # Login first
        response = self.client.post(
            "/auth/login",
            json={
                "username": "admin",
                "password": "admin123",
            },
        )

        if response.status_code == 200:
            refresh_token = response.json()["refresh_token"]

            # Refresh token
            self.client.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token},
            )


class StreamingLoadTest(HttpUser):
    """Load test for streaming analytics."""

    wait_time = between(0.1, 0.5)  # Fast ingestion
    host = "http://localhost:8013"

    @task(10)
    def ingest_event(self):
        """Test stream ingestion."""
        self.client.post(
            "/stream/ingest",
            json={
                "key": f"sensor_{random.randint(1, 10)}",
                "value": random.uniform(0, 100),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    @task(2)
    def get_recent_events(self):
        """Test retrieving recent events."""
        self.client.get("/stream/recent", params={"limit": 50})

    @task(1)
    def get_current_window(self):
        """Test window statistics."""
        self.client.get("/windows/current")


# Statistics tracking
stats = {
    "total_requests": 0,
    "failed_requests": 0,
    "total_response_time": 0,
}


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track request statistics."""
    stats["total_requests"] += 1
    stats["total_response_time"] += response_time

    if exception:
        stats["failed_requests"] += 1


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary statistics when test stops."""
    print("\n" + "=" * 70)
    print("Load Test Summary")
    print("=" * 70)
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Failed Requests: {stats['failed_requests']}")

    if stats["total_requests"] > 0:
        avg_response_time = stats["total_response_time"] / stats["total_requests"]
        print(f"Average Response Time: {avg_response_time:.2f} ms")

        failure_rate = (stats["failed_requests"] / stats["total_requests"]) * 100
        print(f"Failure Rate: {failure_rate:.2f}%")

    print("=" * 70)


# Example run configurations (use with locust CLI)
if __name__ == "__main__":
    print("Load Test Configurations:")
    print("")
    print("1. Full Platform Load Test:")
    print("   locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m")
    print("")
    print("2. Authentication Load Test:")
    print("   locust -f locustfile.py AuthenticationLoadTest --users 50 --spawn-rate 5")
    print("")
    print("3. Streaming Load Test:")
    print("   locust -f locustfile.py StreamingLoadTest --users 200 --spawn-rate 20")
    print("")
    print("4. Data Governance Load Test:")
    print("   locust -f locustfile.py DataForgeUser --users 30 --spawn-rate 5")
    print("")
    print("Run with web UI:")
    print("   locust -f locustfile.py")
    print("   Then open http://localhost:8089")
