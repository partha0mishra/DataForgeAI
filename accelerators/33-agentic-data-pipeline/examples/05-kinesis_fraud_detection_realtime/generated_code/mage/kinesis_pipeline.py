"""
Mage pipeline for Kinesis fraud detection orchestration.
"""

from mage_ai.data_preparation.decorators import data_loader, transformer, data_exporter
import boto3
import json
from typing import Dict, List

kinesis_client = boto3.client('kinesis', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

STREAM_NAME = 'transaction-stream'


@data_loader
def load_transactions() -> List[Dict]:
    """
    Load transactions from Kinesis stream.
    This would typically be triggered by Kinesis events.
    """
    # For demo purposes, return sample data
    # In production, this would read from Kinesis stream
    return []


@transformer
def enrich_transaction_data(transactions: List[Dict]) -> List[Dict]:
    """
    Enrich transactions with user profile data.
    """
    enriched = []

    for txn in transactions:
        user_id = txn['user_id']

        # Get user profile from DynamoDB
        table = dynamodb.Table('user-profiles')
        try:
            response = table.get_item(Key={'user_id': user_id})
            if 'Item' in response:
                user_profile = response['Item']
                txn['user_avg_amount'] = user_profile.get('avg_transaction_amount', 0)
                txn['user_risk_score'] = user_profile.get('risk_score', 0)

        except Exception as e:
            print(f"Error enriching transaction: {e}")

        enriched.append(txn)

    return enriched


@transformer
def apply_fraud_rules(transactions: List[Dict]) -> List[Dict]:
    """
    Apply fraud detection rules to transactions.
    """
    flagged_transactions = []

    for txn in transactions:
        fraud_score = 0
        flags = []

        # High amount check
        if txn['amount'] > 1000:
            fraud_score += 30
            flags.append('HIGH_AMOUNT')

        # User risk score check
        if txn.get('user_risk_score', 0) > 70:
            fraud_score += 40
            flags.append('HIGH_RISK_USER')

        # Unusual amount for user
        user_avg = txn.get('user_avg_amount', 0)
        if user_avg > 0 and txn['amount'] > user_avg * 3:
            fraud_score += 30
            flags.append('UNUSUAL_AMOUNT')

        if fraud_score > 50:
            txn['fraud_score'] = fraud_score
            txn['fraud_flags'] = flags
            flagged_transactions.append(txn)

    return flagged_transactions


@data_exporter
def export_to_fraud_alerts(flagged_transactions: List[Dict]):
    """
    Export flagged transactions to DynamoDB fraud alerts table.
    """
    if not flagged_transactions:
        print("No fraud detected")
        return

    table = dynamodb.Table('fraud-alerts')

    with table.batch_writer() as batch:
        for txn in flagged_transactions:
            alert = {
                'alert_id': f"alert_{txn['transaction_id']}",
                'transaction_id': txn['transaction_id'],
                'user_id': txn['user_id'],
                'amount': str(txn['amount']),
                'fraud_score': txn['fraud_score'],
                'fraud_flags': txn['fraud_flags'],
                'timestamp': txn['timestamp'],
                'status': 'PENDING_REVIEW'
            }
            batch.put_item(Item=alert)

    print(f"Exported {len(flagged_transactions)} fraud alerts")


@data_exporter
def send_alerts(flagged_transactions: List[Dict]):
    """
    Send SNS alerts for high-risk transactions.
    """
    if not flagged_transactions:
        return

    sns = boto3.client('sns', region_name='us-east-1')
    topic_arn = 'arn:aws:sns:us-east-1:123456789012:fraud-alerts'

    high_risk = [t for t in flagged_transactions if t['fraud_score'] > 70]

    for txn in high_risk:
        message = f"""
        HIGH RISK FRAUD ALERT

        Transaction: {txn['transaction_id']}
        User: {txn['user_id']}
        Amount: ${txn['amount']}
        Fraud Score: {txn['fraud_score']}
        Flags: {', '.join(txn['fraud_flags'])}
        """

        sns.publish(
            TopicArn=topic_arn,
            Subject='High Risk Fraud Alert',
            Message=message
        )

    print(f"Sent {len(high_risk)} high risk alerts")
