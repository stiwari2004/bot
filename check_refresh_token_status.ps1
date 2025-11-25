# Check if refresh_token is present in the database
Write-Host "=== Checking Database for Refresh Token ===" -ForegroundColor Cyan

$query = @"
SELECT 
    id,
    tool_name,
    CASE 
        WHEN meta_data::json->>'refresh_token' IS NULL THEN 'NULL'
        WHEN meta_data::json->>'refresh_token' = 'null' THEN 'null string'
        WHEN meta_data::json->>'refresh_token' = '' THEN 'empty'
        ELSE 'PRESENT'
    END as refresh_token_status,
    CASE 
        WHEN meta_data::json->>'access_token' IS NULL THEN 'NO'
        WHEN meta_data::json->>'access_token' = 'null' THEN 'NO'
        ELSE 'YES'
    END as has_access_token,
    LENGTH(meta_data::json->>'refresh_token') as refresh_token_length
FROM ticketing_tool_connections 
WHERE id = 7;
"@

Write-Host "`nQuerying database..." -ForegroundColor Yellow
$result = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c $query 2>&1

Write-Host $result

Write-Host "`n=== Checking Recent Backend Logs ===" -ForegroundColor Cyan
Write-Host "Looking for refresh_token related messages in last 100 lines..." -ForegroundColor Yellow

$logs = docker-compose logs backend --tail 100 2>&1
$relevantLogs = $logs | Select-String -Pattern "refresh_token|Zoho token response keys|OAuth authorization successful|Token exchange successful|refresh_token saved" -CaseSensitive:$false

if ($relevantLogs) {
    Write-Host "`nFound relevant log entries:" -ForegroundColor Green
    $relevantLogs | ForEach-Object { Write-Host $_ -ForegroundColor White }
} else {
    Write-Host "`nNo relevant log entries found in last 100 lines." -ForegroundColor Yellow
    Write-Host "Try checking more lines with: docker-compose logs backend --tail 500" -ForegroundColor Yellow
}



