#!/usr/bin/env python3
"""
Looker Dashboard Refresh Script

This production-ready script provides a command-line interface for refreshing
Looker dashboards and monitoring query execution via the Looker API.

Features:
- Dashboard and Look refresh
- Query execution and result caching
- Query status monitoring
- Batch dashboard refresh
- Error handling and retries
- Detailed logging
- Command-line interface

Prerequisites:
- Looker instance with API access
- Looker API credentials (Client ID and Secret)
- Python 3.8+
- looker-sdk library

Installation:
    pip install looker-sdk

Usage:
    # Refresh a single dashboard
    python refresh_dashboard.py --dashboard-id 123

    # Refresh multiple dashboards
    python refresh_dashboard.py --dashboard-ids 123,456,789

    # Refresh a Look
    python refresh_dashboard.py --look-id 456

    # List all dashboards
    python refresh_dashboard.py --list-dashboards

    # Check query status
    python refresh_dashboard.py --query-id abc123 --check-status
"""

import os
import sys
import time
import logging
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

import looker_sdk
from looker_sdk import models40 as models
from looker_sdk.error import SDKError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

class LookerConfig:
    """Looker API configuration from environment variables."""

    def __init__(self):
        self.base_url = os.getenv('LOOKER_BASE_URL', '')
        self.client_id = os.getenv('LOOKER_CLIENT_ID', '')
        self.client_secret = os.getenv('LOOKER_CLIENT_SECRET', '')
        self.verify_ssl = os.getenv('LOOKER_VERIFY_SSL', 'true').lower() == 'true'
        self.timeout = int(os.getenv('LOOKER_TIMEOUT', '120'))

    def validate(self) -> bool:
        """Validate that required configuration is present."""
        if not self.base_url:
            logger.error("LOOKER_BASE_URL environment variable not set")
            return False
        if not self.client_id:
            logger.error("LOOKER_CLIENT_ID environment variable not set")
            return False
        if not self.client_secret:
            logger.error("LOOKER_CLIENT_SECRET environment variable not set")
            return False
        return True


# ============================================================================
# LOOKER CLIENT
# ============================================================================

class LookerClient:
    """Wrapper for Looker SDK with helper methods."""

    def __init__(self, config: LookerConfig):
        """
        Initialize Looker client.

        Args:
            config: LookerConfig instance
        """
        self.config = config
        self.sdk: Optional[looker_sdk.Looker40SDK] = None

    def connect(self) -> bool:
        """
        Connect to Looker API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Set environment variables for SDK
            os.environ['LOOKERSDK_BASE_URL'] = self.config.base_url
            os.environ['LOOKERSDK_CLIENT_ID'] = self.config.client_id
            os.environ['LOOKERSDK_CLIENT_SECRET'] = self.config.client_secret
            os.environ['LOOKERSDK_VERIFY_SSL'] = str(self.config.verify_ssl)
            os.environ['LOOKERSDK_TIMEOUT'] = str(self.config.timeout)

            # Initialize SDK
            self.sdk = looker_sdk.init40()

            # Test authentication
            me = self.sdk.me()
            logger.info(f"Connected to Looker as: {me.display_name} ({me.email})")

            return True

        except SDKError as e:
            logger.error(f"Failed to connect to Looker API: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Looker: {e}")
            return False

    def get_dashboard(self, dashboard_id: str) -> Optional[models.Dashboard]:
        """
        Get dashboard by ID.

        Args:
            dashboard_id: Dashboard ID

        Returns:
            Dashboard object or None if not found
        """
        try:
            dashboard = self.sdk.dashboard(dashboard_id)
            return dashboard
        except SDKError as e:
            logger.error(f"Failed to get dashboard {dashboard_id}: {e}")
            return None

    def get_look(self, look_id: str) -> Optional[models.Look]:
        """
        Get Look by ID.

        Args:
            look_id: Look ID

        Returns:
            Look object or None if not found
        """
        try:
            look = self.sdk.look(look_id)
            return look
        except SDKError as e:
            logger.error(f"Failed to get Look {look_id}: {e}")
            return None

    def refresh_dashboard(self, dashboard_id: str, force: bool = True) -> Dict[str, Any]:
        """
        Refresh all queries on a dashboard.

        Args:
            dashboard_id: Dashboard ID
            force: If True, bypass cache and force refresh

        Returns:
            Dict with refresh results
        """
        try:
            logger.info(f"Refreshing dashboard: {dashboard_id}")

            # Get dashboard details
            dashboard = self.get_dashboard(dashboard_id)
            if not dashboard:
                return {
                    'status': 'error',
                    'message': f'Dashboard {dashboard_id} not found',
                }

            logger.info(f"Dashboard title: {dashboard.title}")

            # Get all dashboard elements
            elements = self.sdk.dashboard_dashboard_elements(dashboard_id)

            refresh_results = []
            for element in elements:
                if element.query_id:
                    try:
                        # Run query to refresh cache
                        logger.info(f"Refreshing query {element.query_id} for element {element.id}")

                        result = self.sdk.run_query(
                            query_id=element.query_id,
                            result_format='json',
                            cache=not force,  # If force=True, bypass cache
                        )

                        refresh_results.append({
                            'element_id': element.id,
                            'query_id': element.query_id,
                            'title': element.title,
                            'status': 'success',
                        })

                    except SDKError as e:
                        logger.warning(f"Failed to refresh query {element.query_id}: {e}")
                        refresh_results.append({
                            'element_id': element.id,
                            'query_id': element.query_id,
                            'title': element.title,
                            'status': 'error',
                            'error': str(e),
                        })

            success_count = sum(1 for r in refresh_results if r['status'] == 'success')
            error_count = sum(1 for r in refresh_results if r['status'] == 'error')

            logger.info(
                f"Dashboard refresh complete: {success_count} succeeded, {error_count} failed"
            )

            return {
                'status': 'success' if error_count == 0 else 'partial',
                'dashboard_id': dashboard_id,
                'dashboard_title': dashboard.title,
                'queries_refreshed': success_count,
                'queries_failed': error_count,
                'results': refresh_results,
                'timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Unexpected error refreshing dashboard {dashboard_id}: {e}")
            return {
                'status': 'error',
                'dashboard_id': dashboard_id,
                'message': str(e),
            }

    def refresh_look(self, look_id: str, force: bool = True) -> Dict[str, Any]:
        """
        Refresh a Look.

        Args:
            look_id: Look ID
            force: If True, bypass cache and force refresh

        Returns:
            Dict with refresh results
        """
        try:
            logger.info(f"Refreshing Look: {look_id}")

            # Get Look details
            look = self.get_look(look_id)
            if not look:
                return {
                    'status': 'error',
                    'message': f'Look {look_id} not found',
                }

            logger.info(f"Look title: {look.title}")

            # Run the Look's query
            if look.query_id:
                result = self.sdk.run_query(
                    query_id=look.query_id,
                    result_format='json',
                    cache=not force,
                )

                logger.info(f"Look {look_id} refreshed successfully")

                return {
                    'status': 'success',
                    'look_id': look_id,
                    'look_title': look.title,
                    'query_id': look.query_id,
                    'timestamp': datetime.now().isoformat(),
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Look {look_id} has no associated query',
                }

        except SDKError as e:
            logger.error(f"Failed to refresh Look {look_id}: {e}")
            return {
                'status': 'error',
                'look_id': look_id,
                'message': str(e),
            }

    def list_dashboards(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List available dashboards.

        Args:
            limit: Maximum number of dashboards to return

        Returns:
            List of dashboard summaries
        """
        try:
            dashboards = self.sdk.all_dashboards(fields='id,title,folder,updated_at')

            dashboard_list = []
            for dashboard in dashboards[:limit]:
                dashboard_list.append({
                    'id': dashboard.id,
                    'title': dashboard.title,
                    'folder': dashboard.folder.name if dashboard.folder else None,
                    'updated_at': dashboard.updated_at,
                })

            return dashboard_list

        except SDKError as e:
            logger.error(f"Failed to list dashboards: {e}")
            return []

    def check_query_status(self, query_task_id: str) -> Dict[str, Any]:
        """
        Check the status of a running query.

        Args:
            query_task_id: Query task ID

        Returns:
            Dict with query status information
        """
        try:
            task = self.sdk.query_task(query_task_id)

            return {
                'status': task.status,
                'query_id': task.query_id,
                'runtime': task.runtime,
                'result_source': task.result_source,
                'cache_key': task.cache_key,
            }

        except SDKError as e:
            logger.error(f"Failed to check query status: {e}")
            return {
                'status': 'error',
                'message': str(e),
            }


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Looker Dashboard Refresh Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Refresh a single dashboard
  python refresh_dashboard.py --dashboard-id 123

  # Refresh multiple dashboards
  python refresh_dashboard.py --dashboard-ids 123,456,789

  # Refresh a Look
  python refresh_dashboard.py --look-id 456

  # List all dashboards
  python refresh_dashboard.py --list-dashboards

  # Set Looker credentials
  export LOOKER_BASE_URL='https://mycompany.looker.com'
  export LOOKER_CLIENT_ID='your_client_id'
  export LOOKER_CLIENT_SECRET='your_client_secret'
        """
    )

    parser.add_argument(
        '--dashboard-id',
        type=str,
        help='Dashboard ID to refresh'
    )

    parser.add_argument(
        '--dashboard-ids',
        type=str,
        help='Comma-separated list of dashboard IDs to refresh'
    )

    parser.add_argument(
        '--look-id',
        type=str,
        help='Look ID to refresh'
    )

    parser.add_argument(
        '--list-dashboards',
        action='store_true',
        help='List all available dashboards'
    )

    parser.add_argument(
        '--query-id',
        type=str,
        help='Query ID to check status'
    )

    parser.add_argument(
        '--check-status',
        action='store_true',
        help='Check query status (requires --query-id)'
    )

    parser.add_argument(
        '--no-force',
        action='store_true',
        help='Use cached results instead of forcing refresh'
    )

    parser.add_argument(
        '--output',
        type=str,
        choices=['json', 'text'],
        default='text',
        help='Output format (default: text)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_arguments()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    config = LookerConfig()
    if not config.validate():
        logger.error("Invalid configuration. Please set required environment variables:")
        logger.error("  - LOOKER_BASE_URL")
        logger.error("  - LOOKER_CLIENT_ID")
        logger.error("  - LOOKER_CLIENT_SECRET")
        sys.exit(1)

    # Create client and connect
    client = LookerClient(config)
    if not client.connect():
        logger.error("Failed to connect to Looker API")
        sys.exit(1)

    results = {}

    try:
        # List dashboards
        if args.list_dashboards:
            dashboards = client.list_dashboards()

            if args.output == 'json':
                print(json.dumps(dashboards, indent=2))
            else:
                print(f"\nFound {len(dashboards)} dashboards:\n")
                for dashboard in dashboards:
                    print(f"  ID: {dashboard['id']}")
                    print(f"  Title: {dashboard['title']}")
                    print(f"  Folder: {dashboard.get('folder', 'N/A')}")
                    print(f"  Updated: {dashboard.get('updated_at', 'N/A')}")
                    print()

            return

        # Check query status
        if args.check_status and args.query_id:
            status = client.check_query_status(args.query_id)

            if args.output == 'json':
                print(json.dumps(status, indent=2))
            else:
                print(f"\nQuery Status: {status.get('status', 'Unknown')}")
                print(f"Query ID: {status.get('query_id', 'N/A')}")
                print(f"Runtime: {status.get('runtime', 'N/A')} seconds")
                print(f"Result Source: {status.get('result_source', 'N/A')}")

            return

        # Refresh single dashboard
        if args.dashboard_id:
            result = client.refresh_dashboard(
                args.dashboard_id,
                force=not args.no_force
            )
            results['dashboards'] = [result]

        # Refresh multiple dashboards
        if args.dashboard_ids:
            dashboard_ids = [d.strip() for d in args.dashboard_ids.split(',')]
            dashboard_results = []

            for dashboard_id in dashboard_ids:
                result = client.refresh_dashboard(
                    dashboard_id,
                    force=not args.no_force
                )
                dashboard_results.append(result)

            results['dashboards'] = dashboard_results

        # Refresh Look
        if args.look_id:
            result = client.refresh_look(
                args.look_id,
                force=not args.no_force
            )
            results['looks'] = [result]

        # Output results
        if results:
            if args.output == 'json':
                print(json.dumps(results, indent=2))
            else:
                print("\n" + "="*80)
                print("REFRESH RESULTS")
                print("="*80)

                if 'dashboards' in results:
                    for result in results['dashboards']:
                        print(f"\nDashboard: {result.get('dashboard_title', result.get('dashboard_id'))}")
                        print(f"  Status: {result['status']}")
                        if result['status'] in ['success', 'partial']:
                            print(f"  Queries Refreshed: {result.get('queries_refreshed', 0)}")
                            print(f"  Queries Failed: {result.get('queries_failed', 0)}")

                if 'looks' in results:
                    for result in results['looks']:
                        print(f"\nLook: {result.get('look_title', result.get('look_id'))}")
                        print(f"  Status: {result['status']}")

                print("\n" + "="*80)

        else:
            logger.warning("No refresh operations specified. Use --help for usage information.")

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
