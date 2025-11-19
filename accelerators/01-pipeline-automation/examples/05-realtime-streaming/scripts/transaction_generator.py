#!/usr/bin/env python3
"""
Transaction Generator for Kinesis Streaming
============================================

Generates realistic transaction data with suspicious patterns for fraud detection testing.
Publishes to AWS Kinesis stream.

Features:
    - Realistic transaction patterns
    - Configurable transaction rate (TPS)
    - Fraud pattern injection
    - Customer behavior simulation
    - Geographic distribution
    - Merchant categorization
    - Support for Kinesis and LocalStack

Usage:
    # Continuous mode with fraud patterns
    python transaction_generator.py --stream transactions --rate 100 --fraud-rate 0.05

    # Generate specific number of transactions
    python transaction_generator.py --transactions 10000 --rate 50

    # Use LocalStack for local testing
    python transaction_generator.py --localstack --rate 10

Author: DataForgeAI Team
Version: 1.0.0
"""

import argparse
import json
import logging
import random
import signal
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

# AWS SDK
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logging.error("boto3 not available - install with: pip install boto3")

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Transaction patterns
CUSTOMER_COUNT = 1000
MERCHANT_COUNT = 500

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
CURRENCY_WEIGHTS = [0.60, 0.20, 0.08, 0.05, 0.04, 0.03]

MERCHANT_CATEGORIES = [
    "RETAIL", "GROCERY", "RESTAURANT", "GAS_STATION", "HOTEL",
    "AIRLINE", "HEALTHCARE", "ENTERTAINMENT", "UTILITIES",
    "GAMBLING", "CRYPTO", "WIRE_TRANSFER", "ATM_WITHDRAWAL"
]

MERCHANT_CATEGORY_WEIGHTS = [
    0.25, 0.20, 0.15, 0.10, 0.05,
    0.05, 0.04, 0.04, 0.04,
    0.02, 0.02, 0.02, 0.02
]

COUNTRIES = ["US", "GB", "DE", "FR", "CA", "AU", "JP", "NG", "PK", "RU", "CN"]
COUNTRY_WEIGHTS = [0.50, 0.15, 0.10, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01, 0.01, 0.01]

# Fraud patterns
FRAUD_PATTERNS = [
    "high_velocity",      # Many transactions in short time
    "high_amount",        # Unusually large amount
    "suspicious_merchant",# Gambling, crypto, etc.
    "risky_country",      # High-risk countries
    "unusual_hours",      # Transactions at odd hours
    "velocity_spike"      # Sudden spike in activity
]


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Customer:
    """Customer profile with spending patterns."""
    customer_id: str
    risk_score: float
    avg_transaction_amount: float
    typical_categories: List[str]
    home_country: str
    typical_currency: str

    def generate_amount(self, is_fraud: bool = False) -> float:
        """Generate transaction amount based on customer profile."""
        if is_fraud:
            # Fraudulent transactions often have higher amounts
            return random.uniform(self.avg_transaction_amount * 2, 10000)
        else:
            # Normal distribution around average
            amount = np.random.lognormal(
                mean=np.log(self.avg_transaction_amount),
                sigma=0.5
            )
            return round(max(1.0, amount), 2)


@dataclass
class Merchant:
    """Merchant information."""
    merchant_id: str
    merchant_category: str
    merchant_country: str


@dataclass
class Transaction:
    """Transaction data."""
    transaction_id: str
    customer_id: str
    timestamp: str
    amount: float
    currency: str
    merchant_id: str
    merchant_category: str
    merchant_country: str
    card_last_4: str
    location_lat: float
    location_lon: float
    ip_address: str
    device_id: str

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), indent=None)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ============================================================================
# KINESIS PRODUCER
# ============================================================================

class TransactionProducer:
    """Generate and publish transactions to Kinesis."""

    def __init__(
        self,
        stream_name: str,
        region: str = "us-east-1",
        localstack: bool = False,
        fraud_rate: float = 0.05
    ):
        """
        Initialize transaction producer.

        Args:
            stream_name: Kinesis stream name
            region: AWS region
            localstack: Use LocalStack for local testing
            fraud_rate: Probability of generating fraudulent transaction
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required - install with: pip install boto3")

        self.stream_name = stream_name
        self.region = region
        self.fraud_rate = fraud_rate
        self.transactions_produced = 0
        self.fraud_transactions = 0

        # Initialize Kinesis client
        if localstack:
            logger.info("Using LocalStack for Kinesis")
            self.kinesis = boto3.client(
                'kinesis',
                region_name=region,
                endpoint_url='http://localhost:4566',
                aws_access_key_id='test',
                aws_secret_access_key='test'
            )
        else:
            self.kinesis = boto3.client('kinesis', region_name=region)

        # Initialize customers and merchants
        self.customers = self._create_customers()
        self.merchants = self._create_merchants()

        # Verify stream exists
        self._verify_stream()

        logger.info(f"Initialized producer for stream: {stream_name}")
        logger.info(f"Customers: {len(self.customers)}, Merchants: {len(self.merchants)}")
        logger.info(f"Fraud rate: {fraud_rate * 100}%")

    def _verify_stream(self) -> None:
        """Verify Kinesis stream exists."""
        try:
            response = self.kinesis.describe_stream(StreamName=self.stream_name)
            status = response['StreamDescription']['StreamStatus']
            logger.info(f"Stream status: {status}")

            if status != 'ACTIVE':
                logger.warning(f"Stream is not active: {status}")

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.error(f"Stream not found: {self.stream_name}")
                logger.info("Create stream with: aws kinesis create-stream --stream-name transactions --shard-count 1")
                raise
            else:
                raise

    def _create_customers(self) -> List[Customer]:
        """Create simulated customers."""
        customers = []

        for i in range(CUSTOMER_COUNT):
            # Generate customer risk score (most are low risk)
            if random.random() < 0.1:
                risk_score = random.uniform(0.6, 0.9)  # High risk
            elif random.random() < 0.3:
                risk_score = random.uniform(0.4, 0.6)  # Medium risk
            else:
                risk_score = random.uniform(0.1, 0.4)  # Low risk

            customer = Customer(
                customer_id=f"CUST-{i:06d}",
                risk_score=risk_score,
                avg_transaction_amount=random.uniform(20, 500),
                typical_categories=random.sample(
                    MERCHANT_CATEGORIES[:9],  # Exclude suspicious categories
                    k=random.randint(2, 4)
                ),
                home_country=random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS)[0],
                typical_currency=random.choices(CURRENCIES, weights=CURRENCY_WEIGHTS)[0]
            )
            customers.append(customer)

        return customers

    def _create_merchants(self) -> List[Merchant]:
        """Create simulated merchants."""
        merchants = []

        for i in range(MERCHANT_COUNT):
            merchant = Merchant(
                merchant_id=f"MERCH-{i:05d}",
                merchant_category=random.choices(
                    MERCHANT_CATEGORIES,
                    weights=MERCHANT_CATEGORY_WEIGHTS
                )[0],
                merchant_country=random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS)[0]
            )
            merchants.append(merchant)

        return merchants

    def _generate_location(self, country: str) -> Tuple[float, float]:
        """Generate latitude/longitude for country."""
        # Simplified location mapping
        locations = {
            "US": (37.7749, -122.4194),
            "GB": (51.5074, -0.1278),
            "DE": (52.5200, 13.4050),
            "FR": (48.8566, 2.3522),
            "CA": (43.6532, -79.3832),
            "AU": (-33.8688, 151.2093),
            "JP": (35.6762, 139.6503),
            "NG": (9.0820, 8.6753),
            "PK": (33.6844, 73.0479),
            "RU": (55.7558, 37.6173),
            "CN": (39.9042, 116.4074)
        }

        base_lat, base_lon = locations.get(country, (0.0, 0.0))

        # Add random offset
        lat = base_lat + random.uniform(-1, 1)
        lon = base_lon + random.uniform(-1, 1)

        return round(lat, 4), round(lon, 4)

    def _generate_ip_address(self) -> str:
        """Generate random IP address."""
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}"

    def _should_be_fraudulent(self, customer: Customer) -> bool:
        """Determine if transaction should be fraudulent."""
        # Higher chance for high-risk customers
        fraud_probability = self.fraud_rate * (1 + customer.risk_score)
        return random.random() < fraud_probability

    def _apply_fraud_pattern(
        self,
        customer: Customer,
        merchant: Merchant,
        amount: float
    ) -> Tuple[Merchant, float]:
        """
        Apply fraud pattern to transaction.

        Args:
            customer: Customer
            merchant: Merchant
            amount: Transaction amount

        Returns:
            Tuple[Merchant, float]: Modified merchant and amount
        """
        pattern = random.choice(FRAUD_PATTERNS)

        if pattern == "high_amount":
            amount = random.uniform(5000, 15000)

        elif pattern == "suspicious_merchant":
            # Use gambling, crypto, or wire transfer
            suspicious_cats = ["GAMBLING", "CRYPTO", "WIRE_TRANSFER"]
            merchant.merchant_category = random.choice(suspicious_cats)

        elif pattern == "risky_country":
            # Use high-risk country
            risky_countries = ["NG", "PK", "RU", "CN"]
            merchant.merchant_country = random.choice(risky_countries)

        return merchant, amount

    def _generate_transaction(self, customer: Customer) -> Transaction:
        """
        Generate a single transaction.

        Args:
            customer: Customer to generate transaction for

        Returns:
            Transaction: Generated transaction
        """
        # Determine if fraudulent
        is_fraud = self._should_be_fraudulent(customer)

        # Select merchant
        merchant = random.choice(self.merchants)

        # Generate amount
        amount = customer.generate_amount(is_fraud)

        # Apply fraud pattern if fraudulent
        if is_fraud:
            merchant, amount = self._apply_fraud_pattern(customer, merchant, amount)
            self.fraud_transactions += 1

        # Generate location
        lat, lon = self._generate_location(merchant.merchant_country)

        # Create transaction
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            customer_id=customer.customer_id,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            amount=amount,
            currency=customer.typical_currency,
            merchant_id=merchant.merchant_id,
            merchant_category=merchant.merchant_category,
            merchant_country=merchant.merchant_country,
            card_last_4=f"{random.randint(1000, 9999)}",
            location_lat=lat,
            location_lon=lon,
            ip_address=self._generate_ip_address(),
            device_id=f"DEV-{random.randint(100000, 999999)}"
        )

        return transaction

    def _send_to_kinesis(self, transaction: Transaction) -> bool:
        """
        Send transaction to Kinesis stream.

        Args:
            transaction: Transaction to send

        Returns:
            bool: True if successful
        """
        try:
            response = self.kinesis.put_record(
                StreamName=self.stream_name,
                Data=transaction.to_json(),
                PartitionKey=transaction.customer_id
            )

            self.transactions_produced += 1

            if self.transactions_produced % 100 == 0:
                logger.info(
                    f"Produced {self.transactions_produced} transactions "
                    f"({self.fraud_transactions} fraudulent, "
                    f"{self.fraud_transactions / self.transactions_produced * 100:.1f}%) "
                    f"- Shard: {response['ShardId']}, "
                    f"Seq: {response['SequenceNumber'][:20]}..."
                )

            return True

        except ClientError as e:
            logger.error(f"Error sending to Kinesis: {e}")
            return False

    def produce_transactions(
        self,
        rate: float = 10.0,
        max_transactions: Optional[int] = None,
        duration: Optional[int] = None
    ) -> None:
        """
        Produce transactions at specified rate.

        Args:
            rate: Transactions per second
            max_transactions: Maximum number of transactions (None for unlimited)
            duration: Duration in seconds (None for unlimited)
        """
        logger.info(f"Starting transaction production at {rate} TPS")
        if max_transactions:
            logger.info(f"Will produce {max_transactions} transactions")
        if duration:
            logger.info(f"Will run for {duration} seconds")

        start_time = time.time()
        interval = 1.0 / rate

        try:
            while True:
                # Check termination conditions
                if max_transactions and self.transactions_produced >= max_transactions:
                    logger.info(f"Reached max transactions: {max_transactions}")
                    break

                if duration and (time.time() - start_time) >= duration:
                    logger.info(f"Reached duration: {duration} seconds")
                    break

                # Generate and send transaction
                customer = random.choice(self.customers)
                transaction = self._generate_transaction(customer)
                self._send_to_kinesis(transaction)

                # Sleep to maintain target rate
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
        finally:
            self._print_summary(time.time() - start_time)

    def _print_summary(self, elapsed_time: float) -> None:
        """Print production summary."""
        logger.info("=" * 80)
        logger.info("TRANSACTION GENERATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total transactions: {self.transactions_produced}")
        logger.info(f"Fraudulent transactions: {self.fraud_transactions}")
        logger.info(f"Fraud rate: {self.fraud_transactions / max(1, self.transactions_produced) * 100:.2f}%")
        logger.info(f"Elapsed time: {elapsed_time:.2f} seconds")
        logger.info(f"Average TPS: {self.transactions_produced / max(1, elapsed_time):.2f}")
        logger.info("=" * 80)


# ============================================================================
# MAIN
# ============================================================================

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    logger.info("Received signal to terminate")
    sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate mock transactions and publish to Kinesis"
    )

    parser.add_argument(
        "--stream",
        type=str,
        default="transactions",
        help="Kinesis stream name (default: transactions)"
    )

    parser.add_argument(
        "--region",
        type=str,
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )

    parser.add_argument(
        "--rate",
        type=float,
        default=10.0,
        help="Transactions per second (default: 10)"
    )

    parser.add_argument(
        "--transactions",
        type=int,
        help="Total number of transactions to produce (default: unlimited)"
    )

    parser.add_argument(
        "--duration",
        type=int,
        help="Duration in seconds (default: unlimited)"
    )

    parser.add_argument(
        "--fraud-rate",
        type=float,
        default=0.05,
        help="Probability of fraud (0.0-1.0, default: 0.05)"
    )

    parser.add_argument(
        "--localstack",
        action="store_true",
        help="Use LocalStack instead of AWS"
    )

    args = parser.parse_args()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run producer
    producer = TransactionProducer(
        stream_name=args.stream,
        region=args.region,
        localstack=args.localstack,
        fraud_rate=args.fraud_rate
    )

    producer.produce_transactions(
        rate=args.rate,
        max_transactions=args.transactions,
        duration=args.duration
    )


if __name__ == "__main__":
    main()
