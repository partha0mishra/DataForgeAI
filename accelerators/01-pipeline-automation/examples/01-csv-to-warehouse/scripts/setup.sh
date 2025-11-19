#!/bin/bash

###############################################################################
# Sales CSV to Snowflake Pipeline - Setup Script
#
# This script automates the setup of the complete pipeline including:
# - Airflow connections and variables
# - S3 bucket and sample data upload
# - Snowflake database and schema creation
# - DAG deployment
# - dbt profile configuration
#
# Usage:
#   ./setup.sh [options]
#
# Options:
#   --s3-bucket BUCKET       S3 bucket name (required)
#   --snowflake-account ACC  Snowflake account identifier (required)
#   --snowflake-user USER    Snowflake username (required)
#   --snowflake-pass PASS    Snowflake password (required)
#   --skip-s3               Skip S3 setup
#   --skip-snowflake        Skip Snowflake setup
#   --dry-run               Print commands without executing
#
# Author: DataForgeAI
###############################################################################

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DRY_RUN=false
SKIP_S3=false
SKIP_SNOWFLAKE=false
S3_BUCKET=""
S3_PREFIX="sales/"
SNOWFLAKE_ACCOUNT=""
SNOWFLAKE_USER=""
SNOWFLAKE_PASSWORD=""
SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
SNOWFLAKE_DATABASE="ANALYTICS"
SNOWFLAKE_SCHEMA="sales"
SNOWFLAKE_ROLE="SYSADMIN"

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
EXAMPLE_DIR="$(dirname "$SCRIPT_DIR")"

###############################################################################
# Helper Functions
###############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

run_command() {
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] $1"
    else
        log_info "Executing: $1"
        eval "$1"
    fi
}

check_prerequisite() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed or not in PATH"
        exit 1
    fi
}

###############################################################################
# Parse Command Line Arguments
###############################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --s3-bucket)
            S3_BUCKET="$2"
            shift 2
            ;;
        --snowflake-account)
            SNOWFLAKE_ACCOUNT="$2"
            shift 2
            ;;
        --snowflake-user)
            SNOWFLAKE_USER="$2"
            shift 2
            ;;
        --snowflake-pass)
            SNOWFLAKE_PASSWORD="$2"
            shift 2
            ;;
        --skip-s3)
            SKIP_S3=true
            shift
            ;;
        --skip-snowflake)
            SKIP_SNOWFLAKE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            grep "^#" "$0" | grep -v "^#!/" | sed 's/^# //; s/^#//'
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

###############################################################################
# Validate Configuration
###############################################################################

log_info "Validating configuration..."

if [ "$SKIP_S3" = false ] && [ -z "$S3_BUCKET" ]; then
    log_error "S3 bucket name is required (use --s3-bucket or --skip-s3)"
    exit 1
fi

if [ "$SKIP_SNOWFLAKE" = false ]; then
    if [ -z "$SNOWFLAKE_ACCOUNT" ] || [ -z "$SNOWFLAKE_USER" ] || [ -z "$SNOWFLAKE_PASSWORD" ]; then
        log_error "Snowflake credentials are required (use --snowflake-* options or --skip-snowflake)"
        exit 1
    fi
fi

log_success "Configuration validated"

###############################################################################
# Check Prerequisites
###############################################################################

log_info "Checking prerequisites..."

check_prerequisite "airflow"

if [ "$SKIP_S3" = false ]; then
    check_prerequisite "aws"
fi

check_prerequisite "dbt"

log_success "All prerequisites found"

###############################################################################
# Setup Airflow Variables
###############################################################################

log_info "Setting up Airflow variables..."

run_command "airflow variables set s3_bucket '$S3_BUCKET'"
run_command "airflow variables set s3_prefix '$S3_PREFIX'"
run_command "airflow variables set s3_file_pattern 'sales_*.csv'"
run_command "airflow variables set snowflake_database '$SNOWFLAKE_DATABASE'"
run_command "airflow variables set snowflake_schema '$SNOWFLAKE_SCHEMA'"
run_command "airflow variables set snowflake_warehouse '$SNOWFLAKE_WAREHOUSE'"

log_success "Airflow variables configured"

###############################################################################
# Setup Airflow Connections
###############################################################################

log_info "Setting up Airflow connections..."

# Snowflake connection
if [ "$SKIP_SNOWFLAKE" = false ]; then
    SNOWFLAKE_EXTRA="{\"account\": \"$SNOWFLAKE_ACCOUNT\", \"warehouse\": \"$SNOWFLAKE_WAREHOUSE\", \"database\": \"$SNOWFLAKE_DATABASE\", \"role\": \"$SNOWFLAKE_ROLE\"}"

    run_command "airflow connections delete snowflake_default 2>/dev/null || true"
    run_command "airflow connections add snowflake_default \
        --conn-type 'snowflake' \
        --conn-login '$SNOWFLAKE_USER' \
        --conn-password '$SNOWFLAKE_PASSWORD' \
        --conn-schema '$SNOWFLAKE_SCHEMA' \
        --conn-extra '$SNOWFLAKE_EXTRA'"

    log_success "Snowflake connection configured"
fi

# AWS connection (if using S3)
if [ "$SKIP_S3" = false ]; then
    log_info "Verifying AWS credentials..."
    run_command "aws sts get-caller-identity > /dev/null"
    log_success "AWS connection verified"
fi

###############################################################################
# Upload Sample Data to S3
###############################################################################

if [ "$SKIP_S3" = false ]; then
    log_info "Uploading sample data to S3..."

    SAMPLE_DATA_PATH="$EXAMPLE_DIR/sample_data/sales_2024_11.csv"

    if [ -f "$SAMPLE_DATA_PATH" ]; then
        run_command "aws s3 cp '$SAMPLE_DATA_PATH' 's3://$S3_BUCKET/$S3_PREFIX'"
        log_success "Sample data uploaded to s3://$S3_BUCKET/$S3_PREFIX"
    else
        log_warning "Sample data file not found: $SAMPLE_DATA_PATH"
    fi
fi

###############################################################################
# Setup Snowflake Database and Schema
###############################################################################

if [ "$SKIP_SNOWFLAKE" = false ]; then
    log_info "Setting up Snowflake database and schemas..."

    SNOWFLAKE_SQL=$(cat <<EOF
-- Create database
CREATE DATABASE IF NOT EXISTS $SNOWFLAKE_DATABASE
COMMENT = 'Analytics database for sales data pipeline';

USE DATABASE $SNOWFLAKE_DATABASE;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS bronze
COMMENT = 'Bronze layer - Raw ingested data';

CREATE SCHEMA IF NOT EXISTS silver
COMMENT = 'Silver layer - Cleaned and transformed data';

CREATE SCHEMA IF NOT EXISTS gold
COMMENT = 'Gold layer - Business-level aggregations';

-- Create bronze table
CREATE TABLE IF NOT EXISTS bronze.sales_raw (
    sale_id VARCHAR(50),
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    sale_date VARCHAR(50),
    amount VARCHAR(50),
    quantity VARCHAR(50),
    load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    source_file VARCHAR(500)
)
COMMENT = 'Bronze layer - Raw sales data from CSV files';

-- Grant permissions
GRANT USAGE ON DATABASE $SNOWFLAKE_DATABASE TO ROLE $SNOWFLAKE_ROLE;
GRANT USAGE ON SCHEMA bronze TO ROLE $SNOWFLAKE_ROLE;
GRANT USAGE ON SCHEMA silver TO ROLE $SNOWFLAKE_ROLE;
GRANT ALL ON ALL TABLES IN SCHEMA bronze TO ROLE $SNOWFLAKE_ROLE;
GRANT ALL ON ALL TABLES IN SCHEMA silver TO ROLE $SNOWFLAKE_ROLE;
GRANT CREATE TABLE ON SCHEMA bronze TO ROLE $SNOWFLAKE_ROLE;
GRANT CREATE TABLE ON SCHEMA silver TO ROLE $SNOWFLAKE_ROLE;
EOF
)

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would execute Snowflake SQL setup"
        echo "$SNOWFLAKE_SQL"
    else
        echo "$SNOWFLAKE_SQL" | snowsql -a "$SNOWFLAKE_ACCOUNT" -u "$SNOWFLAKE_USER" -d "$SNOWFLAKE_DATABASE" --private-key-path ~/.ssh/snowflake_rsa_key.p8 2>/dev/null || \
        echo "$SNOWFLAKE_SQL" | snowsql -a "$SNOWFLAKE_ACCOUNT" -u "$SNOWFLAKE_USER" -d "$SNOWFLAKE_DATABASE" -o output_format=json
        log_success "Snowflake database and schemas created"
    fi
fi

###############################################################################
# Deploy Airflow DAG
###############################################################################

log_info "Deploying Airflow DAG..."

AIRFLOW_DAGS_DIR="${AIRFLOW_HOME:-/opt/airflow}/dags"
DAG_SOURCE="$EXAMPLE_DIR/airflow/sales_ingestion_dag.py"
DAG_DEST="$AIRFLOW_DAGS_DIR/sales_ingestion_dag.py"

if [ -f "$DAG_SOURCE" ]; then
    run_command "mkdir -p '$AIRFLOW_DAGS_DIR'"
    run_command "cp '$DAG_SOURCE' '$DAG_DEST'"
    log_success "DAG deployed to $DAG_DEST"
else
    log_warning "DAG file not found: $DAG_SOURCE"
fi

# Verify DAG syntax
if [ "$DRY_RUN" = false ]; then
    log_info "Validating DAG syntax..."
    python "$DAG_DEST" && log_success "DAG syntax is valid" || log_error "DAG syntax validation failed"
fi

###############################################################################
# Setup dbt Profile
###############################################################################

log_info "Setting up dbt profile..."

DBT_PROFILES_DIR="${HOME}/.dbt"
DBT_PROFILE_PATH="$DBT_PROFILES_DIR/profiles.yml"

run_command "mkdir -p '$DBT_PROFILES_DIR'"

if [ "$SKIP_SNOWFLAKE" = false ]; then
    DBT_PROFILE_CONTENT=$(cat <<EOF
sales_pipeline:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: $SNOWFLAKE_ACCOUNT
      user: $SNOWFLAKE_USER
      password: $SNOWFLAKE_PASSWORD
      role: $SNOWFLAKE_ROLE
      database: $SNOWFLAKE_DATABASE
      warehouse: $SNOWFLAKE_WAREHOUSE
      schema: silver
      threads: 4
      client_session_keep_alive: False
EOF
)

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would create dbt profile"
        echo "$DBT_PROFILE_CONTENT"
    else
        echo "$DBT_PROFILE_CONTENT" >> "$DBT_PROFILE_PATH"
        log_success "dbt profile configured at $DBT_PROFILE_PATH"
    fi
fi

###############################################################################
# Summary
###############################################################################

echo ""
log_success "========================================="
log_success "Setup Complete!"
log_success "========================================="
echo ""
log_info "Next steps:"
echo ""
echo "1. Trigger the Airflow DAG:"
echo "   airflow dags trigger sales_csv_to_snowflake"
echo ""
echo "2. Monitor the DAG in Airflow UI:"
echo "   http://localhost:8080"
echo ""
echo "3. Run dbt models manually (optional):"
echo "   dbt run --models sales_raw sales_clean"
echo "   dbt test --models sales_clean"
echo ""
echo "4. Query your data in Snowflake:"
echo "   SELECT * FROM $SNOWFLAKE_DATABASE.silver.sales_clean LIMIT 10;"
echo ""
log_info "Configuration Summary:"
echo "  S3 Bucket: $S3_BUCKET"
echo "  S3 Prefix: $S3_PREFIX"
echo "  Snowflake Database: $SNOWFLAKE_DATABASE"
echo "  Bronze Table: $SNOWFLAKE_DATABASE.bronze.sales_raw"
echo "  Silver Table: $SNOWFLAKE_DATABASE.silver.sales_clean"
echo ""
