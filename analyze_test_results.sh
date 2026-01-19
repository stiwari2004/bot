#!/bin/bash
# Analyze and extract test results from test plan execution

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TEST_OUTPUT_DIR="./test_results"
ANALYSIS_DIR="./test_analysis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Results Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Find the most recent test run
LATEST_RUN=$(ls -t "$TEST_OUTPUT_DIR"/*test_plan_report*.txt 2>/dev/null | head -1)

if [ -z "$LATEST_RUN" ]; then
    echo -e "${RED}No test results found in $TEST_OUTPUT_DIR${NC}"
    exit 1
fi

TIMESTAMP_PATTERN=$(basename "$LATEST_RUN" | grep -oP '\d{8}_\d{6}' | head -1)
echo -e "${GREEN}Analyzing test run: $TIMESTAMP_PATTERN${NC}"
echo ""

# Create analysis directory
mkdir -p "$ANALYSIS_DIR"

# Extract summary from report
SUMMARY_FILE="$ANALYSIS_DIR/summary_${TIMESTAMP_PATTERN}.txt"
echo "Test Run Summary - $(date)" > "$SUMMARY_FILE"
echo "========================================" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
cat "$LATEST_RUN" >> "$SUMMARY_FILE"

# Extract all failed tests
FAILED_TESTS_FILE="$ANALYSIS_DIR/failed_tests_${TIMESTAMP_PATTERN}.txt"
echo "Failed Tests Analysis" > "$FAILED_TESTS_FILE"
echo "========================================" >> "$FAILED_TESTS_FILE"
echo "" >> "$FAILED_TESTS_FILE"

for result_file in "$TEST_OUTPUT_DIR"/*${TIMESTAMP_PATTERN}*.txt; do
    if [ -f "$result_file" ] && [ "$(basename "$result_file")" != "test_plan_report_${TIMESTAMP_PATTERN}.txt" ]; then
        filename=$(basename "$result_file")
        echo "=== $filename ===" >> "$FAILED_TESTS_FILE"
        
        # Extract failed tests
        grep -E "FAILED|ERROR" "$result_file" | head -20 >> "$FAILED_TESTS_FILE" || echo "No failures found" >> "$FAILED_TESTS_FILE"
        echo "" >> "$FAILED_TESTS_FILE"
    fi
done

# Extract all errors
ERRORS_FILE="$ANALYSIS_DIR/errors_${TIMESTAMP_PATTERN}.txt"
echo "Error Analysis" > "$ERRORS_FILE"
echo "========================================" >> "$ERRORS_FILE"
echo "" >> "$ERRORS_FILE"

for result_file in "$TEST_OUTPUT_DIR"/*${TIMESTAMP_PATTERN}*.txt; do
    if [ -f "$result_file" ] && [ "$(basename "$result_file")" != "test_plan_report_${TIMESTAMP_PATTERN}.txt" ]; then
        filename=$(basename "$result_file")
        echo "=== $filename ===" >> "$ERRORS_FILE"
        
        # Extract ERROR lines with context
        grep -B 2 -A 5 "ERROR" "$result_file" | head -50 >> "$ERRORS_FILE" || echo "No errors found" >> "$ERRORS_FILE"
        echo "" >> "$ERRORS_FILE"
    fi
done

# Create detailed breakdown by phase
BREAKDOWN_FILE="$ANALYSIS_DIR/breakdown_${TIMESTAMP_PATTERN}.txt"
echo "Test Breakdown by Phase" > "$BREAKDOWN_FILE"
echo "========================================" >> "$BREAKDOWN_FILE"
echo "" >> "$BREAKDOWN_FILE"

for phase in phase1 phase2 phase3 phase4; do
    echo "=== $phase ===" >> "$BREAKDOWN_FILE"
    for result_file in "$TEST_OUTPUT_DIR"/${phase}_*${TIMESTAMP_PATTERN}*.txt; do
        if [ -f "$result_file" ]; then
            filename=$(basename "$result_file")
            echo "  $filename:" >> "$BREAKDOWN_FILE"
            
            PASSED=$(grep -oP '\d+(?= passed)' "$result_file" | tail -1 || echo "0")
            FAILED=$(grep -oP '\d+(?= failed)' "$result_file" | tail -1 || echo "0")
            ERROR=$(grep -oP '\d+(?= error)' "$result_file" | tail -1 || echo "0")
            
            echo "    Passed: $PASSED" >> "$BREAKDOWN_FILE"
            echo "    Failed: $FAILED" >> "$BREAKDOWN_FILE"
            echo "    Errors: $ERROR" >> "$BREAKDOWN_FILE"
            echo "" >> "$BREAKDOWN_FILE"
        fi
    done
done

# Extract coverage information if available
COVERAGE_FILE="$TEST_OUTPUT_DIR/coverage_report_${TIMESTAMP_PATTERN}.txt"
if [ -f "$COVERAGE_FILE" ]; then
    COVERAGE_SUMMARY="$ANALYSIS_DIR/coverage_summary_${TIMESTAMP_PATTERN}.txt"
    echo "Coverage Summary" > "$COVERAGE_SUMMARY"
    echo "========================================" >> "$COVERAGE_SUMMARY"
    echo "" >> "$COVERAGE_SUMMARY"
    
    # Extract coverage table
    grep -A 100 "TOTAL" "$COVERAGE_FILE" | head -50 >> "$COVERAGE_SUMMARY" || echo "Coverage data not found" >> "$COVERAGE_SUMMARY"
fi

# Create HTML report
HTML_REPORT="$ANALYSIS_DIR/report_${TIMESTAMP_PATTERN}.html"
cat > "$HTML_REPORT" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Test Results Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #ccc; padding-bottom: 5px; }
        .summary { background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .passed { color: green; }
        .failed { color: red; }
        .error { color: orange; }
        pre { background: #f0f0f0; padding: 10px; border-radius: 5px; overflow-x: auto; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>Test Results Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <pre>
EOF

cat "$SUMMARY_FILE" >> "$HTML_REPORT"

cat >> "$HTML_REPORT" << 'EOF'
        </pre>
    </div>
    
    <h2>Failed Tests</h2>
    <pre>
EOF

cat "$FAILED_TESTS_FILE" >> "$HTML_REPORT"

cat >> "$HTML_REPORT" << 'EOF'
    </pre>
    
    <h2>Errors</h2>
    <pre>
EOF

head -100 "$ERRORS_FILE" >> "$HTML_REPORT"

cat >> "$HTML_REPORT" << 'EOF'
    </pre>
</body>
</html>
EOF

# Display summary
echo -e "${GREEN}Analysis Complete!${NC}"
echo ""
echo -e "${BLUE}Generated Files:${NC}"
echo "  - Summary: $SUMMARY_FILE"
echo "  - Failed Tests: $FAILED_TESTS_FILE"
echo "  - Errors: $ERRORS_FILE"
echo "  - Breakdown: $BREAKDOWN_FILE"
[ -f "$COVERAGE_SUMMARY" ] && echo "  - Coverage: $COVERAGE_SUMMARY"
echo "  - HTML Report: $HTML_REPORT"
echo ""

# Show quick summary
echo -e "${BLUE}Quick Summary:${NC}"
cat "$SUMMARY_FILE" | grep -E "Tests Passed|Tests Failed|Errors|Coverage" || true
echo ""

# Show top failures
echo -e "${YELLOW}Top 10 Failed Tests:${NC}"
grep -E "FAILED" "$FAILED_TESTS_FILE" | head -10 || echo "No failures found"
echo ""

echo -e "${GREEN}Open $HTML_REPORT in your browser for a detailed view${NC}"
