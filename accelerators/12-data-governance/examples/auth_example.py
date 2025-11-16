"""Example demonstrating authentication flow with Data Governance API."""

import requests
import pandas as pd
from io import StringIO

# API base URL
BASE_URL = "http://localhost:8012"


def login(username: str, password: str) -> dict:
    """Login and get access token.

    Args:
        username: Username
        password: Password

    Returns:
        Token response with access_token and refresh_token
    """
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()


def get_current_user(access_token: str) -> dict:
    """Get current user information.

    Args:
        access_token: JWT access token

    Returns:
        User information
    """
    response = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    return response.json()


def scan_pii(access_token: str, csv_data: str) -> dict:
    """Scan CSV data for PII.

    Args:
        access_token: JWT access token
        csv_data: CSV data as string

    Returns:
        PII scan report
    """
    files = {"file": ("data.csv", csv_data, "text/csv")}
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.post(
        f"{BASE_URL}/pii/scan",
        files=files,
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


def get_audit_events(access_token: str) -> dict:
    """Get audit events (admin only).

    Args:
        access_token: JWT access token (must be admin)

    Returns:
        Audit events
    """
    response = requests.get(
        f"{BASE_URL}/audit/events",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    return response.json()


def main():
    """Run authentication example."""
    print("=" * 60)
    print("DataForge Data Governance - Authentication Example")
    print("=" * 60)

    # Step 1: Login
    print("\n1. Logging in as admin...")
    token_response = login("admin", "admin123")
    access_token = token_response["access_token"]
    print(f"✓ Logged in successfully")
    print(f"  Access token: {access_token[:20]}...")
    print(f"  Expires in: {token_response['expires_in']} seconds")

    # Step 2: Get current user
    print("\n2. Getting current user information...")
    user = get_current_user(access_token)
    print(f"✓ User: {user['username']}")
    print(f"  Email: {user['email']}")
    print(f"  Roles: {', '.join(user['roles'])}")
    print(f"  Is superuser: {user['is_superuser']}")

    # Step 3: Scan PII
    print("\n3. Scanning data for PII...")
    sample_data = """name,email,phone,age
John Doe,john@example.com,555-123-4567,30
Jane Smith,jane@example.com,555-987-6543,25
Bob Johnson,bob@example.com,555-555-5555,35
"""

    report = scan_pii(access_token, sample_data)
    print(f"✓ Scan complete")
    print(f"  Total rows: {report['total_rows']}")
    print(f"  Total columns: {report['total_columns']}")
    print(f"  PII columns: {', '.join(report['pii_columns'])}")
    print(f"  PII types found:")
    for pii_type, count in report['summary'].items():
        print(f"    - {pii_type}: {count} matches")

    # Step 4: Get audit events (admin only)
    print("\n4. Retrieving audit events (admin only)...")
    events = get_audit_events(access_token)
    print(f"✓ Retrieved {events['total_events']} audit events")
    if events['events']:
        latest = events['events'][-1]
        print(f"  Latest event:")
        print(f"    - Action: {latest['action']}")
        print(f"    - User: {latest['user_id']}")
        print(f"    - Resource: {latest['resource_type']}/{latest['resource_id']}")
        print(f"    - Timestamp: {latest['timestamp']}")

    print("\n" + "=" * 60)
    print("✓ Authentication example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.HTTPError as e:
        print(f"\n✗ Error: {e}")
        if e.response is not None:
            print(f"  Status: {e.response.status_code}")
            print(f"  Detail: {e.response.json()}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
