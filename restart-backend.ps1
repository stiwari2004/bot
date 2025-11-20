# PowerShell script to restart backend service
Write-Host "Restarting backend service..."
docker-compose restart backend
Write-Host "Backend service restarted. Waiting 5 seconds for it to start..."
Start-Sleep -Seconds 5
Write-Host "Done."
