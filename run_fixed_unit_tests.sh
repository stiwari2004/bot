#!/bin/bash
# Quick script to run all fixed unit tests
# Run this on the Linux server: bash run_fixed_unit_tests.sh

set -e

echo "=========================================="
echo "Running All Fixed Unit Tests"
echo "=========================================="
echo ""

# Set environment variables
export COVERAGE_FILE=/tmp/coverage/.coverage
export PYTEST_CACHE_DIR=/tmp/.pytest_cache

# Create directories
docker exec bot-dev-backend mkdir -p /tmp/.pytest_cache /tmp/coverage /tmp/htmlcov 2>/dev/null || true
docker exec bot-dev-backend chown -R appuser:appuser /tmp/.pytest_cache /tmp/coverage /tmp/htmlcov 2>/dev/null || true

# Run all fixed unit tests
echo "Running all fixed unit tests..."
echo ""

docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache bot-dev-backend pytest \
    tests/unit/test_execution_controller.py \
    tests/unit/services/test_execution_engine.py \
    tests/unit/services/test_runbook_generator.py \
    tests/unit/test_command_validator.py \
    tests/unit/services/test_ticket_analysis.py \
    tests/unit/test_runbook_validation.py \
    tests/unit/controllers/test_runbook_controller.py \
    -v --tb=short --no-cov -o cache_dir=/tmp/.pytest_cache

echo ""
echo "=========================================="
echo "All tests completed!"
echo "=========================================="
