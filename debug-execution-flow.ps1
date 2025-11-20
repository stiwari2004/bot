# Debug Execution Flow Script
# Checks each component of the execution flow

Write-Host "=== EXECUTION FLOW DEBUG ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check if session exists
Write-Host "1. Checking execution session 12..." -ForegroundColor Yellow
$sessionQuery = @"
SELECT id, status, waiting_for_approval, approval_step_number, current_step, runbook_id, ticket_id
FROM execution_sessions
WHERE id = 12;
"@

docker exec bot-postgres-1 psql -U postgres -d aiops -c $sessionQuery

Write-Host ""
Write-Host "2. Checking steps for session 12..." -ForegroundColor Yellow
$stepsQuery = @"
SELECT step_number, step_type, requires_approval, approved, completed, success, command
FROM execution_steps
WHERE session_id = 12
ORDER BY step_number;
"@

docker exec bot-postgres-1 psql -U postgres -d aiops -c $stepsQuery

Write-Host ""
Write-Host "3. Checking backend logs for execution activity..." -ForegroundColor Yellow
docker-compose logs backend --tail 50 | Select-String -Pattern "session.*12|EXECUTE_STEP|approve|start_execution" -Context 1

Write-Host ""
Write-Host "4. Checking if approval endpoint exists..." -ForegroundColor Yellow
$approvalEndpoint = "http://localhost:8000/api/v1/agent/12/approve-step"
Write-Host "Endpoint: $approvalEndpoint"
Write-Host "Try: POST $approvalEndpoint with body: {`"step_number`": 1, `"approve`": true}"

Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Cyan
Write-Host "If session status is 'waiting_approval' and step 1 requires_approval=true and approved=null:"
Write-Host "  → Step needs to be approved first"
Write-Host "  → Call approval endpoint to approve step 1"
Write-Host "  → After approval, _execute_step should be called automatically"
Write-Host ""




