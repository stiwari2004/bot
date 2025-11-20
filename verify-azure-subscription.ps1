# Script to verify Azure subscription details
# This helps verify the subscription ID matches what's in Azure

Write-Host "=== Azure Subscription Verification ===" -ForegroundColor Cyan
Write-Host ""

# Check if Azure CLI is installed
$azInstalled = Get-Command az -ErrorAction SilentlyContinue
if (-not $azInstalled) {
    Write-Host "Azure CLI is not installed. Installing..." -ForegroundColor Yellow
    Write-Host "Please install Azure CLI from: https://aka.ms/installazurecliwindows" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Alternatively, you can check your subscription ID in Azure Portal:" -ForegroundColor Cyan
    Write-Host "1. Go to https://portal.azure.com" -ForegroundColor White
    Write-Host "2. Navigate to: Subscriptions" -ForegroundColor White
    Write-Host "3. Find your subscription and copy the Subscription ID" -ForegroundColor White
    Write-Host ""
    exit
}

Write-Host "Checking Azure login status..." -ForegroundColor Cyan
$account = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged in to Azure. Please run: az login" -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "=== Current Azure Subscription ===" -ForegroundColor Green
az account show --output table

Write-Host ""
Write-Host "=== All Available Subscriptions ===" -ForegroundColor Green
az account list --output table

Write-Host ""
Write-Host "=== Subscription ID from your connection ===" -ForegroundColor Cyan
Write-Host "From the test response, your subscription ID is: b80e9168-f3ac-4c55-9260-356cdf0233e0" -ForegroundColor Yellow
Write-Host ""
Write-Host "Compare this with the subscription IDs above to verify it matches." -ForegroundColor White
Write-Host ""

# Check VMs in the subscription
Write-Host "=== Checking VMs in subscription b80e9168-f3ac-4c55-9260-356cdf0233e0 ===" -ForegroundColor Cyan
Write-Host ""

az account set --subscription "b80e9168-f3ac-4c55-9260-356cdf0233e0" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Listing VMs (including stopped/deallocated):" -ForegroundColor Green
    az vm list --subscription "b80e9168-f3ac-4c55-9260-356cdf0233e0" --output table --show-details 2>&1
    
    Write-Host ""
    Write-Host "If no VMs are listed above, check:" -ForegroundColor Yellow
    Write-Host "1. You're looking at the correct subscription" -ForegroundColor White
    Write-Host "2. VMs exist in this subscription (even if stopped)" -ForegroundColor White
    Write-Host "3. Your account has permission to view VMs" -ForegroundColor White
} else {
    Write-Host "Could not access subscription. Check permissions." -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Service Principal Permissions Check ===" -ForegroundColor Cyan
Write-Host "To check if your service principal has 'Reader' role:" -ForegroundColor White
Write-Host "1. Go to Azure Portal: https://portal.azure.com" -ForegroundColor White
Write-Host "2. Navigate to: Subscriptions -> Your Subscription -> Access control (IAM)" -ForegroundColor White
Write-Host "3. Look for your service principal (Client ID) in the role assignments" -ForegroundColor White
Write-Host "4. It should have 'Reader' role (or 'Contributor'/'Owner' which includes Reader)" -ForegroundColor White
Write-Host ""



