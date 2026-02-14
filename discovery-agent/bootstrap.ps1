# One-command discovery for Windows: download agent, install deps (venv), run scan.
# Usage (PowerShell):
#   .\bootstrap.ps1 -IngestUrl "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" -Token "YOUR_TOKEN"
# Or one-liner from web (if script is hosted):
#   iex (New-Object Net.WebClient).DownloadString("https://.../bootstrap.ps1"); Run-Discovery "URL" "TOKEN"
#
# Requires: PowerShell 5+, Python 3 in PATH
param(
    [Parameter(Mandatory=$true)][string]$IngestUrl,
    [Parameter(Mandatory=$true)][string]$Token
)

$ErrorActionPreference = "Stop"

# Derive base URL and agent.zip URL
if ($IngestUrl -match "^(.+)/api/") {
    $BaseUrl = $Matches[1]
} else {
    $BaseUrl = $IngestUrl -replace "/ingest$", ""
}
$AgentZipUrl = "$BaseUrl/api/v1/tenant-admin/discovery/agent.zip"

# Install dir
$InstallDir = if ($env:RESOLVIFY_DISCOVERY_DIR) { $env:RESOLVIFY_DISCOVERY_DIR } else { Join-Path $env:USERPROFILE ".resolvify-discovery" }
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Location $InstallDir

Write-Host "Downloading discovery agent from $AgentZipUrl ..."
$TmpZip = Join-Path $env:TEMP "resolvify-agent-$([Guid]::NewGuid().ToString('n')).zip"
try {
    Invoke-WebRequest -Uri $AgentZipUrl -OutFile $TmpZip -UseBasicParsing
} catch {
    Write-Host "Download failed. Copy the discovery-agent folder to this machine and run: python discover.py `"$IngestUrl`" `"TOKEN`"" -ForegroundColor Yellow
    exit 1
}

# Check zip
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::OpenRead($TmpZip).Dispose()
} catch {
    Write-Host "Downloaded file is not a valid zip. Copy discovery-agent folder manually." -ForegroundColor Yellow
    Remove-Item -Force $TmpZip -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "Extracting to $InstallDir ..."
Expand-Archive -Path $TmpZip -DestinationPath $InstallDir -Force
Remove-Item -Force $TmpZip -ErrorAction SilentlyContinue

$AgentDir = $InstallDir
if (Test-Path (Join-Path $InstallDir "discovery-agent\discover.py")) {
    $AgentDir = Join-Path $InstallDir "discovery-agent"
} elseif (Test-Path (Join-Path $InstallDir "discover.py")) {
    $AgentDir = $InstallDir
}

if (-not (Test-Path (Join-Path $AgentDir "discover.py"))) {
    Write-Host "Agent package layout unexpected." -ForegroundColor Red
    exit 1
}

Write-Host "Installing dependencies and running discovery..."
Set-Location $AgentDir
& python discover.py $IngestUrl $Token
exit $LASTEXITCODE
