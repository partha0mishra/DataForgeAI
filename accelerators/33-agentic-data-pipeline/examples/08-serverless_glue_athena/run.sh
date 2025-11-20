#!/bin/bash

# Serverless Glue + Athena Pipeline - Local Test Runner

set -e

echo "========================================"
echo "Serverless Glue + Athena Pipeline"
echo "Local Test Runner"
echo "========================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

python3 -m pytest tests/test_pipeline.py -v

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Deploy: Upload Glue scripts and deploy Step Functions"
else
    echo -e "${RED}✗ Tests failed!${NC}"
    exit 1
fi
