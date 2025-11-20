#!/bin/bash

# Oracle CDC to Snowflake Pipeline - Local Test Runner
# This script runs the pipeline tests locally

set -e  # Exit on error

echo "===================================="
echo "Oracle CDC to Snowflake Pipeline"
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
    echo "1. Set up Oracle database with LogMiner:"
    echo "   - Enable supplemental logging"
    echo "   - Create CDC user with required privileges"
    echo "   - Grant SELECT on tables to capture"
    echo ""
    echo "2. Deploy Kafka Connect with Debezium:"
    echo "   curl -X POST http://kafka-connect:8083/connectors \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d @generated_code/debezium/connector_config.json"
    echo ""
    echo "3. Configure Snowflake:"
    echo "   - Create database and schemas"
    echo "   - Set up external stage for S3"
    echo "   - Create target tables with CDC columns"
    echo ""
    echo "4. Deploy DAG to Airflow:"
    echo "   cp generated_code/dags/oracle_cdc_dag.py \$AIRFLOW_HOME/dags/"
    echo ""
    echo "5. Set Airflow variables:"
    echo "   airflow variables set snowflake_user <user>"
    echo "   airflow variables set snowflake_password <password>"
    echo ""
    echo "6. Monitor CDC pipeline:"
    echo "   - Check Kafka Connect status"
    echo "   - Monitor Kafka topics for CDC events"
    echo "   - Verify data in Snowflake"
    echo ""
else
    echo ""
    echo -e "${RED}===================================="
    echo -e "✗ Tests failed!"
    echo -e "====================================${NC}"
    exit 1
fi
