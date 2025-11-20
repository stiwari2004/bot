# PowerShell script to start llama.cpp server on Windows
# Optimized for 32GB RAM system with NVIDIA GPU

Write-Host "🚀 Starting LLM Server (Llama/Mistral 7B)" -ForegroundColor Green
Write-Host "💾 Optimized for 32GB RAM system:" -ForegroundColor Cyan
Write-Host "   - Context size: 8192 tokens (full context for runbook generation)" -ForegroundColor Gray
Write-Host "   - Threads: 8 (utilize multiple CPU cores)" -ForegroundColor Gray
Write-Host "   - Batch size: 512 (process multiple requests)" -ForegroundColor Gray
Write-Host "   - GPU acceleration: Enabled (if available)" -ForegroundColor Gray
Write-Host ""

# Configuration
$PORT = 8080
$MODELS_DIR = "$PSScriptRoot\models"
$LLAMA_SERVER_PATH = ""

# Try to find llama-server binary
$possiblePaths = @(
    "llama-server",
    "C:\llama.cpp\llama-server.exe",
    "C:\llama.cpp\server.exe",
    "$env:USERPROFILE\llama.cpp\build\bin\Release\llama-server.exe",
    "$env:USERPROFILE\llama.cpp\build\bin\Release\server.exe"
)

foreach ($path in $possiblePaths) {
    if (Get-Command $path -ErrorAction SilentlyContinue) {
        $LLAMA_SERVER_PATH = $path
        break
    }
    if (Test-Path $path) {
        $LLAMA_SERVER_PATH = $path
        break
    }
}

if (-not $LLAMA_SERVER_PATH) {
    Write-Host "❌ Error: llama-server not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install llama.cpp server:" -ForegroundColor Yellow
    Write-Host "  1. Download from: https://github.com/ggerganov/llama.cpp/releases" -ForegroundColor Yellow
    Write-Host "  2. Extract to C:\llama.cpp\" -ForegroundColor Yellow
    Write-Host "  3. Or update this script with the correct path" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or build from source:" -ForegroundColor Yellow
    Write-Host "  git clone https://github.com/ggerganov/llama.cpp.git" -ForegroundColor Yellow
    Write-Host "  cd llama.cpp" -ForegroundColor Yellow
    Write-Host "  mkdir build && cd build" -ForegroundColor Yellow
    Write-Host "  cmake .. -DCMAKE_BUILD_TYPE=Release" -ForegroundColor Yellow
    Write-Host "  cmake --build . --config Release" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Found llama-server at: $LLAMA_SERVER_PATH" -ForegroundColor Green

# Check if port is already in use
$portInUse = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "⚠️  Port $PORT is already in use. Stopping existing process..." -ForegroundColor Yellow
    $process = Get-Process -Id ($portInUse.OwningProcess) -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $process.Id -Force
        Start-Sleep -Seconds 2
    }
}

# Find model file
$modelFiles = @(
    "$MODELS_DIR\mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    "$MODELS_DIR\llama-2-7b-chat.Q4_K_M.gguf",
    "$MODELS_DIR\mistral-7b-instruct-v0.2.Q4_K_S.gguf",
    "$MODELS_DIR\llama-2-7b-chat.Q4_K_S.gguf",
    "$MODELS_DIR\*.gguf"
)

$MODEL_PATH = $null
foreach ($modelFile in $modelFiles) {
    if (Test-Path $modelFile) {
        $MODEL_PATH = (Get-Item $modelFile).FullName
        break
    }
}

if (-not $MODEL_PATH) {
    Write-Host "❌ Error: Model file not found in $MODELS_DIR" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please download a model:" -ForegroundColor Yellow
    Write-Host "  Recommended: Mistral 7B Q4_K_M" -ForegroundColor Yellow
    Write-Host "  URL: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF" -ForegroundColor Yellow
    Write-Host "  File: mistral-7b-instruct-v0.2.Q4_K_M.gguf" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or Llama 2 7B:" -ForegroundColor Yellow
    Write-Host "  URL: https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF" -ForegroundColor Yellow
    Write-Host "  File: llama-2-7b-chat.Q4_K_M.gguf" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Save the .gguf file to: $MODELS_DIR" -ForegroundColor Yellow
    
    # Create models directory if it doesn't exist
    if (-not (Test-Path $MODELS_DIR)) {
        Write-Host ""
        Write-Host "Creating models directory..." -ForegroundColor Cyan
        New-Item -ItemType Directory -Path $MODELS_DIR -Force | Out-Null
    }
    
    exit 1
}

Write-Host "✅ Found model: $(Split-Path $MODEL_PATH -Leaf)" -ForegroundColor Green
Write-Host ""

# Check for GPU (NVIDIA)
$hasGPU = $false
try {
    $gpu = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
    if ($gpu) {
        $hasGPU = $true
        Write-Host "✅ NVIDIA GPU detected: $($gpu.Name)" -ForegroundColor Green
    }
} catch {
    # Ignore errors
}

# Start llama-server with optimized settings for 32GB RAM
Write-Host "📡 Starting server on port $PORT..." -ForegroundColor Cyan
Write-Host "   Model: $(Split-Path $MODEL_PATH -Leaf)" -ForegroundColor Gray
Write-Host "   Context: 8192 tokens (full context for runbook generation)" -ForegroundColor Gray
Write-Host "   Threads: 8 (utilize multiple CPU cores)" -ForegroundColor Gray
Write-Host "   Batch size: 512 (process multiple requests)" -ForegroundColor Gray
if ($hasGPU) {
    Write-Host "   GPU: Enabled (using NVIDIA GPU)" -ForegroundColor Gray
} else {
    Write-Host "   GPU: CPU-only mode" -ForegroundColor Gray
}
Write-Host ""

# Build command arguments
$args = @(
    "--model", "`"$MODEL_PATH`"",
    "--port", $PORT,
    "--ctx-size", "8192",
    "--threads", "8",
    "--batch-size", "512",
    "--parallel", "4",
    "--host", "0.0.0.0",
    "--n-gpu-layers", "35"  # Use GPU for most layers if available
)

# Start the server
Write-Host "Starting llama-server..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

try {
    & $LLAMA_SERVER_PATH $args
} catch {
    Write-Host "❌ Error starting server: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Verify llama-server binary is correct" -ForegroundColor Yellow
    Write-Host "  2. Check model file is valid" -ForegroundColor Yellow
    Write-Host "  3. Ensure port 8080 is not blocked by firewall" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "✅ LLM Server started successfully!" -ForegroundColor Green
Write-Host "   Access at: http://localhost:$PORT" -ForegroundColor Cyan
Write-Host "   Docker containers can access via: http://host.docker.internal:$PORT" -ForegroundColor Cyan




