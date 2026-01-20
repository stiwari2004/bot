#!/bin/bash
# Quick test for ticket analysis to see actual errors

docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache bot-dev-backend pytest \
    tests/unit/services/test_ticket_analysis.py::TestAnalyzeTicket::test_analyze_ticket_with_true_positive \
    -v -s --tb=long --no-cov -o cache_dir=/tmp/.pytest_cache 2>&1 | tail -50
