#!/bin/bash
# Comprehensive Test Plan Runner
# Based on TEST_COVERAGE_PLAN.md and TEST_IMPLEMENTATION_SUMMARY.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.dev.yml"
TEST_OUTPUT_DIR="./test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COVERAGE_THRESHOLD=70

# Auto-detect backend container name
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "(bot-dev-backend|bot_backend|backend)" | head -1)
if [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -i backend | head -1)
    if [ -z "$CONTAINER_NAME" ]; then
        CONTAINER_NAME="bot-dev-backend"
        echo -e "${YELLOW}Warning: Using default container name: $CONTAINER_NAME${NC}"
    fi
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Comprehensive Test Plan Runner${NC}"
echo -e "${BLUE}Based on TEST_COVERAGE_PLAN.md${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Using container: $CONTAINER_NAME${NC}"
echo ""

# Check if backend container is running
if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}Error: Backend container '$CONTAINER_NAME' is not running${NC}"
    echo -e "${YELLOW}Please start the dev environment: docker-compose -f $COMPOSE_FILE up -d${NC}"
    exit 1
fi

# Fix permissions for coverage files and pytest cache (run as root temporarily)
echo -e "${YELLOW}Fixing permissions for test files...${NC}"
docker exec "$CONTAINER_NAME" bash -c "mkdir -p /tmp/coverage /tmp/htmlcov /tmp/.pytest_cache && chmod 777 /tmp/coverage /tmp/htmlcov /tmp/.pytest_cache" 2>/dev/null || true
docker exec "$CONTAINER_NAME" bash -c "rm -f /app/.coverage /tmp/.coverage 2>/dev/null || true" 2>/dev/null || true

# Create test results directory
mkdir -p "$TEST_OUTPUT_DIR"

# Function to run test category
run_test_category() {
    local category=$1
    local test_path=$2
    local description=$3
    local output_file="$TEST_OUTPUT_DIR/${category}_${TIMESTAMP}.txt"
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$description${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # Create writable directory for coverage files and fix permissions
    docker exec "$CONTAINER_NAME" bash -c "mkdir -p /tmp/coverage && chmod 777 /tmp/coverage" 2>/dev/null || true
    
    # Set coverage data file to writable location
    export COVERAGE_FILE=/tmp/coverage/.coverage
    
    docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
        "$test_path" \
        -v \
        --tb=short \
        --maxfail=10 \
        --no-cov \
        -o cache_dir=/tmp/.pytest_cache \
        2>&1 | tee "$output_file"
    
    local exit_code=${PIPESTATUS[0]}
    
    # Extract summary
    PASSED=$(grep -oP '\d+(?= passed)' "$output_file" | tail -1 || echo "0")
    FAILED=$(grep -oP '\d+(?= failed)' "$output_file" | tail -1 || echo "0")
    ERROR=$(grep -oP '\d+(?= error)' "$output_file" | tail -1 || echo "0")
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ $description: $PASSED passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $description: $FAILED failed, $ERROR errors${NC}"
        return $exit_code
    fi
}

# Function to run with coverage
run_with_coverage() {
    local category=$1
    local test_path=$2
    local description=$3
    local output_file="$TEST_OUTPUT_DIR/${category}_coverage_${TIMESTAMP}.txt"
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$description (with coverage)${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # Create writable directory for coverage files
    docker exec "$CONTAINER_NAME" bash -c "mkdir -p /tmp/coverage /tmp/htmlcov && chmod 777 /tmp/coverage /tmp/htmlcov" 2>/dev/null || true
    
    docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage "$CONTAINER_NAME" pytest \
        "$test_path" \
        -v \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html:/tmp/htmlcov/${category} \
        --tb=short \
        2>&1 | tee "$output_file"
    
    return ${PIPESTATUS[0]}
}

# Start test execution
echo -e "${GREEN}Starting comprehensive test plan execution...${NC}"
echo ""

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_ERRORS=0

# Phase 0: Fixed Unit Tests (All Recently Fixed Tests)
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}PHASE 0: Fixed Unit Tests${NC}"
echo -e "${GREEN}Running all recently fixed unit tests${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

echo -e "${BLUE}Running all fixed unit tests together...${NC}"
FIXED_TESTS_OUTPUT="$TEST_OUTPUT_DIR/fixed_unit_tests_${TIMESTAMP}.txt"

docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
    tests/unit/test_execution_controller.py \
    tests/unit/services/test_execution_engine.py \
    tests/unit/services/test_runbook_generator.py \
    tests/unit/test_command_validator.py \
    tests/unit/services/test_ticket_analysis.py \
    tests/unit/test_runbook_validation.py \
    tests/unit/controllers/test_runbook_controller.py \
    -v \
    --tb=short \
    --no-cov \
    -o cache_dir=/tmp/.pytest_cache \
    2>&1 | tee "$FIXED_TESTS_OUTPUT"

FIXED_EXIT=${PIPESTATUS[0]}

# Extract summary from fixed tests
FIXED_PASSED=$(grep -oP '\d+(?= passed)' "$FIXED_TESTS_OUTPUT" | tail -1 || echo "0")
FIXED_FAILED=$(grep -oP '\d+(?= failed)' "$FIXED_TESTS_OUTPUT" | tail -1 || echo "0")
FIXED_ERRORS=$(grep -oP '\d+(?= error)' "$FIXED_TESTS_OUTPUT" | tail -1 || echo "0")

echo ""
if [ $FIXED_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓ Fixed Unit Tests: $FIXED_PASSED passed, $FIXED_FAILED failed, $FIXED_ERRORS errors${NC}"
else
    echo -e "${RED}✗ Fixed Unit Tests: $FIXED_PASSED passed, $FIXED_FAILED failed, $FIXED_ERRORS errors${NC}"
    echo -e "${YELLOW}Check $FIXED_TESTS_OUTPUT for details${NC}"
fi
echo ""

# Phase 1: Foundation Tests (Unit Tests - Services)
echo -e "${YELLOW}PHASE 1: Foundation Tests (Unit Tests - Services)${NC}"
echo ""

run_test_category "phase1_auth" "tests/unit/services/test_auth.py" "Authentication Service Tests" || true
run_test_category "phase1_websocket" "tests/unit/services/test_websocket_manager.py" "WebSocket Manager Tests" || true
run_test_category "phase1_execution" "tests/unit/services/test_execution_engine.py" "Execution Engine Tests" || true
run_test_category "phase1_runbook" "tests/unit/services/test_runbook_generator.py" "Runbook Generator Tests" || true

# Phase 2: Additional Unit Tests
echo ""
echo -e "${YELLOW}PHASE 2: Additional Unit Tests${NC}"
echo ""

run_test_category "phase2_ticket_analysis" "tests/unit/services/test_ticket_analysis.py" "Ticket Analysis Service Tests" || true
run_test_category "phase2_validation" "tests/unit/services/test_validation_services.py" "Validation Services Tests" || true
run_test_category "phase2_ticket_controller" "tests/unit/controllers/test_ticket_controller.py" "Ticket Controller Tests" || true
run_test_category "phase2_runbook_controller" "tests/unit/controllers/test_runbook_controller.py" "Runbook Controller Tests" || true
run_test_category "phase2_execution_controller" "tests/unit/test_execution_controller.py" "Execution Controller Tests" || true
run_test_category "phase2_command_validator" "tests/unit/test_command_validator.py" "Command Validator Tests" || true
run_test_category "phase2_runbook_validation" "tests/unit/test_runbook_validation.py" "Runbook Validation Tests" || true

# Phase 3: Integration Tests (API Endpoints)
echo ""
echo -e "${YELLOW}PHASE 3: Integration Tests (API Endpoints)${NC}"
echo ""

run_test_category "phase3_auth_endpoints" "tests/integration/test_auth_endpoints.py" "Authentication Endpoint Tests" || true
run_test_category "phase3_execution_endpoints" "tests/integration/test_execution_endpoints.py" "Execution Endpoint Tests" || true
run_test_category "phase3_runbook_endpoints" "tests/integration/test_runbook_endpoints.py" "Runbook Endpoint Tests" || true
run_test_category "phase3_ticket_endpoints" "tests/integration/test_ticket_endpoints.py" "Ticket Endpoint Tests" || true

# Phase 4: E2E Tests
echo ""
echo -e "${YELLOW}PHASE 4: E2E Tests${NC}"
echo ""

run_test_category "phase4_execution_workflow" "tests/e2e/test_execution_workflow.py" "Execution Workflow E2E Tests" || true
run_test_category "phase4_runbook_generation" "tests/e2e/test_runbook_generation_workflow.py" "Runbook Generation Workflow E2E Tests" || true
run_test_category "phase4_ticket_analysis" "tests/e2e/test_ticket_analysis_workflow.py" "Ticket Analysis Workflow E2E Tests" || true
run_test_category "phase4_multi_tenant" "tests/e2e/test_multi_tenant_isolation.py" "Multi-Tenant Isolation E2E Tests" || true
run_test_category "phase4_error_handling" "tests/e2e/test_error_handling.py" "Error Handling E2E Tests" || true

# Final: Overall Coverage Report
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Generating Overall Coverage Report${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

COVERAGE_OUTPUT="$TEST_OUTPUT_DIR/coverage_report_${TIMESTAMP}.txt"

# Create writable directory for coverage files
docker exec "$CONTAINER_NAME" bash -c "mkdir -p /tmp/coverage /tmp/htmlcov && chmod 777 /tmp/coverage /tmp/htmlcov" 2>/dev/null || true

docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache "$CONTAINER_NAME" pytest \
    tests/ \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:/tmp/htmlcov/full \
    --cov-fail-under=$COVERAGE_THRESHOLD \
    -o cache_dir=/tmp/.pytest_cache \
    -v \
    --tb=line \
    2>&1 | tee "$COVERAGE_OUTPUT"

COVERAGE_EXIT=${PIPESTATUS[0]}

# Extract final summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Plan Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract totals from coverage output
FINAL_PASSED=$(grep -oP '\d+(?= passed)' "$COVERAGE_OUTPUT" | tail -1 || echo "0")
FINAL_FAILED=$(grep -oP '\d+(?= failed)' "$COVERAGE_OUTPUT" | tail -1 || echo "0")
FINAL_ERRORS=$(grep -oP '\d+(?= error)' "$COVERAGE_OUTPUT" | tail -1 || echo "0")

# Extract coverage percentage
COVERAGE_PCT=$(grep -oP 'TOTAL\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)%' "$COVERAGE_OUTPUT" | grep -oP '\d+%' | head -1 || echo "N/A")

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Final Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Fixed Unit Tests:${NC}"
echo -e "  Passed: $FIXED_PASSED"
echo -e "  Failed: $FIXED_FAILED"
echo -e "  Errors: $FIXED_ERRORS"
echo ""
echo -e "${GREEN}Overall Test Results:${NC}"
echo -e "  Total Passed: $FINAL_PASSED"
echo -e "  Total Failed: $FINAL_FAILED"
echo -e "  Total Errors: $FINAL_ERRORS"
echo -e "  Coverage: $COVERAGE_PCT"
echo ""

# Generate detailed report
REPORT_FILE="$TEST_OUTPUT_DIR/test_plan_report_${TIMESTAMP}.txt"
echo "Test Plan Execution Report - $(date)" > "$REPORT_FILE"
echo "========================================" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Container: $CONTAINER_NAME" >> "$REPORT_FILE"
echo "Timestamp: $TIMESTAMP" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Fixed Unit Tests Summary:" >> "$REPORT_FILE"
echo "  Tests Passed: $FIXED_PASSED" >> "$REPORT_FILE"
echo "  Tests Failed: $FIXED_FAILED" >> "$REPORT_FILE"
echo "  Errors: $FIXED_ERRORS" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Overall Summary:" >> "$REPORT_FILE"
echo "  Tests Passed: $FINAL_PASSED" >> "$REPORT_FILE"
echo "  Tests Failed: $FINAL_FAILED" >> "$REPORT_FILE"
echo "  Errors: $FINAL_ERRORS" >> "$REPORT_FILE"
echo "  Coverage: $COVERAGE_PCT" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# List all test result files
echo "Test Result Files:" >> "$REPORT_FILE"
echo "------------------" >> "$REPORT_FILE"
ls -lh "$TEST_OUTPUT_DIR"/*${TIMESTAMP}* 2>/dev/null | awk '{print $9, "(" $5 ")"}' >> "$REPORT_FILE" || echo "No result files found" >> "$REPORT_FILE"

cat "$REPORT_FILE"

echo ""
echo -e "${GREEN}Test results saved to:${NC}"
echo "  - Fixed unit tests: $FIXED_TESTS_OUTPUT"
echo "  - Coverage report: $COVERAGE_OUTPUT"
echo "  - Summary report: $REPORT_FILE"
echo "  - HTML coverage: htmlcov/full/index.html (in container)"
echo ""
echo -e "${YELLOW}To view fixed unit test details:${NC}"
echo "  cat $FIXED_TESTS_OUTPUT"
echo ""

# Extract failed test names for detailed report
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Failed Test Details${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Extract failed tests from coverage output
FAILED_TEST_PATHS=$(grep -E "FAILED.*\[.*\]" "$COVERAGE_OUTPUT" | grep -v "ERROR" | grep -oP 'tests/[^:]+::[^:]+::[^:]+' | sort -u | head -10)

if [ -n "$FAILED_TEST_PATHS" ]; then
    echo -e "${RED}Failed Tests (not errors):${NC}"
    echo "$FAILED_TEST_PATHS" | while IFS= read -r test_path; do
        echo "  - $test_path"
    done
    echo ""
    echo -e "${YELLOW}To diagnose failures, run:${NC}"
    echo "  bash diagnose_5_failures.sh"
    echo ""
fi

# Exit with appropriate code
if [ $COVERAGE_EXIT -eq 0 ] && [ "$FINAL_FAILED" = "0" ] && [ "$FINAL_ERRORS" = "0" ]; then
    echo -e "${GREEN}✓ All tests passed! Coverage target met.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed or coverage below threshold.${NC}"
    echo -e "${YELLOW}Check the output files for details.${NC}"
    echo ""
    echo -e "${YELLOW}To diagnose failures:${NC}"
    echo "  bash diagnose_5_failures.sh"
    echo ""
    exit 1
fi
