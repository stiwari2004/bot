# PowerShell script to download Docker Desktop for Windows

Write-Host "📥 Downloading Docker Desktop for Windows..." -ForegroundColor Green
Write-Host ""

$downloadUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$downloadPath = "$env:USERPROFILE\Downloads\Docker Desktop Installer.exe"

try {
    Write-Host "Downloading from: $downloadUrl" -ForegroundColor Cyan
    Write-Host "Saving to: $downloadPath" -ForegroundColor Cyan
    Write-Host ""
    
    # Create Downloads directory if it doesn't exist
    $downloadsDir = Split-Path $downloadPath -Parent
    if (-not (Test-Path $downloadsDir)) {
        New-Item -ItemType Directory -Path $downloadsDir -Force | Out-Null
    }
    
    # Download using Invoke-WebRequest
    Invoke-WebRequest -Uri $downloadUrl -OutFile $downloadPath -UseBasicParsing
    
    Write-Host "✅ Download complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Run the installer: $downloadPath" -ForegroundColor Yellow
    Write-Host "  2. Follow the installation wizard" -ForegroundColor Yellow
    Write-Host "  3. Enable WSL 2 backend (recommended)" -ForegroundColor Yellow
    Write-Host "  4. Restart your computer if prompted" -ForegroundColor Yellow
    Write-Host "  5. Launch Docker Desktop after restart" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installation, verify with: docker --version" -ForegroundColor Cyan
    
    # Ask if user wants to open the installer
    $response = Read-Host "Would you like to open the installer now? (Y/N)"
    if ($response -eq "Y" -or $response -eq "y") {
        Start-Process $downloadPath
    }
    
} catch {
    Write-Host "❌ Error downloading Docker Desktop: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please download manually from:" -ForegroundColor Yellow
    Write-Host "  https://www.docker.com/products/docker-desktop/" -ForegroundColor Cyan
    exit 1
}






