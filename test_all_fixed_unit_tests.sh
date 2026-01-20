#!/bin/bash
# Script to run all fixed unit tests to verify they pass
# This runs all the unit tests we've fixed in this session

set -e  # Exit on error

echo "=========================================="
echo "Running All Fixed Unit Tests"
echo "=========================================="
echo ""

# Set environment variables for pytest
export COVERAGE_FILE=/tmp/coverage/.coverage
export PYTEST_CACHE_DIR=/tmp/.pytest_cache

# Create necessary directories in container
docker exec bot-dev-backend mkdir -p /tmp/.pytest_cache /tmp/coverage /tmp/htmlcov || true
docker exec bot-dev-backend chown -R appuser:appuser /tmp/.pytest_cache /tmp/coverage /tmp/htmlcov || true

# Test files we've fixed
TEST_FILES=(
    "tests/unit/test_execution_controller.py"
    "tests/unit/services/test_execution_engine.py"
    "tests/unit/services/test_runbook_generator.py"
    "tests/unit/test_command_validator.py"
    "tests/unit/services/test_ticket_analysis.py"
    "tests/unit/test_runbook_validation.py"
    "tests/unit/controllers/test_runbook_controller.py"
)

echo "Running unit tests for fixed test files..."
echo ""

TOTAL_PASSED=0
TOTAL_FAILED=0
FAILED_TESTS=()

for test_file in "${TEST_FILES[@]}"; do
    echo "----------------------------------------"
    echo "Testing: $test_file"
    echo "----------------------------------------"
    
    if docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache bot-dev-backend pytest \
        "$test_file" \
        -v --tb=short --no-cov -o cache_dir=/tmp/.pytest_cache 2>&1 | tee /tmp/test_output.log; then
        echo "✅ PASSED: $test_file"
        PASSED=$(grep -c "passed" /tmp/test_output.log || echo "0")
        TOTAL_PASSED=$((TOTAL_PASSED + PASSED))
    else
        echo "❌ FAILED: $test_file"
        FAILED=$(grep -c "failed\|ERROR" /tmp/test_output.log || echo "0")
        TOTAL_FAILED=$((TOTAL_FAILED + FAILED))
        FAILED_TESTS+=("$test_file")
    fi
    echo ""
done

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Total test files: ${#TEST_FILES[@]}"
echo "Passed: $TOTAL_PASSED tests"
echo "Failed: $TOTAL_FAILED tests"

if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    echo ""
    echo "Failed test files:"
    for failed_test in "${FAILED_TESTS[@]}"; do
        echo "  - $failed_test"
    done
    echo ""
    exit 1
else
    echo ""
    echo "✅ All fixed unit tests passed!"
    echo ""
    exit 0
fi
