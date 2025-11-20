#!/bin/bash

# Snowpark Python Native Pipeline - Local Test Runner
# This script runs the pipeline tests locally

set -e  # Exit on error

echo "========================================"
echo "Snowpark Python Native Pipeline"
echo "Local Test Runner"
echo "========================================"
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

# Check if snowflake-snowpark-python is available (optional)
if ! python3 -c "import snowflake.snowpark" &> /dev/null; then
    echo -e "${YELLOW}⚠ snowflake-snowpark-python not found (optional for local testing)${NC}"
    echo -e "${YELLOW}  Install with: pip install snowflake-snowpark-python${NC}"
else
    echo -e "${GREEN}✓ snowflake-snowpark-python found${NC}"
fi

# Run tests
echo ""
echo "Running unit tests..."
python3 -m pytest tests/test_pipeline.py -v

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================"
    echo -e "✓ All tests passed!"
    echo -e "========================================${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Install Snowpark Python:"
    echo "   pip install snowflake-snowpark-python"
    echo ""
    echo "2. Set up Snowflake connection:"
    echo "   export SNOWFLAKE_ACCOUNT='xy12345.us-east-1'"
    echo "   export SNOWFLAKE_USER='your_user'"
    echo "   export SNOWFLAKE_PASSWORD='your_password'"
    echo "   export SNOWFLAKE_ROLE='DATA_ENGINEER'"
    echo "   export SNOWFLAKE_WAREHOUSE='COMPUTE_WH'"
    echo ""
    echo "3. Run setup SQL to create objects:"
    echo "   snowsql -f generated_code/setup.sql"
    echo ""
    echo "4. Upload Python procedures to Snowflake stage:"
    echo "   snowsql -q \"PUT file://generated_code/procedures/*.py @ANALYTICS.STAGES.PYTHON_CODE AUTO_COMPRESS=FALSE;\""
    echo ""
    echo "5. Test procedures manually:"
    echo "   snowsql -q \"CALL ANALYTICS.PROCEDURES.INGEST_SALES_DATA('2025-01-15');\""
    echo "   snowsql -q \"CALL ANALYTICS.PROCEDURES.TRANSFORM_SALES_DATA('2025-01-15');\""
    echo "   snowsql -q \"CALL ANALYTICS.PROCEDURES.AGGREGATE_METRICS('2025-01-15');\""
    echo ""
    echo "6. Enable Snowflake Tasks for automation:"
    echo "   snowsql -q \"ALTER TASK ANALYTICS.PROCEDURES.AGGREGATE_METRICS_TASK RESUME;\""
    echo "   snowsql -q \"ALTER TASK ANALYTICS.PROCEDURES.TRANSFORM_SALES_TASK RESUME;\""
    echo "   snowsql -q \"ALTER TASK ANALYTICS.PROCEDURES.INGEST_SALES_TASK RESUME;\""
    echo ""
    echo "7. Monitor task execution:"
    echo "   snowsql -q \"SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY()) ORDER BY SCHEDULED_TIME DESC LIMIT 10;\""
    echo ""
else
    echo ""
    echo -e "${RED}========================================"
    echo -e "✗ Tests failed!"
    echo -e "========================================${NC}"
    exit 1
fi
