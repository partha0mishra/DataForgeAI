#!/bin/bash

# Multi-source Medallion Architecture - Local Test Runner
# This script runs the pipeline tests locally

set -e  # Exit on error

echo "============================================"
echo "Multi-source Medallion Architecture Pipeline"
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
    echo -e "${GREEN}============================================"
    echo -e "✓ All tests passed!"
    echo -e "============================================${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Set up Kafka cluster:"
    echo "   - Deploy Kafka brokers"
    echo "   - Create topics: user-events, transaction-events"
    echo "   - Configure producers to send events"
    echo ""
    echo "2. Set up PostgreSQL database:"
    echo "   - Create readonly user"
    echo "   - Grant SELECT permissions on tables"
    echo "   - Enable logical replication (optional for CDC)"
    echo ""
    echo "3. Configure Databricks:"
    echo "   - Create Unity Catalog: analytics"
    echo "   - Create schemas: bronze, silver, gold"
    echo "   - Set up secrets for PostgreSQL credentials"
    echo ""
    echo "4. Upload notebooks to Databricks:"
    echo "   databricks workspace import_dir generated_code/notebooks /Workspace/Pipelines"
    echo ""
    echo "5. Start streaming jobs (run continuously):"
    echo "   - bronze_streaming.py (Kafka ingestion)"
    echo "   - silver_transformations.py (real-time cleaning)"
    echo ""
    echo "6. Deploy batch DAG to Airflow:"
    echo "   cp generated_code/dags/medallion_orchestration_dag.py \$AIRFLOW_HOME/dags/"
    echo ""
    echo "7. Monitor the pipeline:"
    echo "   - Check Databricks jobs status"
    echo "   - Verify data in Delta tables"
    echo "   - Monitor Airflow DAG runs"
    echo ""
else
    echo ""
    echo -e "${RED}============================================"
    echo -e "✗ Tests failed!"
    echo -e "============================================${NC}"
    exit 1
fi
