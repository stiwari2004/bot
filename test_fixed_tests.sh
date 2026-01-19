#!/bin/bash
# Test the fixed tests to verify they all pass

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONTAINER_NAME="bot-dev-backend"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing Fixed Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test Execution Controller tests
echo -e "${YELLOW}1. Testing Execution Controller...${NC}"
docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
    tests/unit/test_execution_controller.py::TestCreateExecutionSession \
    -v --tb=short --no-cov -o cache_dir=/tmp/.pytest_cache

echo ""
echo -e "${YELLOW}2. Testing Execution Engine...${NC}"
docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
    tests/unit/services/test_execution_engine.py::TestApproveStep \
    tests/unit/services/test_execution_engine.py::TestStartExecution \
    -v --tb=short --no-cov -o cache_dir=/tmp/.pytest_cache

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All fixed tests completed!${NC}"
echo -e "${GREEN}========================================${NC}"
