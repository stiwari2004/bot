# Test Runner Script Documentation

## Overview
The `run_tests.sh` script provides a comprehensive way to run all tests on your Linux server with detailed output and reporting.

## Prerequisites
- Docker and Docker Compose installed
- Backend container running (script will attempt to start it if not running)
- Sufficient disk space for test output files

## Usage

### Basic Usage
```bash
./run_tests.sh
```

### What the Script Does
1. **Checks Environment**: Verifies Docker Compose is available and backend container is running
2. **Starts Services**: If needed, starts backend, postgres, and redis containers
3. **Runs All Tests**: Executes the complete test suite with verbose output
4. **Generates Reports**: Creates detailed test reports in `./test_results/` directory
5. **Provides Summary**: Shows pass/fail counts and lists failed tests

## Output Files

The script creates the following files in `./test_results/`:

- `full_test_run_YYYYMMDD_HHMMSS.txt` - Complete test output with all details
- `test_report_YYYYMMDD_HHMMSS.txt` - Summary report with pass/fail counts and failed test list

## Exit Codes

- `0` - All tests passed
- Non-zero - Some tests failed (exit code matches pytest exit code)

## Customization

You can modify the script to:
- Change test paths (e.g., run only unit tests)
- Adjust verbosity levels
- Change output directory
- Add email notifications
- Integrate with CI/CD pipelines

## Example Output

```
========================================
Comprehensive Test Suite Runner
========================================

Running test suite...

========================================
Running ALL Tests
========================================

[Test output...]

========================================
Test Summary
========================================

Total Tests Passed: 128
Total Tests Failed: 54
Total Errors: 0

Test results saved to:
  - Full output: ./test_results/full_test_run_20260115_143022.txt
  - Report: ./test_results/test_report_20260115_143022.txt
```

## Troubleshooting

### Container Not Running
If the script can't find the backend container, it will attempt to start services automatically. Wait 10 seconds for services to initialize.

### Permission Denied
Make sure the script is executable:
```bash
chmod +x run_tests.sh
```

### Out of Disk Space
The test output files can be large. Monitor disk space in the `test_results/` directory.

### Tests Hanging
If tests appear to hang, check:
- Database connectivity
- Redis connectivity
- Container resource limits
- Network connectivity

## Integration with CI/CD

You can integrate this script into your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: ./run_tests.sh
  
- name: Upload Test Results
  uses: actions/upload-artifact@v2
  with:
    name: test-results
    path: test_results/
```

## Next Steps

After running tests:
1. Review the test report for failed tests
2. Check individual test output files for detailed error messages
3. Fix failing tests
4. Re-run the script to verify fixes
