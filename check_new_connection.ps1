# Find the new ManageEngine connection and check for refresh_token
Write-Host "=== Finding ManageEngine Connection ===" -ForegroundColor Cyan

# Get all connections
Write-Host "`nAll ticketing connections:" -ForegroundColor Yellow
docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, tool_name, is_active, created_at FROM ticketing_tool_connections ORDER BY created_at DESC LIMIT 5;" 2>&1 | Select-String -Pattern "id|tool_name|manageengine" -CaseSensitive:$false

# Find ManageEngine connection ID
Write-Host "`n=== Checking ManageEngine Connection for Refresh Token ===" -ForegroundColor Cyan
$query = @"
SELECT 
    id,
    tool_name,
    CASE 
        WHEN meta_data::json->>'refresh_token' IS NULL THEN 'NO'
        WHEN meta_data::json->>'refresh_token' = 'null' THEN 'NO'
        WHEN meta_data::json->>'refresh_token' = '' THEN 'NO'
        ELSE 'YES'
    END as has_refresh_token,
    CASE 
        WHEN meta_data::json->>'access_token' IS NULL THEN 'NO'
        WHEN meta_data::json->>'access_token' = 'null' THEN 'NO'
        ELSE 'YES'
    END as has_access_token
FROM ticketing_tool_connections 
WHERE tool_name = 'manageengine'
ORDER BY created_at DESC
LIMIT 1;
"@

$result = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c $query 2>&1
Write-Host $result

# If we found a connection, show the full meta_data (sanitized)
Write-Host "`n=== Full Connection Details (Sanitized) ===" -ForegroundColor Cyan
$metaQuery = @"
SELECT 
    id,
    meta_data::json->>'client_id' as client_id,
    CASE WHEN meta_data::json->>'access_token' IS NOT NULL THEN 'PRESENT' ELSE 'MISSING' END as access_token_status,
    CASE WHEN meta_data::json->>'refresh_token' IS NOT NULL AND meta_data::json->>'refresh_token' != 'null' THEN 'PRESENT' ELSE 'MISSING' END as refresh_token_status,
    LENGTH(meta_data::json->>'refresh_token') as refresh_token_length
FROM ticketing_tool_connections 
WHERE tool_name = 'manageengine'
ORDER BY created_at DESC
LIMIT 1;
"@

$metaResult = docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c $metaQuery 2>&1
Write-Host $metaResult



