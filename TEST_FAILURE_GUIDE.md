# Test Failure Analysis & Fix Guide

## Current Status
- **Tests Passed**: 81
- **Tests Failed**: 27
- **Errors**: 74 (mostly setup errors in E2E/Integration tests)

## Common Issues & Fixes

### 1. Unit Test Failures (27 failures)

#### Execution Engine Tests (4 failures)
**Files**: `test_execution_engine.py`

**Likely Issues**:
- Mock setup doesn't match actual service initialization
- Service attributes may not be accessible as expected
- Async method signatures may have changed

**Fix Approach**:
1. Check if `ExecutionEngine` services are initialized correctly
2. Verify mock patches match actual service names
3. Ensure async/await is handled correctly

#### Runbook Generator Tests (2 failures)
**Files**: `test_runbook_generator.py`

**Likely Issues**:
- Missing service dependencies
- Mock setup incomplete
- YAML pipeline dependencies not properly mocked

**Fix Approach**:
1. Verify all service dependencies are initialized
2. Check mock patches cover all dependencies
3. Ensure return values match expected types

### 2. Setup Errors (74 errors)

#### E2E Tests
**Files**: `tests/e2e/*.py`

**Common Causes**:
- Missing test database setup
- Missing fixtures
- Missing test data
- Database connection issues

**Fix Approach**:
1. Ensure test database exists: `test_troubleshooting_ai`
2. Check `conftest.py` fixtures are properly configured
3. Verify database migrations are run
4. Check for missing test data factories

#### Integration Tests
**Files**: `tests/integration/*.py`

**Common Causes**:
- TestClient not properly configured
- Missing authentication setup
- Database session issues
- Missing test data

**Fix Approach**:
1. Verify `conftest.py` has proper `client` fixture
2. Check authentication fixtures are set up
3. Ensure test database is properly isolated
4. Verify test data factories are working

## Quick Diagnostic Commands

### Check ExecutionEngine
```bash
docker exec bot-dev-backend python -c "
from app.services.execution.execution_engine import ExecutionEngine
engine = ExecutionEngine()
print('Services:', dir(engine))
"
```

### Check RunbookGeneratorService
```bash
docker exec bot-dev-backend python -c "
from app.services.runbook.generation.runbook_generator_core import RunbookGeneratorService
service = RunbookGeneratorService()
print('Services:', dir(service))
"
```

### Run Single Failing Test with Full Output
```bash
docker exec bot-dev-backend pytest \
    tests/unit/services/test_execution_engine.py::TestApproveStep::test_approve_step_with_valid_session \
    -v -s --tb=long
```

### Check Test Database
```bash
docker exec bot-dev-backend python -c "
from app.core.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
"
```

## Priority Fix Order

1. **Fix Unit Test Failures** (27 failures)
   - These are likely easier to fix (mock issues)
   - Will improve test reliability

2. **Fix Setup Errors** (74 errors)
   - Check conftest.py fixtures
   - Verify test database setup
   - Ensure all dependencies are available

3. **Verify Integration Tests**
   - Once setup errors are fixed, integration tests should work
   - May need test data factories

## Next Steps

1. Run diagnostic script: `./diagnose_test_failures.sh`
2. Review specific error messages from test output files
3. Fix mocks to match actual implementation
4. Fix conftest.py if fixtures are missing
5. Re-run tests to verify fixes
