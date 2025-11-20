# Check credential structure
$credentialId = Read-Host "Enter credential ID (or press Enter for 1)"
if ([string]::IsNullOrWhiteSpace($credentialId)) {
    $credentialId = 1
}

Write-Host "Checking credential $credentialId..." -ForegroundColor Cyan

# Check via API
$url = "http://localhost:8000/api/v1/connectors/credentials"
try {
    $response = Invoke-RestMethod -Uri $url -Method GET
    $cred = $response.credentials | Where-Object { $_.id -eq [int]$credentialId }
    
    if ($cred) {
        Write-Host "`nCredential found:" -ForegroundColor Green
        Write-Host "  ID: $($cred.id)" -ForegroundColor White
        Write-Host "  Name: $($cred.name)" -ForegroundColor White
        Write-Host "  Type: $($cred.type)" -ForegroundColor White
        Write-Host "  Environment: $($cred.environment)" -ForegroundColor White
        Write-Host "  Host: $($cred.host)" -ForegroundColor White
        Write-Host "  Port: $($cred.port)" -ForegroundColor White
        
        if ($cred.type -ne "azure") {
            Write-Host "`n⚠ WARNING: Credential type is '$($cred.type)', not 'azure'!" -ForegroundColor Yellow
            Write-Host "  The credential must be of type 'azure' for Azure connections." -ForegroundColor Yellow
        }
    } else {
        Write-Host "`n✗ Credential $credentialId not found" -ForegroundColor Red
    }
} catch {
    Write-Host "`n✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nChecking infrastructure connection..." -ForegroundColor Cyan
$connUrl = "http://localhost:8000/api/v1/connectors/infrastructure-connections"
try {
    $response = Invoke-RestMethod -Uri $connUrl -Method GET
    $conn = $response.connections | Where-Object { $_.id -eq 1 }
    
    if ($conn) {
        Write-Host "`nConnection found:" -ForegroundColor Green
        Write-Host "  ID: $($conn.id)" -ForegroundColor White
        Write-Host "  Name: $($conn.name)" -ForegroundColor White
        Write-Host "  Type: $($conn.type)" -ForegroundColor White
        Write-Host "  Credential ID: $($conn.credential_id)" -ForegroundColor White
        
        if (-not $conn.credential_id) {
            Write-Host "`n⚠ WARNING: Connection has no credential assigned!" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "`n✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}





