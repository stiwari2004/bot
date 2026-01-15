# PowerShell script to apply performance indexes to database in Docker container
# Usage: .\apply_performance_indexes.ps1 [container_name] [database_name]

param(
    [string]$ContainerName = "bot-dev-postgres",
    [string]$DatabaseName = "troubleshooting_ai_dev",
    [string]$DbUser = "postgres"
)

Write-Host "Applying performance indexes to database: $DatabaseName"
Write-Host "Container: $ContainerName, User: $DbUser"

# Check if container is running
$container = docker ps --filter "name=$ContainerName" --format "{{.Names}}"
if (-not $container) {
    Write-Host "Error: Container '$ContainerName' is not running."
    Write-Host "Available containers:"
    docker ps --format "{{.Names}}"
    exit 1
}

# Copy SQL file into container
Write-Host "Copying SQL file into container..."
docker cp backend/sql/add_performance_indexes.sql ${ContainerName}:/tmp/add_performance_indexes.sql

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to copy SQL file into container"
    exit 1
}

# Execute SQL script inside container
Write-Host "Executing SQL script..."
docker exec -i ${ContainerName} psql -U ${DbUser} -d ${DatabaseName} -f /tmp/add_performance_indexes.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Performance indexes applied successfully!"
    # Clean up
    docker exec ${ContainerName} rm -f /tmp/add_performance_indexes.sql
} else {
    Write-Host "❌ Failed to apply performance indexes"
    exit 1
}
