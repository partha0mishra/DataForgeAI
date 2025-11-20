#!/bin/bash

# GA4 to BigQuery with Looker Pipeline - Local Test Runner

set -e

echo "========================================"
echo "GA4 to BigQuery with Looker Pipeline"
echo "Local Test Runner"
echo "========================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

if ! python3 -c "import pytest" &> /dev/null; then
    echo -e "${YELLOW}⚠ pytest not found, installing...${NC}"
    pip install pytest
fi
echo -e "${GREEN}✓ pytest found${NC}"

echo ""
echo "Running unit tests..."
python3 -m pytest tests/test_pipeline.py -v

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================"
    echo -e "✓ All tests passed!"
    echo -e "========================================${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Enable GA4 BigQuery export in Google Analytics"
    echo "2. Deploy DAG to Cloud Composer"
    echo "3. Deploy LookML to Looker project"
    echo ""
else
    echo ""
    echo -e "${RED}========================================"
    echo -e "✗ Tests failed!"
    echo -e "========================================${NC}"
    exit 1
fi
