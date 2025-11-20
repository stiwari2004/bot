# PowerShell script to install Ollama on Windows

Write-Host "📥 Installing Ollama for Windows..." -ForegroundColor Green
Write-Host ""

$ollamaUrl = "https://ollama.com/download/windows"
$downloadPath = "$env:USERPROFILE\Downloads\OllamaSetup.exe"

Write-Host "Ollama provides an easy way to run LLMs locally." -ForegroundColor Cyan
Write-Host "Its much simpler than llama.cpp - just install and run!" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is already installed
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "✅ Ollama is already installed!" -ForegroundColor Green
    $version = ollama --version 2>&1
    Write-Host "   Version: $version" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To pull Llama 3.2, run:" -ForegroundColor Yellow
    Write-Host "   ollama pull llama3.2" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To start the server, run:" -ForegroundColor Yellow
    Write-Host "   ollama serve" -ForegroundColor Cyan
    exit 0
}

Write-Host "Ollama is not installed. Please download and install:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Visit: https://ollama.com/download/windows" -ForegroundColor Cyan
Write-Host "2. Download the Windows installer" -ForegroundColor Cyan
Write-Host "3. Run the installer" -ForegroundColor Cyan
Write-Host "4. After installation, Ollama will start automatically" -ForegroundColor Cyan
Write-Host ""
Write-Host "Or use winget (if available):" -ForegroundColor Yellow
Write-Host "   winget install Ollama.Ollama" -ForegroundColor Cyan
Write-Host ""

# Try to open the download page
$response = Read-Host "Would you like to open the download page in your browser? (Y/N)"
if ($response -eq "Y" -or $response -eq "y") {
    Start-Process "https://ollama.com/download/windows"
}

Write-Host ""
Write-Host "After installation, run this script again to verify and pull Llama 3.2." -ForegroundColor Yellow

