"""
AWS Lambda function for real-time fraud detection on Kinesis stream.
"""

import json
import base64
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any
import math

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
cloudwatch = boto3.client('cloudwatch')

# Configuration
USER_PROFILES_TABLE = 'user-profiles'
FRAUD_ALERTS_TABLE = 'fraud-alerts'
MERCHANT_BLOCKLIST_TABLE = 'merchant-blocklist'
FRAUD_ALERTS_TOPIC = 'arn:aws:sns:us-east-1:123456789012:fraud-alerts'


def lambda_handler(event, context):
    """Process Kinesis stream events for fraud detection."""

    fraud_detected_count = 0
    processing_start = datetime.now()

    for record in event['Records']:
        # Decode Kinesis record
        payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
        transaction = json.loads(payload)

        # Run fraud detection rules
        fraud_signals = detect_fraud(transaction)

        if fraud_signals:
            fraud_detected_count += 1
            handle_fraud_alert(transaction, fraud_signals)

    # Emit CloudWatch metrics
    processing_duration = (datetime.now() - processing_start).total_seconds() * 1000

    cloudwatch.put_metric_data(
        Namespace='FraudDetection',
        MetricData=[
            {
                'MetricName': 'FraudTransactionsDetected',
                'Value': fraud_detected_count,
                'Unit': 'Count',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'ProcessingLatency',
                'Value': processing_duration,
                'Unit': 'Milliseconds',
                'Timestamp': datetime.now()
            }
        ]
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(event['Records']),
            'fraud_detected': fraud_detected_count
        })
    }


def detect_fraud(transaction: Dict[str, Any]) -> List[str]:
    """Run fraud detection rules on a transaction."""
    signals = []

    # Rule 1: High velocity check
    if check_high_velocity(transaction):
        signals.append('HIGH_VELOCITY')

    # Rule 2: Unusual amount check
    if check_unusual_amount(transaction):
        signals.append('UNUSUAL_AMOUNT')

    # Rule 3: Location anomaly check
    if check_location_anomaly(transaction):
        signals.append('LOCATION_ANOMALY')

    # Rule 4: Suspicious merchant check
    if check_suspicious_merchant(transaction):
        signals.append('SUSPICIOUS_MERCHANT')

    return signals


def check_high_velocity(transaction: Dict[str, Any]) -> bool:
    """Check if user has made too many transactions in short time."""
    user_id = transaction['user_id']
    current_time = datetime.fromisoformat(transaction['timestamp'].replace('Z', '+00:00'))

    # Get user's recent transactions from DynamoDB
    table = dynamodb.Table(USER_PROFILES_TABLE)

    try:
        response = table.get_item(Key={'user_id': user_id})
        if 'Item' not in response:
            return False

        recent_transactions = response['Item'].get('recent_transactions', [])

        # Count transactions in last 10 minutes
        time_threshold = current_time - timedelta(minutes=10)
        recent_count = sum(
            1 for txn in recent_transactions
            if datetime.fromisoformat(txn['timestamp'].replace('Z', '+00:00')) > time_threshold
        )

        return recent_count >= 5

    except Exception as e:
        print(f"Error checking velocity: {e}")
        return False


def check_unusual_amount(transaction: Dict[str, Any]) -> bool:
    """Check if transaction amount is unusual for this user."""
    user_id = transaction['user_id']
    amount = transaction['amount']

    table = dynamodb.Table(USER_PROFILES_TABLE)

    try:
        response = table.get_item(Key={'user_id': user_id})
        if 'Item' not in response:
            return False

        user_profile = response['Item']
        avg_amount = user_profile.get('avg_transaction_amount', 0)
        std_dev = user_profile.get('std_dev_amount', 0)

        # Flag if more than 3 standard deviations from average
        if std_dev > 0:
            z_score = abs(amount - avg_amount) / std_dev
            return z_score > 3

        # If no std dev, flag very large amounts
        return amount > 1000

    except Exception as e:
        print(f"Error checking amount: {e}")
        return False


def check_location_anomaly(transaction: Dict[str, Any]) -> bool:
    """Check for impossible travel between locations."""
    user_id = transaction['user_id']
    current_location = transaction.get('location', {})

    if not current_location:
        return False

    table = dynamodb.Table(USER_PROFILES_TABLE)

    try:
        response = table.get_item(Key={'user_id': user_id})
        if 'Item' not in response:
            return False

        last_location = response['Item'].get('last_location', {})
        last_transaction_time = response['Item'].get('last_transaction_time')

        if not last_location or not last_transaction_time:
            return False

        # Calculate distance and time
        distance_miles = calculate_distance(
            last_location['lat'], last_location['lon'],
            current_location['lat'], current_location['lon']
        )

        time_diff_hours = (
            datetime.fromisoformat(transaction['timestamp'].replace('Z', '+00:00')) -
            datetime.fromisoformat(last_transaction_time.replace('Z', '+00:00'))
        ).total_seconds() / 3600

        # Check if travel speed exceeds 600 mph (impossible for normal travel)
        if time_diff_hours > 0:
            speed_mph = distance_miles / time_diff_hours
            return speed_mph > 600

        return False

    except Exception as e:
        print(f"Error checking location: {e}")
        return False


def check_suspicious_merchant(transaction: Dict[str, Any]) -> bool:
    """Check if merchant is on blocklist."""
    merchant_id = transaction.get('merchant_id')

    if not merchant_id:
        return False

    table = dynamodb.Table(MERCHANT_BLOCKLIST_TABLE)

    try:
        response = table.get_item(Key={'merchant_id': merchant_id})
        return 'Item' in response

    except Exception as e:
        print(f"Error checking merchant: {e}")
        return False


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in miles using Haversine formula."""
    R = 3959  # Earth's radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def handle_fraud_alert(transaction: Dict[str, Any], fraud_signals: List[str]):
    """Store fraud alert and send notifications."""

    # Store alert in DynamoDB
    table = dynamodb.Table(FRAUD_ALERTS_TABLE)

    alert = {
        'alert_id': f"alert_{transaction['transaction_id']}",
        'transaction_id': transaction['transaction_id'],
        'user_id': transaction['user_id'],
        'timestamp': transaction['timestamp'],
        'amount': str(transaction['amount']),
        'fraud_signals': fraud_signals,
        'merchant_id': transaction.get('merchant_id'),
        'merchant_name': transaction.get('merchant_name'),
        'status': 'PENDING_REVIEW',
        'created_at': datetime.now().isoformat()
    }

    table.put_item(Item=alert)

    # Send SNS notification
    message = f"""
    FRAUD ALERT

    Transaction ID: {transaction['transaction_id']}
    User ID: {transaction['user_id']}
    Amount: ${transaction['amount']} {transaction['currency']}
    Merchant: {transaction.get('merchant_name', 'Unknown')}
    Fraud Signals: {', '.join(fraud_signals)}

    Timestamp: {transaction['timestamp']}
    """

    sns.publish(
        TopicArn=FRAUD_ALERTS_TOPIC,
        Subject='Fraud Detection Alert',
        Message=message
    )

    print(f"Fraud alert created for transaction {transaction['transaction_id']}")
