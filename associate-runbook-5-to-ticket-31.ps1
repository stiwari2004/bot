# PowerShell script to manually associate runbook 5 with ticket 31
$containerName = "bot-postgres-1"
$databaseName = "troubleshooting_ai"
$user = "postgres"
$ticketId = 31
$runbookId = 5

Write-Host "Associating runbook $runbookId with ticket $ticketId..."

# Check if container is running
$containerStatus = docker inspect -f '{{.State.Status}}' $containerName 2>$null
if ($containerStatus -ne "running") {
    Write-Error "Docker container '$containerName' is not running. Please start it first."
    exit 1
}

# Get runbook title
$runbookQuery = "SELECT title FROM runbooks WHERE id = $runbookId AND is_active = 'active';"
$runbookTitle = docker exec $containerName psql -U $user -d $databaseName -t -c $runbookQuery | ForEach-Object { $_.Trim() }

if (-not $runbookTitle) {
    Write-Error "Runbook $runbookId not found or not active."
    exit 1
}

Write-Host "Runbook title: $runbookTitle"

# Update ticket meta_data to include runbook
# Escape single quotes in title
$runbookTitleEscaped = $runbookTitle -replace "'", "''"

# Use a simpler UPDATE query that works in PowerShell
# First check if runbook already exists, then update
$checkQuery = "SELECT COUNT(*) FROM tickets, jsonb_array_elements(COALESCE(meta_data->'matched_runbooks', '[]'::jsonb)) AS rb WHERE tickets.id = $ticketId AND (rb->>'id')::int = $runbookId;"
$exists = docker exec $containerName psql -U $user -d $databaseName -t -c $checkQuery | ForEach-Object { $_.Trim() }

if ($exists -eq "0") {
    Write-Host "Runbook not in list, adding..."
    $updateQuery = @"
UPDATE tickets
SET meta_data = 
    COALESCE(meta_data, '{}'::jsonb) || 
    jsonb_build_object(
        'matched_runbooks',
        COALESCE(meta_data->'matched_runbooks', '[]'::jsonb) || 
        jsonb_build_array(
            jsonb_build_object(
                'id', $runbookId,
                'title', '$runbookTitleEscaped',
                'confidence_score', 1.0,
                'reasoning', 'Manually associated runbook'
            )
        )
    )
WHERE id = $ticketId;
"@
} else {
    Write-Host "Runbook already in list, skipping..."
    $updateQuery = "SELECT 'Already exists' AS status;"
}

Write-Host "Executing update query..."
docker exec $containerName psql -U $user -d $databaseName -c $updateQuery

Write-Host "`nVerifying association..."
$verifyQuery = "SELECT id, title, meta_data->'matched_runbooks' AS matched_runbooks FROM tickets WHERE id = $ticketId;"
docker exec $containerName psql -U $user -d $databaseName -c $verifyQuery

Write-Host "`nDone!"

