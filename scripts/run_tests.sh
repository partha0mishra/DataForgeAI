#!/bin/bash
# DataForge AI Platform - Test Runner Script

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "DataForge AI Platform - Test Suite"
echo "========================================="

# Change to project root
cd "$(dirname "$0")/.."

# Default values
TEST_TYPE="all"
VERBOSE=false
COVERAGE=false
MARKERS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--unit)
            TEST_TYPE="unit"
            MARKERS="-m unit"
            shift
            ;;
        -i|--integration)
            TEST_TYPE="integration"
            MARKERS="-m integration"
            shift
            ;;
        -a|--api)
            TEST_TYPE="api"
            MARKERS="-m api"
            shift
            ;;
        --auth)
            TEST_TYPE="auth"
            MARKERS="-m auth"
            shift
            ;;
        --db)
            TEST_TYPE="database"
            MARKERS="-m db"
            shift
            ;;
        -f|--fast)
            TEST_TYPE="fast"
            MARKERS="-m 'not slow'"
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -u, --unit         Run only unit tests"
            echo "  -i, --integration  Run only integration tests"
            echo "  -a, --api          Run only API tests"
            echo "  --auth             Run only authentication tests"
            echo "  --db               Run only database tests"
            echo "  -f, --fast         Run only fast tests (exclude slow tests)"
            echo "  -v, --verbose      Verbose output"
            echo "  -c, --coverage     Generate coverage report"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                 # Run all tests"
            echo "  $0 -u -v           # Run unit tests with verbose output"
            echo "  $0 -i -c           # Run integration tests with coverage"
            echo "  $0 -f              # Run only fast tests"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}Test Type: ${TEST_TYPE}${NC}"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}pytest is not installed!${NC}"
    echo "Install with: pip install pytest pytest-cov"
    exit 1
fi

# Build pytest command
PYTEST_CMD="pytest tests/"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=shared-libraries --cov=accelerators --cov-report=html --cov-report=term"
fi

if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD $MARKERS"
fi

echo -e "${YELLOW}Running: $PYTEST_CMD${NC}"
echo ""

# Run tests
if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}=========================================${NC}"

    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${YELLOW}Coverage report generated: htmlcov/index.html${NC}"
    fi

    exit 0
else
    echo ""
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}✗ Tests failed!${NC}"
    echo -e "${RED}=========================================${NC}"
    exit 1
fi
