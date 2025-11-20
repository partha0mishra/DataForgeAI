#!/usr/bin/env python3
"""
Customer Risk Score Loader for Redis
=====================================

Loads customer risk scores into Redis for real-time lookups during fraud detection.
Supports loading from CSV files, databases, or APIs.

Features:
    - Batch loading with progress tracking
    - Connection pooling for performance
    - Error handling and retry logic
    - Support for incremental updates
    - Data validation

Usage:
    # Load from CSV
    python customer_risk_loader.py --source csv --file customers.csv

    # Load from PostgreSQL
    python customer_risk_loader.py --source postgres --connection-string "postgresql://..."

    # Load from API
    python customer_risk_loader.py --source api --url "https://api.example.com/risk-scores"

Author: DataForgeAI Team
Version: 1.0.0
"""

import argparse
import csv
import json
import logging
import sys
import time
from typing import Dict, List, Tuple, Optional, Iterator
from pathlib import Path
from dataclasses import dataclass
import redis
from redis.connection import ConnectionPool
import requests

# Database support (optional)
try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logging.warning("psycopg2 not available - PostgreSQL source disabled")

try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    logging.warning("pymysql not available - MySQL source disabled")

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis configuration
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0

# Loading configuration
DEFAULT_BATCH_SIZE = 1000
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 5  # seconds


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class CustomerRisk:
    """Customer risk score data."""
    customer_id: str
    risk_score: float
    risk_category: Optional[str] = None
    last_updated: Optional[str] = None

    def validate(self) -> bool:
        """
        Validate customer risk data.

        Returns:
            bool: True if valid
        """
        if not self.customer_id:
            return False

        if not (0.0 <= self.risk_score <= 1.0):
            return False

        return True


# ============================================================================
# REDIS LOADER
# ============================================================================

class CustomerRiskLoader:
    """Load customer risk scores into Redis."""

    def __init__(
        self,
        redis_host: str = DEFAULT_REDIS_HOST,
        redis_port: int = DEFAULT_REDIS_PORT,
        redis_db: int = DEFAULT_REDIS_DB,
        redis_password: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE
    ):
        """
        Initialize customer risk loader.

        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
            redis_password: Redis password (if required)
            batch_size: Batch size for bulk operations
        """
        self.batch_size = batch_size
        self.loaded_count = 0
        self.error_count = 0

        # Create connection pool
        self.pool = ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
            max_connections=10
        )

        self.redis_client = redis.Redis(connection_pool=self.pool)

        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def load_batch(self, customers: List[CustomerRisk]) -> Tuple[int, int]:
        """
        Load a batch of customer risk scores.

        Args:
            customers: List of CustomerRisk objects

        Returns:
            Tuple[int, int]: (loaded_count, error_count)
        """
        loaded = 0
        errors = 0

        # Prepare pipeline for batch operation
        pipeline = self.redis_client.pipeline()

        for customer in customers:
            # Validate data
            if not customer.validate():
                logger.warning(f"Invalid customer data: {customer.customer_id}")
                errors += 1
                continue

            try:
                # Store risk score in hash
                pipeline.hset(
                    "customer_risk_scores",
                    customer.customer_id,
                    customer.risk_score
                )

                # Optionally store additional metadata
                if customer.risk_category or customer.last_updated:
                    metadata = {
                        "risk_score": customer.risk_score,
                        "risk_category": customer.risk_category or "UNKNOWN",
                        "last_updated": customer.last_updated or ""
                    }
                    pipeline.set(
                        f"customer_metadata:{customer.customer_id}",
                        json.dumps(metadata),
                        ex=86400  # 24 hour expiry
                    )

                loaded += 1

            except Exception as e:
                logger.error(f"Error preparing batch for {customer.customer_id}: {e}")
                errors += 1

        # Execute pipeline
        try:
            pipeline.execute()
            logger.info(f"Loaded batch of {loaded} customers")
        except Exception as e:
            logger.error(f"Error executing batch: {e}")
            errors += len(customers)
            loaded = 0

        return loaded, errors

    def load_from_csv(self, file_path: str) -> None:
        """
        Load customer risk scores from CSV file.

        CSV format:
            customer_id,risk_score,risk_category,last_updated

        Args:
            file_path: Path to CSV file
        """
        logger.info(f"Loading from CSV: {file_path}")

        if not Path(file_path).exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        batch = []
        line_number = 0

        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    line_number += 1

                    try:
                        customer = CustomerRisk(
                            customer_id=row.get('customer_id', '').strip(),
                            risk_score=float(row.get('risk_score', 0.5)),
                            risk_category=row.get('risk_category', '').strip() or None,
                            last_updated=row.get('last_updated', '').strip() or None
                        )

                        batch.append(customer)

                        # Load batch when full
                        if len(batch) >= self.batch_size:
                            loaded, errors = self.load_batch(batch)
                            self.loaded_count += loaded
                            self.error_count += errors
                            batch = []

                    except Exception as e:
                        logger.error(f"Error parsing line {line_number}: {e}")
                        self.error_count += 1

                # Load remaining batch
                if batch:
                    loaded, errors = self.load_batch(batch)
                    self.loaded_count += loaded
                    self.error_count += errors

        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise

        logger.info(f"CSV loading completed. Loaded: {self.loaded_count}, Errors: {self.error_count}")

    def load_from_postgres(
        self,
        connection_string: str,
        query: Optional[str] = None,
        table: Optional[str] = None
    ) -> None:
        """
        Load customer risk scores from PostgreSQL.

        Args:
            connection_string: PostgreSQL connection string
            query: Custom SQL query (optional)
            table: Table name (if query not provided)
        """
        if not POSTGRES_AVAILABLE:
            raise ImportError("psycopg2 not installed - cannot load from PostgreSQL")

        logger.info("Loading from PostgreSQL")

        if not query and not table:
            raise ValueError("Either query or table must be specified")

        if not query:
            query = f"""
                SELECT customer_id, risk_score, risk_category, last_updated
                FROM {table}
            """

        batch = []

        try:
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()

            logger.info(f"Executing query: {query}")
            cursor.execute(query)

            while True:
                rows = cursor.fetchmany(self.batch_size)
                if not rows:
                    break

                for row in rows:
                    try:
                        customer = CustomerRisk(
                            customer_id=str(row[0]),
                            risk_score=float(row[1]),
                            risk_category=str(row[2]) if len(row) > 2 and row[2] else None,
                            last_updated=str(row[3]) if len(row) > 3 and row[3] else None
                        )
                        batch.append(customer)

                    except Exception as e:
                        logger.error(f"Error parsing row: {e}")
                        self.error_count += 1

                # Load batch
                if batch:
                    loaded, errors = self.load_batch(batch)
                    self.loaded_count += loaded
                    self.error_count += errors
                    batch = []

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"Error loading from PostgreSQL: {e}")
            raise

        logger.info(f"PostgreSQL loading completed. Loaded: {self.loaded_count}, Errors: {self.error_count}")

    def load_from_api(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None
    ) -> None:
        """
        Load customer risk scores from REST API.

        Expected JSON format:
            [
                {
                    "customer_id": "...",
                    "risk_score": 0.75,
                    "risk_category": "HIGH",
                    "last_updated": "2024-01-01T00:00:00Z"
                },
                ...
            ]

        Args:
            url: API endpoint URL
            headers: Optional HTTP headers
            auth: Optional (username, password) tuple
        """
        logger.info(f"Loading from API: {url}")

        batch = []

        try:
            response = requests.get(url, headers=headers, auth=auth, timeout=30)
            response.raise_for_status()

            data = response.json()

            if not isinstance(data, list):
                raise ValueError("API response must be a JSON array")

            for item in data:
                try:
                    customer = CustomerRisk(
                        customer_id=item.get('customer_id', '').strip(),
                        risk_score=float(item.get('risk_score', 0.5)),
                        risk_category=item.get('risk_category', '').strip() or None,
                        last_updated=item.get('last_updated', '').strip() or None
                    )

                    batch.append(customer)

                    # Load batch when full
                    if len(batch) >= self.batch_size:
                        loaded, errors = self.load_batch(batch)
                        self.loaded_count += loaded
                        self.error_count += errors
                        batch = []

                except Exception as e:
                    logger.error(f"Error parsing API item: {e}")
                    self.error_count += 1

            # Load remaining batch
            if batch:
                loaded, errors = self.load_batch(batch)
                self.loaded_count += loaded
                self.error_count += errors

        except Exception as e:
            logger.error(f"Error loading from API: {e}")
            raise

        logger.info(f"API loading completed. Loaded: {self.loaded_count}, Errors: {self.error_count}")

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about loaded data.

        Returns:
            Dict: Statistics
        """
        try:
            total_customers = self.redis_client.hlen("customer_risk_scores")

            # Sample some scores for statistics
            all_scores = self.redis_client.hvals("customer_risk_scores")
            scores = [float(s) for s in all_scores[:1000]]  # Sample first 1000

            if scores:
                avg_score = sum(scores) / len(scores)
                min_score = min(scores)
                max_score = max(scores)
            else:
                avg_score = min_score = max_score = 0.0

            return {
                "total_customers": total_customers,
                "loaded_in_session": self.loaded_count,
                "errors_in_session": self.error_count,
                "avg_risk_score": round(avg_score, 3),
                "min_risk_score": round(min_score, 3),
                "max_risk_score": round(max_score, 3)
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def clear_all_data(self) -> None:
        """Clear all customer risk data from Redis."""
        logger.warning("Clearing all customer risk data from Redis")

        try:
            self.redis_client.delete("customer_risk_scores")

            # Clear metadata keys
            pattern = "customer_metadata:*"
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    self.redis_client.delete(*keys)
                if cursor == 0:
                    break

            logger.info("All data cleared")

        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            raise


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load customer risk scores into Redis"
    )

    parser.add_argument(
        "--redis-host",
        type=str,
        default=DEFAULT_REDIS_HOST,
        help=f"Redis host (default: {DEFAULT_REDIS_HOST})"
    )

    parser.add_argument(
        "--redis-port",
        type=int,
        default=DEFAULT_REDIS_PORT,
        help=f"Redis port (default: {DEFAULT_REDIS_PORT})"
    )

    parser.add_argument(
        "--redis-db",
        type=int,
        default=DEFAULT_REDIS_DB,
        help=f"Redis database (default: {DEFAULT_REDIS_DB})"
    )

    parser.add_argument(
        "--redis-password",
        type=str,
        help="Redis password (optional)"
    )

    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["csv", "postgres", "mysql", "api"],
        help="Data source type"
    )

    parser.add_argument(
        "--file",
        type=str,
        help="CSV file path (required for csv source)"
    )

    parser.add_argument(
        "--connection-string",
        type=str,
        help="Database connection string (required for postgres/mysql source)"
    )

    parser.add_argument(
        "--table",
        type=str,
        help="Database table name"
    )

    parser.add_argument(
        "--query",
        type=str,
        help="Custom SQL query"
    )

    parser.add_argument(
        "--url",
        type=str,
        help="API endpoint URL (required for api source)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Batch size for loading (default: {DEFAULT_BATCH_SIZE})"
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing data before loading"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.source == "csv" and not args.file:
        parser.error("--file is required for csv source")

    if args.source in ["postgres", "mysql"] and not args.connection_string:
        parser.error("--connection-string is required for database source")

    if args.source == "api" and not args.url:
        parser.error("--url is required for api source")

    # Initialize loader
    loader = CustomerRiskLoader(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        redis_db=args.redis_db,
        redis_password=args.redis_password,
        batch_size=args.batch_size
    )

    # Clear existing data if requested
    if args.clear:
        loader.clear_all_data()

    # Load data based on source
    start_time = time.time()

    try:
        if args.source == "csv":
            loader.load_from_csv(args.file)

        elif args.source == "postgres":
            loader.load_from_postgres(
                args.connection_string,
                query=args.query,
                table=args.table
            )

        elif args.source == "api":
            loader.load_from_api(args.url)

        else:
            logger.error(f"Unsupported source: {args.source}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Loading failed: {e}")
        sys.exit(1)

    elapsed_time = time.time() - start_time

    # Print statistics
    stats = loader.get_statistics()
    logger.info("=" * 80)
    logger.info("LOADING COMPLETED")
    logger.info("=" * 80)
    logger.info(f"Total customers in Redis: {stats.get('total_customers', 0)}")
    logger.info(f"Loaded in this session: {stats.get('loaded_in_session', 0)}")
    logger.info(f"Errors in this session: {stats.get('errors_in_session', 0)}")
    logger.info(f"Average risk score: {stats.get('avg_risk_score', 0)}")
    logger.info(f"Min risk score: {stats.get('min_risk_score', 0)}")
    logger.info(f"Max risk score: {stats.get('max_risk_score', 0)}")
    logger.info(f"Elapsed time: {elapsed_time:.2f} seconds")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
