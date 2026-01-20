#!/bin/bash
# Diagnose Integration/E2E Test Errors

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Auto-detect backend container
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "(bot-dev-backend|bot_backend|backend)" | head -1)
if [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME="bot-dev-backend"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Diagnosing Integration/E2E Test Errors${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Using container: $CONTAINER_NAME${NC}"
echo ""

# Check if container is running
if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}Error: Backend container '$CONTAINER_NAME' is not running${NC}"
    exit 1
fi

# Create temp directory for output
TEMP_OUTPUT="/tmp/integration_errors_$$.txt"

echo -e "${YELLOW}Running integration tests to capture errors...${NC}"
echo ""

# Run integration tests and capture errors
docker exec -i -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
    tests/integration/ \
    -v \
    --tb=line \
    --no-cov \
    -o cache_dir=/tmp/.pytest_cache \
    --maxfail=5 \
    2>&1 | tee "$TEMP_OUTPUT" || true

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Error Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract error patterns
echo -e "${YELLOW}Common Error Patterns:${NC}"
echo ""

# Check for import errors
IMPORT_ERRORS=$(grep -c "ImportError\|ModuleNotFoundError" "$TEMP_OUTPUT" || echo "0")
if [ "$IMPORT_ERRORS" -gt 0 ]; then
    echo -e "${RED}Import Errors: $IMPORT_ERRORS${NC}"
    grep -A 2 "ImportError\|ModuleNotFoundError" "$TEMP_OUTPUT" | head -20
    echo ""
fi

# Check for fixture errors
FIXTURE_ERRORS=$(grep -c "fixture.*not found\|FixtureNotFoundError" "$TEMP_OUTPUT" || echo "0")
if [ "$FIXTURE_ERRORS" -gt 0 ]; then
    echo -e "${RED}Fixture Errors: $FIXTURE_ERRORS${NC}"
    grep -A 2 "fixture.*not found\|FixtureNotFoundError" "$TEMP_OUTPUT" | head -20
    echo ""
fi

# Check for database errors
DB_ERRORS=$(grep -c "OperationalError\|DatabaseError\|connection\|could not connect" "$TEMP_OUTPUT" || echo "0")
if [ "$DB_ERRORS" -gt 0 ]; then
    echo -e "${RED}Database Errors: $DB_ERRORS${NC}"
    grep -A 2 "OperationalError\|DatabaseError\|connection\|could not connect" "$TEMP_OUTPUT" | head -20
    echo ""
fi

# Check for attribute errors
ATTR_ERRORS=$(grep -c "AttributeError\|has no attribute" "$TEMP_OUTPUT" || echo "0")
if [ "$ATTR_ERRORS" -gt 0 ]; then
    echo -e "${RED}Attribute Errors: $ATTR_ERRORS${NC}"
    grep -A 2 "AttributeError\|has no attribute" "$TEMP_OUTPUT" | head -20
    echo ""
fi

# Show summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TOTAL_ERRORS=$(grep -c "ERROR\|Error\|FAILED" "$TEMP_OUTPUT" || echo "0")
echo -e "Total Errors Found: ${RED}$TOTAL_ERRORS${NC}"
echo ""

# Show first 10 unique error types
echo -e "${YELLOW}Top Error Types:${NC}"
grep -E "ERROR|Error|FAILED" "$TEMP_OUTPUT" | head -10 | sort | uniq -c | sort -rn | head -10

echo ""
echo -e "${YELLOW}Full error output saved to: $TEMP_OUTPUT${NC}"
echo ""
