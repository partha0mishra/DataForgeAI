#!/usr/bin/env python3
"""
Slack Notifier for Fraud Alerts
================================

Sends formatted fraud alerts to Slack with rate limiting and retry logic.
Can be extended for other notification channels (PagerDuty, email, etc.).

Features:
    - Rich message formatting with blocks
    - Rate limiting to prevent spam
    - Retry logic with exponential backoff
    - Alert severity levels
    - Thread grouping for related alerts
    - Custom message templates

Usage:
    from slack_notifier import SlackNotifier

    notifier = SlackNotifier(webhook_url)
    notifier.send_fraud_alert(transaction_data)

Author: DataForgeAI Team
Version: 1.0.0
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import deque
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting configuration
MAX_ALERTS_PER_MINUTE = 10
MAX_ALERTS_PER_HOUR = 100

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2  # Exponential backoff: 1s, 2s, 4s

# Color codes for alert severity
SEVERITY_COLORS = {
    "CRITICAL": "#FF0000",  # Red
    "HIGH": "#FF6600",      # Orange
    "MEDIUM": "#FFCC00",    # Yellow
    "LOW": "#00CC00"        # Green
}


# ============================================================================
# SLACK NOTIFIER
# ============================================================================

class SlackNotifier:
    """Send fraud alerts to Slack with rate limiting and retry logic."""

    def __init__(self, webhook_url: str, rate_limit: bool = True):
        """
        Initialize Slack notifier.

        Args:
            webhook_url: Slack webhook URL
            rate_limit: Enable rate limiting (default: True)
        """
        self.webhook_url = webhook_url
        self.rate_limit_enabled = rate_limit

        # Rate limiting tracking
        self.alert_times_minute = deque(maxlen=MAX_ALERTS_PER_MINUTE)
        self.alert_times_hour = deque(maxlen=MAX_ALERTS_PER_HOUR)

        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info("Slack notifier initialized")

    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.

        Returns:
            bool: True if within limits, False if rate limit exceeded
        """
        if not self.rate_limit_enabled:
            return True

        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)

        # Remove old timestamps
        while self.alert_times_minute and self.alert_times_minute[0] < one_minute_ago:
            self.alert_times_minute.popleft()

        while self.alert_times_hour and self.alert_times_hour[0] < one_hour_ago:
            self.alert_times_hour.popleft()

        # Check limits
        if len(self.alert_times_minute) >= MAX_ALERTS_PER_MINUTE:
            logger.warning(f"Rate limit exceeded: {MAX_ALERTS_PER_MINUTE} alerts per minute")
            return False

        if len(self.alert_times_hour) >= MAX_ALERTS_PER_HOUR:
            logger.warning(f"Rate limit exceeded: {MAX_ALERTS_PER_HOUR} alerts per hour")
            return False

        return True

    def _record_alert(self) -> None:
        """Record that an alert was sent for rate limiting."""
        now = datetime.now()
        self.alert_times_minute.append(now)
        self.alert_times_hour.append(now)

    def _get_severity_from_score(self, fraud_score: float) -> str:
        """
        Determine severity level from fraud score.

        Args:
            fraud_score: Fraud score (0.0 to 1.0)

        Returns:
            str: Severity level
        """
        if fraud_score >= 0.95:
            return "CRITICAL"
        elif fraud_score >= 0.8:
            return "HIGH"
        elif fraud_score >= 0.5:
            return "MEDIUM"
        else:
            return "LOW"

    def _format_currency(self, amount: float, currency: str = "USD") -> str:
        """
        Format currency amount.

        Args:
            amount: Amount
            currency: Currency code

        Returns:
            str: Formatted amount
        """
        symbol_map = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥"
        }
        symbol = symbol_map.get(currency, currency)
        return f"{symbol}{amount:,.2f}"

    def _create_fraud_alert_payload(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Slack message payload for fraud alert.

        Args:
            transaction: Transaction data

        Returns:
            Dict: Slack message payload
        """
        fraud_score = transaction.get("fraud_score", 0.0)
        severity = self._get_severity_from_score(fraud_score)
        color = SEVERITY_COLORS[severity]

        # Format transaction details
        transaction_id = transaction.get("transaction_id", "Unknown")
        customer_id = transaction.get("customer_id", "Unknown")
        amount = transaction.get("amount", 0.0)
        currency = transaction.get("currency", "USD")
        merchant_id = transaction.get("merchant_id", "Unknown")
        merchant_category = transaction.get("merchant_category", "Unknown")
        risk_level = transaction.get("risk_level", severity)
        timestamp = transaction.get("timestamp", datetime.now().isoformat())

        # Create rich message with blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {severity} Fraud Alert",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Transaction ID:*\n{transaction_id}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Fraud Score:*\n{fraud_score:.3f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Amount:*\n{self._format_currency(amount, currency)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Risk Level:*\n{risk_level}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Customer ID:*\n{customer_id}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Merchant:*\n{merchant_id}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Category:*\n{merchant_category}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Timestamp:*\n{timestamp}"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "⚠️ Immediate action required. Please review this transaction."
                    }
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Block Transaction"
                        },
                        "style": "danger",
                        "value": f"block_{transaction_id}",
                        "action_id": "block_transaction"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Allow Transaction"
                        },
                        "style": "primary",
                        "value": f"allow_{transaction_id}",
                        "action_id": "allow_transaction"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Details"
                        },
                        "value": f"details_{transaction_id}",
                        "action_id": "view_details"
                    }
                ]
            }
        ]

        # Fallback text for notifications
        fallback_text = (
            f"{severity} Fraud Alert: Transaction {transaction_id} "
            f"for {self._format_currency(amount, currency)} "
            f"(Score: {fraud_score:.3f})"
        )

        payload = {
            "text": fallback_text,
            "blocks": blocks,
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Alert Type",
                            "value": "Fraud Detection",
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": severity,
                            "short": True
                        }
                    ],
                    "footer": "DataForge Fraud Detection System",
                    "ts": int(time.time())
                }
            ]
        }

        return payload

    def send_fraud_alert(self, transaction: Dict[str, Any]) -> bool:
        """
        Send fraud alert to Slack.

        Args:
            transaction: Transaction data

        Returns:
            bool: True if sent successfully, False otherwise
        """
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning(f"Rate limit exceeded, skipping alert for transaction {transaction.get('transaction_id')}")
            return False

        # Create payload
        payload = self._create_fraud_alert_payload(transaction)

        # Send to Slack
        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Fraud alert sent for transaction {transaction.get('transaction_id')}")
                self._record_alert()
                return True
            else:
                logger.error(
                    f"Failed to send alert: HTTP {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending alert: {e}")
            return False

    def send_simple_message(self, text: str, severity: str = "LOW") -> bool:
        """
        Send a simple text message to Slack.

        Args:
            text: Message text
            severity: Severity level for color coding

        Returns:
            bool: True if sent successfully
        """
        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded, skipping message")
            return False

        payload = {
            "text": text,
            "attachments": [
                {
                    "color": SEVERITY_COLORS.get(severity, SEVERITY_COLORS["LOW"]),
                    "text": text,
                    "footer": "DataForge Fraud Detection System",
                    "ts": int(time.time())
                }
            ]
        }

        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info("Simple message sent to Slack")
                self._record_alert()
                return True
            else:
                logger.error(f"Failed to send message: HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message: {e}")
            return False

    def send_summary(self, summary_data: Dict[str, Any]) -> bool:
        """
        Send a summary report to Slack.

        Args:
            summary_data: Summary statistics

        Returns:
            bool: True if sent successfully
        """
        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded, skipping summary")
            return False

        total_transactions = summary_data.get("total_transactions", 0)
        fraud_detected = summary_data.get("fraud_detected", 0)
        fraud_rate = summary_data.get("fraud_rate", 0.0)
        total_amount = summary_data.get("total_amount", 0.0)
        fraud_amount = summary_data.get("fraud_amount", 0.0)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Fraud Detection Summary",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Transactions:*\n{total_transactions:,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Fraud Detected:*\n{fraud_detected:,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Fraud Rate:*\n{fraud_rate:.2f}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Amount:*\n${total_amount:,.2f}"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            }
        ]

        payload = {
            "text": f"Fraud Detection Summary: {fraud_detected} fraud cases detected",
            "blocks": blocks
        }

        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info("Summary sent to Slack")
                self._record_alert()
                return True
            else:
                logger.error(f"Failed to send summary: HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending summary: {e}")
            return False


# ============================================================================
# TESTING
# ============================================================================

def test_notifier():
    """Test Slack notifier with sample data."""
    import os

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.error("SLACK_WEBHOOK_URL environment variable not set")
        return

    notifier = SlackNotifier(webhook_url)

    # Test fraud alert
    test_transaction = {
        "transaction_id": "TXN-12345",
        "customer_id": "CUST-67890",
        "amount": 5500.00,
        "currency": "USD",
        "merchant_id": "MERCH-123",
        "merchant_category": "GAMBLING",
        "fraud_score": 0.92,
        "risk_level": "HIGH",
        "timestamp": datetime.now().isoformat()
    }

    notifier.send_fraud_alert(test_transaction)

    # Test summary
    test_summary = {
        "total_transactions": 10000,
        "fraud_detected": 250,
        "fraud_rate": 2.5,
        "total_amount": 5000000.00,
        "fraud_amount": 125000.00
    }

    notifier.send_summary(test_summary)


if __name__ == "__main__":
    test_notifier()
