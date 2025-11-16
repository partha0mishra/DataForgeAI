#!/bin/bash
# Validation script for DataForge AI Platform codebase

set -e

echo "🔍 DataForge AI Platform - Codebase Validation"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0

# Function to print results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $2"
        ((FAILED++))
    fi
}

# 1. Check directory structure
echo "1. Checking directory structure..."
check_dir() {
    if [ -d "$1" ]; then
        return 0
    else
        return 1
    fi
}

check_dir "shared/common/src/dataforge_common"
print_result $? "shared/common exists"

check_dir "shared/connectors/src/dataforge_connectors"
print_result $? "shared/connectors exists"

check_dir "shared/ai-core/src/dataforge_ai_core"
print_result $? "shared/ai-core exists"

check_dir "accelerators/01-pipeline-automation"
print_result $? "Accelerator 1 (Pipeline Automation) exists"

echo ""

# 2. Check Python syntax
echo "2. Checking Python syntax..."
check_python_file() {
    if [ -f "$1" ]; then
        python3 -m py_compile "$1" 2>/dev/null
        return $?
    else
        return 1
    fi
}

check_python_file "shared/common/src/dataforge_common/auth.py"
print_result $? "auth.py syntax valid"

check_python_file "shared/common/src/dataforge_common/config.py"
print_result $? "config.py syntax valid"

check_python_file "shared/connectors/src/dataforge_connectors/base.py"
print_result $? "connectors/base.py syntax valid"

check_python_file "shared/ai-core/src/dataforge_ai_core/llm_clients/openai.py"
print_result $? "llm_clients/openai.py syntax valid"

check_python_file "accelerators/01-pipeline-automation/api/src/main.py"
print_result $? "pipeline API main.py syntax valid"

echo ""

# 3. Check required files
echo "3. Checking required files..."
check_file() {
    if [ -f "$1" ]; then
        return 0
    else
        return 1
    fi
}

check_file "README.md"
print_result $? "README.md exists"

check_file "Makefile"
print_result $? "Makefile exists"

check_file ".env.example"
print_result $? ".env.example exists"

check_file "pyproject.toml"
print_result $? "pyproject.toml exists"

check_file "deployments/local/docker-compose.yml"
print_result $? "docker-compose.yml exists"

echo ""

# 4. Check setup.py files
echo "4. Checking setup.py files..."
check_file "shared/common/setup.py"
print_result $? "shared/common/setup.py exists"

check_file "shared/connectors/setup.py"
print_result $? "shared/connectors/setup.py exists"

check_file "shared/ai-core/setup.py"
print_result $? "shared/ai-core/setup.py exists"

echo ""

# 5. Check Airflow DAGs
echo "5. Checking Airflow DAGs..."
check_file "accelerators/01-pipeline-automation/airflow/dags/ingestion_template.py"
print_result $? "Ingestion DAG exists"

check_file "accelerators/01-pipeline-automation/airflow/dags/transformation_template.py"
print_result $? "Transformation DAG exists"

echo ""

# 6. Check dbt project
echo "6. Checking dbt project..."
check_file "accelerators/01-pipeline-automation/dbt/dbt_project.yml"
print_result $? "dbt_project.yml exists"

check_file "accelerators/01-pipeline-automation/dbt/models/staging/stg_customers.sql"
print_result $? "dbt staging model exists"

echo ""

# 7. Check Kubernetes manifests
echo "7. Checking Kubernetes manifests..."
check_file "accelerators/01-pipeline-automation/k8s/deployment.yaml"
print_result $? "K8s deployment exists"

echo ""

# Summary
echo "=============================================="
echo "Validation Summary:"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! Codebase is valid.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some checks failed. Please review the output above.${NC}"
    exit 1
fi
