#!/bin/bash
# Script to diagnose the 5 specific failing tests (not errors)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CONTAINER_NAME="bot-dev-backend"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Diagnosing 5 Failing Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create directories
docker exec "$CONTAINER_NAME" mkdir -p /tmp/.pytest_cache /tmp/coverage 2>/dev/null || true

# Run all tests and extract only FAILED (not ERROR) tests
echo -e "${YELLOW}Running tests to identify failures...${NC}"
echo ""

TEMP_OUTPUT="/tmp/test_output_$(date +%Y%m%d_%H%M%S).txt"

docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
    tests/ \
    -v \
    --tb=line \
    --no-cov \
    -o cache_dir=/tmp/.pytest_cache \
    --maxfail=100 \
    2>&1 | tee "$TEMP_OUTPUT"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Extracting Failed Test Names${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract test names that FAILED (not ERROR)
FAILED_TEST_NAMES=$(grep -E "FAILED.*\[.*\]" "$TEMP_OUTPUT" | grep -v "ERROR" | sed 's/.*::\(.*\)::.*/\1/' | sort -u | head -10)

if [ -z "$FAILED_TEST_NAMES" ]; then
    # Try alternative pattern
    FAILED_TEST_NAMES=$(grep -E "FAILED" "$TEMP_OUTPUT" | grep -v "ERROR" | grep -oP 'tests/[^:]+::[^:]+::[^:]+' | sort -u | head -10)
fi

if [ -z "$FAILED_TEST_NAMES" ]; then
    echo -e "${YELLOW}No failed tests found in standard format. Checking full output...${NC}"
    echo ""
    echo -e "${BLUE}Full test summary:${NC}"
    grep -E "passed|failed|error" "$TEMP_OUTPUT" | tail -5
    echo ""
    echo -e "${YELLOW}Showing last 50 lines of output:${NC}"
    tail -50 "$TEMP_OUTPUT"
else
    echo -e "${RED}Found Failed Tests:${NC}"
    echo "$FAILED_TEST_NAMES" | while IFS= read -r test_name; do
        echo "  - $test_name"
    done
    
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Running Failed Tests Individually${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # Get full test paths - extract from lines like "FAILED tests/path/to/test.py::TestClass::test_method"
    # Pattern: FAILED tests/unit/services/test_validation_services.py::TestRunbookQualityValidator::test_validate_with_valid_spec
    FULL_FAILED_PATHS=$(grep "^FAILED" "$TEMP_OUTPUT" | grep -v "ERROR" | awk '{print $2}' | grep "^tests/" | sort -u | head -10)
    
    if [ -z "$FULL_FAILED_PATHS" ]; then
        # Try alternative extraction method - look for test paths in FAILED lines
        FULL_FAILED_PATHS=$(grep "FAILED" "$TEMP_OUTPUT" | grep -v "ERROR" | grep -oE 'tests/[^[:space:]]+::[^[:space:]]+::[^[:space:]]+' | sort -u | head -10)
    fi
    
    if [ -n "$FULL_FAILED_PATHS" ]; then
        for test_path in $FULL_FAILED_PATHS; do
            echo -e "${YELLOW}Testing: $test_path${NC}"
            docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
                "$test_path" \
                -v \
                --tb=long \
                --no-cov \
                -o cache_dir=/tmp/.pytest_cache \
                2>&1 | tail -50
            echo ""
        done
    else
        echo -e "${YELLOW}Could not extract test paths. Showing relevant lines from output:${NC}"
        grep -B 2 -A 5 "FAILED" "$TEMP_OUTPUT" | grep -v "ERROR" | head -30
    fi
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract final summary
FINAL_SUMMARY=$(grep -E "passed.*failed.*error|passed.*failed" "$TEMP_OUTPUT" | tail -1)
if [ -n "$FINAL_SUMMARY" ]; then
    echo "$FINAL_SUMMARY"
fi

echo ""
echo -e "${YELLOW}Full output saved to: $TEMP_OUTPUT${NC}"
echo ""
