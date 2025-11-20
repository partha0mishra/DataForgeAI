"""
Unit tests for Kinesis fraud detection pipeline.
"""

import pytest
import json
from pathlib import Path


class TestSampleData:
    """Test sample transaction data."""

    def test_sample_data_exists(self):
        """Verify sample transactions file exists."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "transactions.json"
        assert sample_file.exists(), "Sample transactions file should exist"

    def test_sample_data_valid_json(self):
        """Verify sample data is valid JSON."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "transactions.json"
        with open(sample_file) as f:
            data = json.load(f)
        assert isinstance(data, list), "Sample data should be a list"
        assert len(data) > 0, "Should have sample transactions"

    def test_transaction_schema(self):
        """Verify transactions have correct schema."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "transactions.json"
        with open(sample_file) as f:
            transactions = json.load(f)

        txn = transactions[0]
        required_fields = ['transaction_id', 'user_id', 'timestamp', 'amount', 'merchant_id', 'location']
        for field in required_fields:
            assert field in txn, f"Transaction should have {field} field"

    def test_fraud_flags_present(self):
        """Verify some transactions are flagged as fraudulent."""
        sample_file = Path(__file__).parent.parent / "sample_data" / "transactions.json"
        with open(sample_file) as f:
            transactions = json.load(f)

        fraud_flags = [t.get('fraud_flag') for t in transactions]
        assert 'SUSPICIOUS_VELOCITY' in fraud_flags or 'SUSPICIOUS_MERCHANT' in fraud_flags, \
            "Should have examples of fraud"


class TestLambdaFunction:
    """Test Lambda fraud detection function."""

    def test_lambda_file_exists(self):
        """Verify Lambda function file exists."""
        lambda_file = Path(__file__).parent.parent / "generated_code" / "lambda" / "fraud_detector.py"
        assert lambda_file.exists(), "Lambda function should exist"

    def test_lambda_has_fraud_rules(self):
        """Verify Lambda implements fraud detection rules."""
        lambda_file = Path(__file__).parent.parent / "generated_code" / "lambda" / "fraud_detector.py"
        content = lambda_file.read_text()

        assert "detect_fraud" in content, "Should have fraud detection function"
        assert "high_velocity" in content.lower() or "velocity" in content.lower(), \
            "Should check transaction velocity"
        assert "unusual_amount" in content.lower() or "amount" in content.lower(), \
            "Should check unusual amounts"

    def test_lambda_uses_dynamodb(self):
        """Verify Lambda uses DynamoDB for user profiles."""
        lambda_file = Path(__file__).parent.parent / "generated_code" / "lambda" / "fraud_detector.py"
        content = lambda_file.read_text()

        assert "dynamodb" in content.lower(), "Should use DynamoDB"
        assert "user-profiles" in content or "user_profiles" in content, \
            "Should access user profiles table"

    def test_lambda_sends_alerts(self):
        """Verify Lambda sends SNS alerts."""
        lambda_file = Path(__file__).parent.parent / "generated_code" / "lambda" / "fraud_detector.py"
        content = lambda_file.read_text()

        assert "sns" in content.lower(), "Should use SNS"
        assert "publish" in content.lower(), "Should publish alerts"


class TestTerraform:
    """Test Terraform infrastructure code."""

    def test_terraform_file_exists(self):
        """Verify Terraform main file exists."""
        tf_file = Path(__file__).parent.parent / "generated_code" / "terraform" / "main.tf"
        assert tf_file.exists(), "Terraform file should exist"

    def test_terraform_creates_kinesis(self):
        """Verify Terraform creates Kinesis stream."""
        tf_file = Path(__file__).parent.parent / "generated_code" / "terraform" / "main.tf"
        content = tf_file.read_text()

        assert "aws_kinesis_stream" in content, "Should create Kinesis stream"
        assert "transaction-stream" in content, "Should name the stream"

    def test_terraform_creates_dynamodb(self):
        """Verify Terraform creates DynamoDB tables."""
        tf_file = Path(__file__).parent.parent / "generated_code" / "terraform" / "main.tf"
        content = tf_file.read_text()

        assert "aws_dynamodb_table" in content, "Should create DynamoDB tables"
        assert "user-profiles" in content or "user_profiles" in content, \
            "Should create user profiles table"
        assert "fraud-alerts" in content or "fraud_alerts" in content, \
            "Should create fraud alerts table"

    def test_terraform_creates_lambda(self):
        """Verify Terraform creates Lambda function."""
        tf_file = Path(__file__).parent.parent / "generated_code" / "terraform" / "main.tf"
        content = tf_file.read_text()

        assert "aws_lambda_function" in content, "Should create Lambda function"
        assert "fraud" in content.lower(), "Should reference fraud detection"

    def test_terraform_creates_sns(self):
        """Verify Terraform creates SNS topic."""
        tf_file = Path(__file__).parent.parent / "generated_code" / "terraform" / "main.tf"
        content = tf_file.read_text()

        assert "aws_sns_topic" in content, "Should create SNS topic"
        assert "fraud-alerts" in content or "fraud_alerts" in content, \
            "Should create fraud alerts topic"


class TestMagePipeline:
    """Test Mage orchestration pipeline."""

    def test_mage_file_exists(self):
        """Verify Mage pipeline file exists."""
        mage_file = Path(__file__).parent.parent / "generated_code" / "mage" / "kinesis_pipeline.py"
        assert mage_file.exists(), "Mage pipeline should exist"

    def test_mage_has_decorators(self):
        """Verify Mage pipeline uses decorators."""
        mage_file = Path(__file__).parent.parent / "generated_code" / "mage" / "kinesis_pipeline.py"
        content = mage_file.read_text()

        assert "@data_loader" in content, "Should have data loader"
        assert "@transformer" in content, "Should have transformer"
        assert "@data_exporter" in content, "Should have data exporter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
