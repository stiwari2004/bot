# Quick Test Verification Guide

## ✅ Successfully Fixed Tests

The following test is now **PASSING**:
- `tests/unit/test_execution_controller.py::TestCreateExecutionSession::test_create_session_with_valid_runbook`

## 🧪 Verify All Fixed Tests

Run this command to test all the fixed tests:

```bash
# Test Execution Controller
docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache bot-dev-backend pytest \
    tests/unit/test_execution_controller.py::TestCreateExecutionSession \
    -v --tb=short --no-cov -o cache_dir=/tmp/.pytest_cache

# Test Execution Engine - Approve Step
docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache bot-dev-backend pytest \
    tests/unit/services/test_execution_engine.py::TestApproveStep \
    -v --tb=short --no-cov -o cache_dir=/tmp/.pytest_cache

# Test Execution Engine - Start Execution
docker exec -i -e COVERAGE_FILE=/tmp/coverage/.coverage -e PYTEST_CACHE_DIR=/tmp/.pytest_cache bot-dev-backend pytest \
    tests/unit/services/test_execution_engine.py::TestStartExecution \
    -v --tb=short --no-cov -o cache_dir=/tmp/.pytest_cache
```

Or use the provided script:
```bash
chmod +x test_fixed_tests.sh
./test_fixed_tests.sh
```

## 📊 Expected Results

After running the above commands, you should see:
- ✅ `test_create_session_with_valid_runbook` - PASSED
- ✅ `test_approve_step_with_valid_session` - Should PASS
- ✅ `test_approve_step_rejects_step` - Should PASS
- ✅ `test_start_execution_creates_steps` - Should PASS
- ✅ `test_start_execution_with_already_running_session` - Should PASS

## ⚠️ Note on Warnings

The warnings about `.pytest_cache` permissions are expected and harmless. The tests will still pass. The cache is being written to `/tmp/.pytest_cache` instead.

## 🎯 Next Steps

Once all fixed tests pass:
1. Continue fixing remaining unit test failures (21 remaining)
2. Fix E2E/Integration setup errors (74 remaining)
3. Re-run full test suite to verify overall progress
