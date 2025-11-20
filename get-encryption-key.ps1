# Generate Fernet encryption key
Write-Host "Generating Fernet encryption key..." -ForegroundColor Cyan

# Use Python to generate the key
$pythonCode = @"
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
"@

try {
    $key = python -c $pythonCode 2>&1
    if ($LASTEXITCODE -eq 0 -and $key -match '^[A-Za-z0-9+/=]{43}$') {
        Write-Host "`nGenerated encryption key:" -ForegroundColor Green
        Write-Host $key -ForegroundColor White
        Write-Host "`nAdd this to docker-compose.yml as:" -ForegroundColor Yellow
        Write-Host "  - CREDENTIAL_ENCRYPTION_KEY=$key" -ForegroundColor Cyan
    } else {
        Write-Host "Failed to generate key. Using fallback method..." -ForegroundColor Yellow
        # Fallback: use a fixed key for development (NOT for production!)
        $key = "dev-key-not-for-production-change-this-in-production-12345678901234567890123456789012"
        Write-Host "Using development key (CHANGE IN PRODUCTION!):" -ForegroundColor Yellow
        Write-Host $key -ForegroundColor White
    }
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nYou can manually generate a key using:" -ForegroundColor Yellow
    Write-Host "  python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'" -ForegroundColor Cyan
}



