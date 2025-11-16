#!/bin/bash
# Quick start script for DataForge AI Platform

set -e

echo "🚀 DataForge AI Platform - Quick Start"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Step 1:${NC} Installing shared libraries..."
cd shared/common && pip install -e . > /dev/null 2>&1
echo -e "${GREEN}✓${NC} dataforge-common installed"

cd ../connectors && pip install -e . > /dev/null 2>&1
echo -e "${GREEN}✓${NC} dataforge-connectors installed"

cd ../ai-core && pip install -e . > /dev/null 2>&1
echo -e "${GREEN}✓${NC} dataforge-ai-core installed"

cd ../..

echo ""
echo -e "${BLUE}Step 2:${NC} Starting Docker services..."
echo "This may take a few minutes on first run..."
cd deployments/local
docker-compose up -d

echo ""
echo -e "${GREEN}✓${NC} Services started!"
echo ""
echo "Available services:"
echo "  - Airflow UI:     http://localhost:8080 (admin/admin)"
echo "  - Pipeline API:   http://localhost:8000"
echo "  - Prometheus:     http://localhost:9090"
echo "  - Grafana:        http://localhost:3001 (admin/admin)"
echo "  - PostgreSQL:     localhost:5432 (dataforge/dataforge)"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
echo -e "${GREEN}🎉 DataForge AI Platform is running!${NC}"
