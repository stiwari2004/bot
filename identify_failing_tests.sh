#!/bin/bash
# Script to identify and diagnose the 5 failing tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CONTAINER_NAME="bot-dev-backend"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Identifying Failing Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create directories
docker exec "$CONTAINER_NAME" mkdir -p /tmp/.pytest_cache /tmp/coverage 2>/dev/null || true

# Run all tests and capture failures
echo -e "${YELLOW}Running all tests to identify failures...${NC}"
echo ""

FAILURES_OUTPUT="/tmp/test_failures_$(date +%Y%m%d_%H%M%S).txt"

docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
    tests/ \
    -v \
    --tb=short \
    --no-cov \
    -o cache_dir=/tmp/.pytest_cache \
    --maxfail=100 \
    2>&1 | tee "$FAILURES_OUTPUT"

# Extract failed tests
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Failed Tests Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract FAILED tests (not errors)
FAILED_TESTS=$(grep -E "FAILED|FAILED \[.*\]" "$FAILURES_OUTPUT" | grep -v "ERROR" | head -10)

if [ -z "$FAILED_TESTS" ]; then
    echo -e "${GREEN}No failed tests found (only errors)${NC}"
else
    echo -e "${RED}Failed Tests:${NC}"
    echo "$FAILED_TESTS" | while IFS= read -r line; do
        echo "  - $line"
    done
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Error Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract ERROR tests
ERROR_TESTS=$(grep -E "ERROR|ERROR \[.*\]" "$FAILURES_OUTPUT" | head -20)

if [ -z "$ERROR_TESTS" ]; then
    echo -e "${GREEN}No error tests found${NC}"
else
    echo -e "${RED}Error Tests (first 20):${NC}"
    echo "$ERROR_TESTS" | while IFS= read -r line; do
        echo "  - $line"
    done
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary Statistics${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract summary line
SUMMARY=$(grep -E "passed.*failed.*error|passed.*failed" "$FAILURES_OUTPUT" | tail -1)
if [ -n "$SUMMARY" ]; then
    echo "$SUMMARY"
fi

echo ""
echo -e "${YELLOW}Full output saved to: $FAILURES_OUTPUT${NC}"
echo ""
echo -e "${BLUE}To see detailed failure information:${NC}"
echo "  docker exec $CONTAINER_NAME cat $FAILURES_OUTPUT | grep -A 20 'FAILED\|ERROR'"
echo ""
