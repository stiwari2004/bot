# Interactive PaaS Setup Script for Windows
# This script guides users through configuration and generates .env file

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Troubleshooting AI - PaaS Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will help you configure your deployment."
Write-Host "Press Enter to use default values (shown in brackets)."
Write-Host ""

# Navigate to backend directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $scriptPath "..\backend"
Set-Location $backendPath

# Check if .env already exists
if (Test-Path ".env") {
    Write-Host "Warning: .env file already exists" -ForegroundColor Yellow
    $overwrite = Read-Host "Do you want to overwrite it? (y/N)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Setup cancelled."
        exit 0
    }
    $backupName = ".env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item ".env" $backupName
    Write-Host "Backed up existing .env file to $backupName"
    Write-Host ""
}

# Function to generate secure random string
function Generate-Secret {
    try {
        $bytes = New-Object byte[] 32
        [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
        return [Convert]::ToBase64String($bytes).Substring(0, 32)
    } catch {
        return -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    }
}

# Function to generate Fernet key
function Generate-FernetKey {
    try {
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    } catch {
        Write-Host "Warning: Could not auto-generate Fernet key. Python cryptography library required." -ForegroundColor Yellow
        return ""
    }
}

# Start configuration
Write-Host "=== Database Configuration ===" -ForegroundColor Cyan
$DATABASE_URL = Read-Host "Database URL [postgresql://postgres:password@localhost:5432/troubleshooting_ai]"
if ([string]::IsNullOrWhiteSpace($DATABASE_URL)) {
    $DATABASE_URL = "postgresql://postgres:password@localhost:5432/troubleshooting_ai"
}

Write-Host ""
Write-Host "=== Security Configuration ===" -ForegroundColor Cyan
Write-Host "Generating secure keys..."
$SECRET_KEY = Generate-Secret
$CREDENTIAL_ENCRYPTION_KEY = Generate-FernetKey

if ([string]::IsNullOrWhiteSpace($CREDENTIAL_ENCRYPTION_KEY)) {
    $CREDENTIAL_ENCRYPTION_KEY = Read-Host "Enter CREDENTIAL_ENCRYPTION_KEY (or press Enter to skip)"
    if ([string]::IsNullOrWhiteSpace($CREDENTIAL_ENCRYPTION_KEY)) {
        Write-Host "Warning: You'll need to set CREDENTIAL_ENCRYPTION_KEY manually" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Environment Configuration ===" -ForegroundColor Cyan
$ENVIRONMENT = Read-Host "Environment (development/staging/production) [production]"
if ([string]::IsNullOrWhiteSpace($ENVIRONMENT)) {
    $ENVIRONMENT = "production"
}

$DEBUG_INPUT = Read-Host "Enable DEBUG mode? (y/N)"
if ($DEBUG_INPUT -eq "y" -or $DEBUG_INPUT -eq "Y") {
    $DEBUG = "true"
} else {
    $DEBUG = "false"
}

Write-Host ""
Write-Host "=== LLM Configuration ===" -ForegroundColor Cyan
$LLM_PROVIDER = Read-Host "LLM Provider (llamacpp/openai/anthropic) [llamacpp]"
if ([string]::IsNullOrWhiteSpace($LLM_PROVIDER)) {
    $LLM_PROVIDER = "llamacpp"
}

$LLM_BASE_URL = Read-Host "LLM Base URL [http://localhost:11434]"
if ([string]::IsNullOrWhiteSpace($LLM_BASE_URL)) {
    $LLM_BASE_URL = "http://localhost:11434"
}

$LLM_MODEL = Read-Host "LLM Model [llama3.1:8b]"
if ([string]::IsNullOrWhiteSpace($LLM_MODEL)) {
    $LLM_MODEL = "llama3.1:8b"
}

Write-Host ""
Write-Host "=== Optional: External APIs ===" -ForegroundColor Cyan
$PERPLEXITY_API_KEY = Read-Host "Perplexity API Key (optional, press Enter to skip)"

Write-Host ""
Write-Host "=== Frontend Configuration ===" -ForegroundColor Cyan
$FRONTEND_BASE_URL = Read-Host "Frontend Base URL [http://localhost:3000]"
if ([string]::IsNullOrWhiteSpace($FRONTEND_BASE_URL)) {
    $FRONTEND_BASE_URL = "http://localhost:3000"
}

$BACKEND_BASE_URL = Read-Host "Backend Base URL [http://localhost:8000]"
if ([string]::IsNullOrWhiteSpace($BACKEND_BASE_URL)) {
    $BACKEND_BASE_URL = "http://localhost:8000"
}

# Build ALLOWED_HOSTS
Write-Host ""
Write-Host "=== CORS Configuration ===" -ForegroundColor Cyan
$ADDITIONAL_HOSTS = Read-Host "Additional allowed hosts (comma-separated, press Enter for defaults)"
$ALLOWED_HOSTS = "`"$FRONTEND_BASE_URL`",`"$BACKEND_BASE_URL`""
if (-not [string]::IsNullOrWhiteSpace($ADDITIONAL_HOSTS)) {
    $hosts = $ADDITIONAL_HOSTS -split ","
    foreach ($host in $hosts) {
        $ALLOWED_HOSTS += ",`"$($host.Trim())`""
    }
}
$ALLOWED_HOSTS = "[$ALLOWED_HOSTS]"

# Generate .env file
Write-Host ""
Write-Host "=== Generating .env file ===" -ForegroundColor Cyan

$envContent = @"
# Database Configuration
# Generated by setup-paas.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
DATABASE_URL=$DATABASE_URL

# Security
# IMPORTANT: Keep these secret! Do not commit to version control.
SECRET_KEY=$SECRET_KEY
CREDENTIAL_ENCRYPTION_KEY=$CREDENTIAL_ENCRYPTION_KEY

ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=$ENVIRONMENT
DEBUG=$DEBUG

# CORS
ALLOWED_HOSTS=$ALLOWED_HOSTS

# Vector Store
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# LLM
LLM_PROVIDER=$LLM_PROVIDER
LLM_MODEL=$LLM_MODEL
LLM_BASE_URL=$LLM_BASE_URL

# Perplexity API (optional)
PERPLEXITY_API_KEY=$PERPLEXITY_API_KEY

# File Upload
MAX_FILE_SIZE=104857600
UPLOAD_DIR=uploads

# Multi-tenant
DEFAULT_TENANT=default
DEFAULT_TENANT_ID=1

# Queue / Streaming
REDIS_URL=redis://localhost:6379/0
REDIS_STREAM_ASSIGN=session.assign
REDIS_STREAM_COMMAND=session.command
REDIS_STREAM_RESULT=session.result
REDIS_STREAM_EVENTS=session.events
WORKER_ORCHESTRATION_ENABLED=true

# URLs
FRONTEND_BASE_URL=$FRONTEND_BASE_URL
BACKEND_BASE_URL=$BACKEND_BASE_URL
OAUTH_CALLBACK_URL=$BACKEND_BASE_URL/oauth/callback
"@

$envContent | Out-File -FilePath ".env" -Encoding utf8

Write-Host ""
Write-Host "✓ .env file created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Review the generated .env file: Get-Content backend\.env"
Write-Host "2. Update any values if needed"
Write-Host "3. Start your deployment:"
Write-Host "   docker-compose -f docker-compose.optimized.yml up -d"
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green








