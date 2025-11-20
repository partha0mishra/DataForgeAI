#!/bin/bash

# S3 CSV to Snowflake dbt Pipeline - Local Test Runner
# This script runs the pipeline locally for testing purposes

set -e  # Exit on error

echo "==================================="
echo "S3 CSV to Snowflake dbt Pipeline"
echo "Local Test Runner"
echo "==================================="
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
    pip install pytest pandas
fi
echo -e "${GREEN}✓ pytest found${NC}"

# Run tests
echo ""
echo "Running unit tests..."
python3 -m pytest tests/test_pipeline.py -v

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}==================================="
    echo -e "✓ All tests passed!"
    echo -e "===================================${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Configure Snowflake connection"
    echo "2. Configure AWS S3 access"
    echo "3. Deploy DAG to Airflow:"
    echo "   cp generated_code/dags/s3_to_snowflake_dag.py \$AIRFLOW_HOME/dags/"
    echo "4. Deploy dbt models:"
    echo "   cp -r generated_code/dbt \$AIRFLOW_HOME/"
    echo "5. Test manually:"
    echo "   airflow dags test s3_csv_to_snowflake_dbt 2025-01-01"
    echo ""
else
    echo ""
    echo -e "${RED}==================================="
    echo -e "✗ Tests failed!"
    echo -e "===================================${NC}"
    exit 1
fi
