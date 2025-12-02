<#
.SYNOPSIS
    Simple PowerShell script to check Datadog API connection and list monitors

.USAGE
    .\check-datadog-monitors.ps1 -ApiKey "xxx" -AppKey "yyy"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey,

    [Parameter(Mandatory=$true)]
    [string]$AppKey,

    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl = "https://api.datadoghq.com"
)

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host " Datadog Monitor Retrieval Test " -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

$headers = @{
    "DD-API-KEY"         = $ApiKey
    "DD-APPLICATION-KEY" = $AppKey
    "Accept"             = "application/json"
}

$url = "$ApiBaseUrl/api/v1/monitor"

try {
    Write-Host "Calling Datadog API..." -ForegroundColor Gray
    $response = Invoke-RestMethod -Method GET -Uri $url -Headers $headers

    if (-not $response) {
        Write-Host "❌ No monitors found or unexpected response" -ForegroundColor Red
        exit 0
    }

    Write-Host "✅ Datadog API is reachable!" -ForegroundColor Green
    Write-Host ""

    # Ensure array format
    $monitors = @()
    if ($response -is [System.Collections.IEnumerable]) {
        $monitors = $response
    } else {
        $monitors += $response
    }

    Write-Host "Found $($monitors.Count) monitor(s)." -ForegroundColor Yellow
    Write-Host ""

    foreach ($mon in $monitors) {
        $state = if ($mon.overall_state) { $mon.overall_state } `
                 elseif ($mon.state.status) { $mon.state.status } `
                 else { "Unknown" }

        Write-Host "Monitor:" -ForegroundColor Cyan
        Write-Host "  ID: $($mon.id)" -ForegroundColor White
        Write-Host "  Name: $($mon.name)" -ForegroundColor White
        Write-Host "  State: $state" -ForegroundColor $(if ($state -eq "Alert") {"Red"} else {"Green"})
        Write-Host "-" * 60 -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "➡️ You can mute a monitor using:" -ForegroundColor Yellow
    Write-Host '   .\mute-datadog-monitor.ps1 -MonitorId <id> -ApiKey "xxx" -AppKey "yyy"' -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host "❌ Error connecting to Datadog:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
