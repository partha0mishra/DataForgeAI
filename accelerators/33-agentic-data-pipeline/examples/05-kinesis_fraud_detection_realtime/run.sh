#!/bin/bash

# Kinesis Fraud Detection Pipeline - Local Test Runner
# This script runs the pipeline tests locally

set -e  # Exit on error

echo "============================================"
echo "Kinesis Fraud Detection Real-time Pipeline"
echo "Local Test Runner"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

# Check if pytest is installed
if ! python3 -c "import pytest" &> /dev/null; then
    echo -e "${YELLOW}⚠ pytest not found, installing...${NC}"
    pip install pytest
fi
echo -e "${GREEN}✓ pytest found${NC}"

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${YELLOW}⚠ Terraform not found (optional for deployment)${NC}"
else
    echo -e "${GREEN}✓ Terraform found${NC}"
fi

# Run tests
echo ""
echo "Running unit tests..."
python3 -m pytest tests/test_pipeline.py -v

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}============================================"
    echo -e "✓ All tests passed!"
    echo -e "============================================${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Deploy infrastructure with Terraform:"
    echo "   cd generated_code/terraform"
    echo "   terraform init"
    echo "   terraform plan"
    echo "   terraform apply"
    echo ""
    echo "2. Package Lambda function:"
    echo "   cd generated_code/lambda"
    echo "   pip install -r requirements.txt -t ."
    echo "   zip -r fraud_detector.zip ."
    echo ""
    echo "3. Update Lambda function code:"
    echo "   aws lambda update-function-code \\"
    echo "     --function-name fraud-detection-processor \\"
    echo "     --zip-file fileb://fraud_detector.zip"
    echo ""
    echo "4. Deploy Mage pipeline (if using Mage):"
    echo "   cp generated_code/mage/kinesis_pipeline.py \$MAGE_HOME/pipelines/"
    echo ""
    echo "5. Send test transactions to Kinesis:"
    echo "   aws kinesis put-record \\"
    echo "     --stream-name transaction-stream \\"
    echo "     --partition-key user_12345 \\"
    echo "     --data file://sample_data/transactions.json"
    echo ""
    echo "6. Monitor fraud alerts:"
    echo "   - Check DynamoDB fraud-alerts table"
    echo "   - Monitor SNS topic for email alerts"
    echo "   - View CloudWatch logs for Lambda execution"
    echo "   - Check CloudWatch metrics for fraud detection stats"
    echo ""
else
    echo ""
    echo -e "${RED}============================================"
    echo -e "✗ Tests failed!"
    echo -e "============================================${NC}"
    exit 1
fi
