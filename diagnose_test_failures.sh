#!/bin/bash
# Diagnose test failures and provide actionable fixes

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "(bot-dev-backend|bot_backend|backend)" | head -1)
if [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME="bot-dev-backend"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Failure Diagnostics${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Run a single failing test with verbose output to see the actual error
echo -e "${YELLOW}Running diagnostic on failing tests...${NC}"
echo ""

# Test 1: Execution Engine - approve_step
echo -e "${BLUE}1. Testing ExecutionEngine.approve_step...${NC}"
docker exec "$CONTAINER_NAME" pytest \
    tests/unit/services/test_execution_engine.py::TestApproveStep::test_approve_step_with_valid_session \
    -v -s --tb=long 2>&1 | head -50

echo ""
echo -e "${BLUE}2. Testing ExecutionEngine.start_execution...${NC}"
docker exec "$CONTAINER_NAME" pytest \
    tests/unit/services/test_execution_engine.py::TestStartExecution::test_start_execution_creates_steps \
    -v -s --tb=long 2>&1 | head -50

echo ""
echo -e "${BLUE}3. Testing RunbookGeneratorService...${NC}"
docker exec "$CONTAINER_NAME" pytest \
    tests/unit/services/test_runbook_generator.py::TestGenerateRunbook::test_generate_runbook_with_valid_description \
    -v -s --tb=long 2>&1 | head -50

echo ""
echo -e "${YELLOW}Checking ExecutionEngine implementation...${NC}"
docker exec "$CONTAINER_NAME" python -c "
from app.services.execution.execution_engine import ExecutionEngine
engine = ExecutionEngine()
print('ExecutionEngine attributes:')
print('  - session_service:', hasattr(engine, 'session_service'))
print('  - approval_service:', hasattr(engine, 'approval_service'))
print('  - step_execution_service:', hasattr(engine, 'step_execution_service'))
print('  - session_service type:', type(getattr(engine, 'session_service', None)))
print('  - approval_service type:', type(getattr(engine, 'approval_service', None)))
" 2>&1 || echo "Could not inspect ExecutionEngine"

echo ""
echo -e "${YELLOW}Checking RunbookGeneratorService implementation...${NC}"
docker exec "$CONTAINER_NAME" python -c "
from app.services.runbook.generation.runbook_generator_core import RunbookGeneratorService
service = RunbookGeneratorService()
print('RunbookGeneratorService attributes:')
print('  - vector_service:', hasattr(service, 'vector_service'))
print('  - content_builder:', hasattr(service, 'content_builder'))
print('  - yaml_pipeline:', hasattr(service, 'yaml_pipeline'))
" 2>&1 || echo "Could not inspect RunbookGeneratorService"

echo ""
echo -e "${GREEN}Diagnostics complete. Review the output above to identify the issues.${NC}"
