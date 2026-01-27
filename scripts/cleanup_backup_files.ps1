# Cleanup Backup Files Script
# This script removes duplicate/backup files that were accidentally created in C:\Program Files\cursor\
# Run this script with administrator privileges: Right-click PowerShell -> Run as Administrator

Write-Host "Starting cleanup of backup files..." -ForegroundColor Yellow

$backupPaths = @(
    "C:\Program Files\cursor\AUTH_CONTEXT_STRATEGY.md",
    "C:\Program Files\cursor\backend",
    "C:\Program Files\cursor\frontend-nextjs",
    "C:\Program Files\cursor\FIXES_COMPLETE_SUMMARY.md",
    "C:\Program Files\cursor\QUICK_API_TEST_COMMANDS.md",
    "C:\Program Files\cursor\TESTING_NEXT_STEPS.md"
)

$deletedCount = 0
$failedCount = 0

foreach ($path in $backupPaths) {
    if (Test-Path $path) {
        try {
            if (Test-Path $path -PathType Container) {
                Remove-Item -Path $path -Recurse -Force
                Write-Host "Deleted directory: $path" -ForegroundColor Green
            } else {
                Remove-Item -Path $path -Force
                Write-Host "Deleted file: $path" -ForegroundColor Green
            }
            $deletedCount++
        } catch {
            Write-Host "Failed to delete: $path - $_" -ForegroundColor Red
            $failedCount++
        }
    } else {
        Write-Host "Path not found (already deleted?): $path" -ForegroundColor Gray
    }
}

Write-Host "`nCleanup Summary:" -ForegroundColor Cyan
Write-Host "  Deleted: $deletedCount" -ForegroundColor Green
Write-Host "  Failed: $failedCount" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "Green" })
Write-Host "`nCleanup complete!" -ForegroundColor Yellow
