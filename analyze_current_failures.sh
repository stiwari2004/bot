#!/bin/bash
# Analyze current test failures

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Auto-detect backend container
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "(bot-dev-backend|bot-prod-backend|bot_backend|backend)" | head -1)
if [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME="bot-dev-backend"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Analyzing Current Test Failures${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Using container: $CONTAINER_NAME${NC}"
echo ""

# Check if container is running
if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}Error: Backend container '$CONTAINER_NAME' is not running${NC}"
    exit 1
fi

echo -e "${YELLOW}Running E2E tests to identify failures...${NC}"
echo ""

# Run E2E tests and capture failures
OUTPUT_FILE="/tmp/e2e_failures_$$.txt"
docker exec -i -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
    tests/e2e/ \
    -v \
    --tb=short \
    --no-cov \
    -o cache_dir=/tmp/.pytest_cache \
    2>&1 | tee "$OUTPUT_FILE" || true

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Failed Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract failed test names
FAILED_TESTS=$(grep -E "FAILED.*\[.*\]" "$OUTPUT_FILE" | grep -v "ERROR" | grep -oP 'tests/[^:]+::[^:]+::[^:]+' | sort -u)

if [ -n "$FAILED_TESTS" ]; then
    FAILED_COUNT=$(echo "$FAILED_TESTS" | wc -l)
    echo -e "${RED}Found $FAILED_COUNT failed test(s):${NC}"
    echo ""
    echo "$FAILED_TESTS" | while IFS= read -r test_path; do
        echo -e "  ${RED}✗${NC} $test_path"
    done
else
    echo -e "${GREEN}No failed tests found!${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Error Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract error test names
ERROR_TESTS=$(grep -E "ERROR.*\[.*\]" "$OUTPUT_FILE" | grep -oP 'tests/[^:]+::[^:]+::[^:]+' | sort -u)

if [ -n "$ERROR_TESTS" ]; then
    ERROR_COUNT=$(echo "$ERROR_TESTS" | wc -l)
    echo -e "${RED}Found $ERROR_COUNT error test(s):${NC}"
    echo ""
    echo "$ERROR_TESTS" | while IFS= read -r test_path; do
        echo -e "  ${RED}✗${NC} $test_path"
    done
else
    echo -e "${GREEN}No error tests found!${NC}"
fi

echo ""
echo -e "${YELLOW}Full output saved to: $OUTPUT_FILE${NC}"
echo ""
echo -e "${BLUE}To see detailed error for a specific test:${NC}"
echo "  docker exec -i -e PYTEST_CACHE_DIR=/tmp/.pytest_cache $CONTAINER_NAME pytest <test_path> -vv --tb=long --no-cov"
