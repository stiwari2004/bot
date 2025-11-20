# PowerShell script to test Azure discovery and diagnose issues
# Run this after fixing the Client Secret to verify everything works

Write-Host "=== Azure Discovery Diagnostic Script ===" -ForegroundColor Cyan
Write-Host ""

# Check if Azure CLI is installed
$azInstalled = Get-Command az -ErrorAction SilentlyContinue
if (-not $azInstalled) {
    Write-Host "Azure CLI is not installed. Installing diagnostic steps..." -ForegroundColor Yellow
    Write-Host "You can install Azure CLI from: https://aka.ms/installazurecliwindows" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "Azure CLI is installed. Running diagnostics..." -ForegroundColor Green
    Write-Host ""
}

# Your Azure details (update these if needed)
$subscriptionId = "b80e9168-f3ac-4c55-9260-356cdf0233e0"
$tenantId = "60481b61-29cc-4fe7-bfe9-24bcafff9b67"
$clientId = "b265b094-f556-4777-a066-656f069cdd0f"

Write-Host "=== Step 1: Test Service Principal Authentication ===" -ForegroundColor Cyan
Write-Host "To test authentication, you need to provide your Client Secret Value." -ForegroundColor White
Write-Host "This is the long string (not the GUID Secret ID)." -ForegroundColor White
Write-Host ""
$testAuth = Read-Host "Do you want to test authentication now? (y/n)"

if ($testAuth -eq "y" -and $azInstalled) {
    $clientSecret = Read-Host "Enter your Client Secret Value (will be hidden)" -AsSecureString
    $clientSecretPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($clientSecret)
    )
    
    Write-Host ""
    Write-Host "Attempting to login with service principal..." -ForegroundColor Yellow
    
    # Convert secure string to plain text for Azure CLI (not ideal, but needed for testing)
    $env:AZURE_CLIENT_SECRET = $clientSecretPlain
    az login --service-principal -u $clientId -p $clientSecretPlain --tenant $tenantId 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Authentication successful!" -ForegroundColor Green
        Write-Host ""
        
        Write-Host "Setting subscription..." -ForegroundColor Yellow
        az account set --subscription $subscriptionId 2>&1 | Out-Null
        
        Write-Host "Listing VMs..." -ForegroundColor Yellow
        $vms = az vm list --subscription $subscriptionId --output json 2>&1 | ConvertFrom-Json
        
        if ($vms.Count -gt 0) {
            Write-Host "✓ Found $($vms.Count) VM(s):" -ForegroundColor Green
            $vms | ForEach-Object {
                Write-Host "  - $($_.name) (Resource Group: $($_.resourceGroup))" -ForegroundColor White
            }
        } else {
            Write-Host "⚠ No VMs found in subscription." -ForegroundColor Yellow
            Write-Host "  This could mean:" -ForegroundColor White
            Write-Host "  1. No VMs exist in this subscription" -ForegroundColor White
            Write-Host "  2. Service principal lacks permissions" -ForegroundColor White
            Write-Host "  3. VMs are in a different subscription" -ForegroundColor White
        }
        
        # Clean up
        Remove-Item Env:\AZURE_CLIENT_SECRET
        az logout 2>&1 | Out-Null
    } else {
        Write-Host "✗ Authentication failed!" -ForegroundColor Red
        Write-Host "  Check:" -ForegroundColor White
        Write-Host "  1. Client Secret Value is correct (not the Secret ID)" -ForegroundColor White
        Write-Host "  2. Client Secret is not expired" -ForegroundColor White
        Write-Host "  3. Service principal is enabled in Azure AD" -ForegroundColor White
    }
    Write-Host ""
} else {
    Write-Host "Skipping authentication test (Azure CLI not installed or user chose 'n')." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "=== Step 2: Check API Permissions ===" -ForegroundColor Cyan
Write-Host "1. Go to: https://portal.azure.com" -ForegroundColor White
Write-Host "2. Navigate to: Azure Active Directory → App registrations" -ForegroundColor White
Write-Host "3. Find your app (Client ID: $clientId)" -ForegroundColor White
Write-Host "4. Click: API permissions" -ForegroundColor White
Write-Host "5. Check if 'Azure Service Management' → 'user_impersonation' is listed" -ForegroundColor White
Write-Host "6. If missing, add it and GRANT ADMIN CONSENT" -ForegroundColor Yellow
Write-Host ""

Write-Host "=== Step 3: Check Resource Provider Registration ===" -ForegroundColor Cyan
Write-Host "1. Go to: https://portal.azure.com" -ForegroundColor White
Write-Host "2. Navigate to: Subscriptions → Your Subscription → Resource providers" -ForegroundColor White
Write-Host "3. Search for: Microsoft.Compute" -ForegroundColor White
Write-Host "4. Ensure status is: Registered" -ForegroundColor White
Write-Host "5. If not, click Register and wait 1-2 minutes" -ForegroundColor Yellow
Write-Host ""

Write-Host "=== Step 4: Check RBAC Permissions ===" -ForegroundColor Cyan
Write-Host "1. Go to: https://portal.azure.com" -ForegroundColor White
Write-Host "2. Navigate to: Subscriptions → Your Subscription → Access control (IAM)" -ForegroundColor White
Write-Host "3. Click: Role assignments" -ForegroundColor White
Write-Host "4. Search for your service principal (Client ID: $clientId)" -ForegroundColor White
Write-Host "5. Ensure it has: Reader, Contributor, or Owner role" -ForegroundColor White
Write-Host ""

Write-Host "=== Step 5: Test in Application ===" -ForegroundColor Cyan
Write-Host "1. Go to your application: http://localhost:3000" -ForegroundColor White
Write-Host "2. Navigate to: Settings → Infrastructure Connections" -ForegroundColor White
Write-Host "3. Click: Test on your Azure connection" -ForegroundColor White
Write-Host "4. Should show: 'Azure connection successful! Found X resource groups and Y VMs.'" -ForegroundColor Green
Write-Host "5. Click: Discover" -ForegroundColor White
Write-Host "6. Should list your VM(s)" -ForegroundColor Green
Write-Host ""

Write-Host "=== Step 6: Check Backend Logs ===" -ForegroundColor Cyan
Write-Host "If discovery still fails, check logs:" -ForegroundColor White
Write-Host ""
Write-Host "  docker-compose logs backend --tail=100 | Select-String -Pattern 'Azure API|VM|error|Error' -Context 2" -ForegroundColor Yellow
Write-Host ""
Write-Host "Look for:" -ForegroundColor White
Write-Host "  - 'Azure API returned X VMs' - tells you if Azure is returning VMs" -ForegroundColor White
Write-Host "  - Authentication errors" -ForegroundColor White
Write-Host "  - Permission errors (403 Forbidden)" -ForegroundColor White
Write-Host "  - Specific error messages" -ForegroundColor White
Write-Host ""

Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Most common issues:" -ForegroundColor White
Write-Host "1. ❌ Client Secret Value (not ID) - You fixed this" -ForegroundColor White
Write-Host "2. ❌ Missing API Permissions in Azure AD - Check Step 2" -ForegroundColor Yellow
Write-Host "3. ❌ Admin consent not granted - Check Step 2" -ForegroundColor Yellow
Write-Host "4. ❌ Resource provider not registered - Check Step 3" -ForegroundColor Yellow
Write-Host "5. ❌ RBAC permissions missing - Check Step 4" -ForegroundColor Yellow
Write-Host ""

Write-Host "For detailed troubleshooting, see: AZURE_API_PERMISSIONS_GUIDE.md" -ForegroundColor Cyan
Write-Host ""

