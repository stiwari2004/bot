#!/bin/bash
# Comprehensive Test Runner Script for Linux Server
# This script runs all tests and provides detailed output

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.dev.yml"
TEST_OUTPUT_DIR="./test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Auto-detect backend container name (handles different naming conventions)
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "(bot-dev-backend|bot_backend|backend)" | head -1)
if [ -z "$CONTAINER_NAME" ]; then
    # Fallback: try to find any container with "backend" in the name
    CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -i backend | head -1)
    if [ -z "$CONTAINER_NAME" ]; then
        CONTAINER_NAME="bot-dev-backend"  # Default fallback
        echo -e "${YELLOW}Warning: Could not auto-detect container name, using default: $CONTAINER_NAME${NC}"
        echo -e "${YELLOW}If this is wrong, set CONTAINER_NAME environment variable before running script${NC}"
    fi
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Comprehensive Test Suite Runner${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose not found${NC}"
    exit 1
fi

echo -e "${GREEN}Using container: $CONTAINER_NAME${NC}"
echo ""

# Check if backend container is running (using docker ps directly to avoid compose issues)
if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}Warning: Backend container not running. Attempting to start services...${NC}"
    
    # Try to start services, but don't fail if ContainerConfig error occurs
    if docker-compose -f "$COMPOSE_FILE" up -d backend postgres redis 2>&1 | grep -q "ContainerConfig"; then
        echo -e "${YELLOW}ContainerConfig error detected. This is a Docker Compose metadata issue.${NC}"
        echo -e "${YELLOW}Checking if containers are actually running...${NC}"
        
        # Re-detect container name in case it's different
        CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "(bot-dev-backend|bot_backend|backend)" | head -1)
        if [ -z "$CONTAINER_NAME" ]; then
            CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -i backend | head -1)
        fi
        
        # Check if containers are actually running despite the error
        if [ -n "$CONTAINER_NAME" ] && docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
            echo -e "${GREEN}Found running container: $CONTAINER_NAME${NC}"
            echo -e "${GREEN}Containers are running despite the error. Continuing with tests...${NC}"
        else
            echo -e "${RED}Containers are not running. Please fix the ContainerConfig issue:${NC}"
            echo -e "${YELLOW}  Option 1: Restart Docker daemon: sudo systemctl restart docker${NC}"
            echo -e "${YELLOW}  Option 2: Remove orphaned containers: docker-compose -f $COMPOSE_FILE down --remove-orphans${NC}"
            echo -e "${YELLOW}  Option 3: Remove and recreate: docker-compose -f $COMPOSE_FILE down && docker-compose -f $COMPOSE_FILE up -d${NC}"
            exit 1
        fi
    else
        echo "Waiting for services to be ready..."
        sleep 10
    fi
else
    echo -e "${GREEN}Backend container is already running.${NC}"
fi

# Create test results directory
mkdir -p "$TEST_OUTPUT_DIR"

echo -e "${GREEN}Running test suite...${NC}"
echo ""

# Function to run tests with different verbosity levels
run_test_suite() {
    local test_type=$1
    local test_path=$2
    local output_file="$TEST_OUTPUT_DIR/${test_type}_${TIMESTAMP}.txt"
    
    echo -e "${YELLOW}Running $test_type tests...${NC}"
    
    # Use docker exec directly to avoid ContainerConfig issues
    docker exec -i "$CONTAINER_NAME" pytest \
        "$test_path" \
        -v \
        --no-cov \
        --tb=short \
        --maxfail=10 \
        2>&1 | tee "$output_file"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ $test_type tests PASSED${NC}"
        return 0
    else
        echo -e "${RED}✗ $test_type tests FAILED (exit code: $exit_code)${NC}"
        return $exit_code
    fi
}

# Run all tests
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Running ALL Tests${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

FULL_OUTPUT="$TEST_OUTPUT_DIR/full_test_run_${TIMESTAMP}.txt"

# Verify backend container is accessible
if ! docker exec "$CONTAINER_NAME" echo "Container check" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot access backend container '$CONTAINER_NAME'${NC}"
    echo -e "${YELLOW}Please ensure the container is running: docker ps | grep $CONTAINER_NAME${NC}"
    exit 1
fi

# Use docker exec directly instead of docker-compose exec to avoid ContainerConfig issues
docker exec -i "$CONTAINER_NAME" pytest \
    tests/ \
    -v \
    --no-cov \
    --tb=line \
    --maxfail=100 \
    2>&1 | tee "$FULL_OUTPUT"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}========================================${NC}"

# Extract summary from output
if grep -q "passed\|failed\|error" "$FULL_OUTPUT"; then
    echo ""
    grep -E "passed|failed|error" "$FULL_OUTPUT" | tail -1
    echo ""
fi

# Generate detailed report
REPORT_FILE="$TEST_OUTPUT_DIR/test_report_${TIMESTAMP}.txt"
echo "Test Run Report - $(date)" > "$REPORT_FILE"
echo "========================================" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Count passed/failed
PASSED=$(grep -oP '\d+(?= passed)' "$FULL_OUTPUT" | tail -1 || echo "0")
FAILED=$(grep -oP '\d+(?= failed)' "$FULL_OUTPUT" | tail -1 || echo "0")
ERRORS=$(grep -oP '\d+(?= error)' "$FULL_OUTPUT" | tail -1 || echo "0")

echo "Total Tests Passed: $PASSED" >> "$REPORT_FILE"
echo "Total Tests Failed: $FAILED" >> "$REPORT_FILE"
echo "Total Errors: $ERRORS" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# List failed tests
if [ "$FAILED" != "0" ] || [ "$ERRORS" != "0" ]; then
    echo "Failed Tests:" >> "$REPORT_FILE"
    echo "------------" >> "$REPORT_FILE"
    grep "FAILED\|ERROR" "$FULL_OUTPUT" >> "$REPORT_FILE" || echo "No failed tests found in output" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
fi

# Display report
cat "$REPORT_FILE"

echo ""
echo -e "${GREEN}Test results saved to:${NC}"
echo "  - Full output: $FULL_OUTPUT"
echo "  - Report: $REPORT_FILE"
echo ""

# Exit with test suite exit code
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check the output files for details.${NC}"
    exit $EXIT_CODE
fi
