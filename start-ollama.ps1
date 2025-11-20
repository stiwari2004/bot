# PowerShell script to start Ollama server and pull Llama 3.2 if needed

Write-Host "🚀 Starting Ollama with Llama 3.2" -ForegroundColor Green
Write-Host ""

# Check if Ollama is installed
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: Ollama is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Ollama first:" -ForegroundColor Yellow
    Write-Host "  1. Visit: https://ollama.com/download/windows" -ForegroundColor Cyan
    Write-Host "  2. Download and run the installer" -ForegroundColor Cyan
    Write-Host "  3. Or run: .\install-ollama.ps1" -ForegroundColor Cyan
    exit 1
}

Write-Host "✅ Ollama is installed" -ForegroundColor Green

# Check if Ollama server is already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Ollama server is already running on port 11434" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama server is not running. Starting it..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Note: Ollama usually runs as a Windows service." -ForegroundColor Gray
    Write-Host "If it's not running, you may need to:" -ForegroundColor Gray
    Write-Host "  1. Check Windows Services (services.msc)" -ForegroundColor Gray
    Write-Host "  2. Start the 'Ollama' service" -ForegroundColor Gray
    Write-Host "  3. Or run 'ollama serve' manually" -ForegroundColor Gray
    Write-Host ""
    
    # Try to start Ollama serve in background
    Write-Host "Attempting to start Ollama server..." -ForegroundColor Cyan
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    
    # Check again
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Host "✅ Ollama server started successfully!" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not verify server is running. It may need manual start." -ForegroundColor Yellow
    }
}

# Check if Llama 3.2 is installed
Write-Host ""
    Write-Host "Checking for Llama 3.2 model (preferred) or 3.1 (fallback)..." -ForegroundColor Cyan

try {
    $models = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5 | ConvertFrom-Json
    $hasLlama32 = $false
    $hasLlama31 = $false
    $modelName = ""
    
    foreach ($model in $models.models) {
        if ($model.name -like "*llama3.2*" -or $model.name -like "*llama*3.2*") {
            $hasLlama32 = $true
            $modelName = $model.name
            break
        }
        if ($model.name -like "*llama3.1*" -or $model.name -like "*llama*3.1*") {
            $hasLlama31 = $true
            if (-not $modelName) {
                $modelName = $model.name
            }
        }
    }
    
    if ($hasLlama32) {
        Write-Host "✅ Llama 3.2 is already installed: $modelName" -ForegroundColor Green
        Write-Host "   (3.2 is newer and better than 3.1 - great choice!)" -ForegroundColor Gray
    } elseif ($hasLlama31) {
        Write-Host "⚠️  Llama 3.1 found: $modelName" -ForegroundColor Yellow
        Write-Host "   (3.1 works, but 3.2 is newer and better)" -ForegroundColor Gray
        $response = Read-Host "Would you like to download Llama 3.2:8b? (Y/N)"
        if ($response -eq "Y" -or $response -eq "y") {
            Write-Host "📥 Downloading Llama 3.2:8b..." -ForegroundColor Yellow
            Write-Host "   This may take 10-30 minutes depending on your internet speed." -ForegroundColor Gray
            Write-Host "   Model size: ~4.7GB" -ForegroundColor Gray
            Write-Host ""
            
            Write-Host "Pulling llama3.2:8b (recommended - newer and better than 3.1)..." -ForegroundColor Cyan
            $pullProcess = Start-Process -FilePath "ollama" -ArgumentList "pull", "llama3.2:8b" -NoNewWindow -Wait -PassThru
            
            if ($pullProcess.ExitCode -eq 0) {
                Write-Host "✅ Llama 3.2 downloaded successfully!" -ForegroundColor Green
            } else {
                Write-Host "❌ Error downloading model. Exit code: $($pullProcess.ExitCode)" -ForegroundColor Red
                Write-Host "   You can try manually: ollama pull llama3.2:8b" -ForegroundColor Yellow
                Write-Host "   Or continue with Llama 3.1 which is already installed." -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "📥 No Llama model found. Downloading Llama 3.2:8b (recommended)..." -ForegroundColor Yellow
        Write-Host "   This may take 10-30 minutes depending on your internet speed." -ForegroundColor Gray
        Write-Host "   Model size: ~4.7GB" -ForegroundColor Gray
        Write-Host "   (3.2 is newer and better than 3.1)" -ForegroundColor Gray
        Write-Host ""
        
        Write-Host "Pulling llama3.2:8b..." -ForegroundColor Cyan
        $pullProcess = Start-Process -FilePath "ollama" -ArgumentList "pull", "llama3.2:8b" -NoNewWindow -Wait -PassThru
        
        if ($pullProcess.ExitCode -eq 0) {
            Write-Host "✅ Llama 3.2 downloaded successfully!" -ForegroundColor Green
        } else {
            Write-Host "❌ Error downloading model. Exit code: $($pullProcess.ExitCode)" -ForegroundColor Red
            Write-Host "   You can try manually: ollama pull llama3.2:8b" -ForegroundColor Yellow
            Write-Host "   Or try Llama 3.1: ollama pull llama3.1:8b" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "⚠️  Could not check models. Server may not be ready yet." -ForegroundColor Yellow
    Write-Host "   Error: $_" -ForegroundColor Gray
    Write-Host ""
    Write-Host "You can manually pull the model later:" -ForegroundColor Yellow
    Write-Host "   ollama pull llama3.2:8b" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Ollama Configuration:" -ForegroundColor Cyan
Write-Host "   Server: http://localhost:11434" -ForegroundColor Gray
Write-Host "   Model: llama3.2:8b" -ForegroundColor Gray
Write-Host "   API: OpenAI-compatible at http://localhost:11434/v1" -ForegroundColor Gray
Write-Host ""
Write-Host "Docker containers can access via: http://host.docker.internal:11434" -ForegroundColor Cyan
Write-Host ""
Write-Host "To test the connection:" -ForegroundColor Yellow
Write-Host "   curl http://localhost:11434/api/tags" -ForegroundColor Cyan
Write-Host ""
Write-Host "The server will continue running in the background." -ForegroundColor Gray
Write-Host "You can now start your Docker containers!" -ForegroundColor Green

