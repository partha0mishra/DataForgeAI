#!/bin/bash

# Shopify to Databricks DLT Pipeline - Local Test Runner
# This script runs the pipeline tests locally

set -e  # Exit on error

echo "===================================="
echo "Shopify to Databricks DLT Pipeline"
echo "Local Test Runner"
echo "===================================="
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

# Run tests
echo ""
echo "Running unit tests..."
python3 -m pytest tests/test_pipeline.py -v

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}===================================="
    echo -e "✓ All tests passed!"
    echo -e "====================================${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Configure Databricks workspace connection"
    echo "2. Set up Shopify API credentials in Databricks Secrets:"
    echo "   databricks secrets create-scope shopify_api"
    echo "   databricks secrets put-secret shopify_api api_key"
    echo "   databricks secrets put-secret shopify_api api_password"
    echo "3. Upload DLT pipeline to Databricks:"
    echo "   databricks workspace import generated_code/notebooks/shopify_dlt_pipeline.py \\"
    echo "     /Workspace/Pipelines/shopify_dlt_pipeline -l PYTHON"
    echo "4. Create DLT pipeline:"
    echo "   databricks pipelines create --settings generated_code/config/pipeline_config.json"
    echo "5. Start the pipeline:"
    echo "   databricks pipelines start --pipeline-id <pipeline-id>"
    echo ""
else
    echo ""
    echo -e "${RED}===================================="
    echo -e "✗ Tests failed!"
    echo -e "====================================${NC}"
    exit 1
fi
