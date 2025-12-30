# Diagnostic script to check License Plans setup in production
Write-Host "=== License Plans Production Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check if license-plans page exists
Write-Host "1. Checking if license-plans page file exists..." -ForegroundColor Yellow
$licensePagePath = "frontend-nextjs/src/app/super-admin/license-plans/page.tsx"
if (Test-Path $licensePagePath) {
    Write-Host "   ✅ License plans page exists: $licensePagePath" -ForegroundColor Green
    $fileSize = (Get-Item $licensePagePath).Length
    Write-Host "   File size: $fileSize bytes" -ForegroundColor Gray
} else {
    Write-Host "   ❌ License plans page NOT FOUND: $licensePagePath" -ForegroundColor Red
    Write-Host "   → File is missing! Need to pull from git or check git status" -ForegroundColor Yellow
}

Write-Host ""

# 2. Check if navigation link exists in super-admin page
Write-Host "2. Checking super-admin dashboard for license plans link..." -ForegroundColor Yellow
$superAdminPage = "frontend-nextjs/src/app/super-admin/page.tsx"
if (Test-Path $superAdminPage) {
    $content = Get-Content $superAdminPage -Raw
    if ($content -match "license-plans|License Plans") {
        Write-Host "   ✅ License Plans link found in super-admin page" -ForegroundColor Green
        $matches = [regex]::Matches($content, "license-plans|License Plans")
        Write-Host "   Found $($matches.Count) references" -ForegroundColor Gray
    } else {
        Write-Host "   ❌ License Plans link NOT FOUND in super-admin page" -ForegroundColor Red
    }
} else {
    Write-Host "   ❌ Super admin page not found: $superAdminPage" -ForegroundColor Red
}

Write-Host ""

# 3. Check API config for license plans endpoints
Write-Host "3. Checking API config for license plans endpoints..." -ForegroundColor Yellow
$apiConfigPath = "frontend-nextjs/src/lib/api-config.ts"
if (Test-Path $apiConfigPath) {
    $content = Get-Content $apiConfigPath -Raw
    if ($content -match "licensePlans|license-plans") {
        Write-Host "   ✅ License plans endpoints found in API config" -ForegroundColor Green
    } else {
        Write-Host "   ❌ License plans endpoints NOT FOUND in API config" -ForegroundColor Red
    }
} else {
    Write-Host "   ❌ API config not found: $apiConfigPath" -ForegroundColor Red
}

Write-Host ""

# 4. Check if frontend container is running
Write-Host "4. Checking frontend container status..." -ForegroundColor Yellow
$frontendStatus = docker-compose -f docker-compose.production.yml ps frontend 2>&1
if ($frontendStatus -match "Up|running") {
    Write-Host "   ✅ Frontend container is running" -ForegroundColor Green
    Write-Host $frontendStatus
} else {
    Write-Host "   ❌ Frontend container is NOT running" -ForegroundColor Red
    Write-Host $frontendStatus
}

Write-Host ""

# 5. Check frontend build logs for errors
Write-Host "5. Checking recent frontend build logs..." -ForegroundColor Yellow
$buildLogs = docker-compose -f docker-compose.production.yml logs frontend --tail 50 2>&1 | Select-String -Pattern "error|Error|ERROR|failed|Failed|license" -Context 0,2
if ($buildLogs) {
    Write-Host "   Found relevant log entries:" -ForegroundColor Yellow
    $buildLogs | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
} else {
    Write-Host "   No errors found in recent logs" -ForegroundColor Green
}

Write-Host ""

# 6. Check if the built page exists in .next directory
Write-Host "6. Checking if license-plans is in the built output..." -ForegroundColor Yellow
$nextBuildPath = "frontend-nextjs/.next"
if (Test-Path $nextBuildPath) {
    Write-Host "   ✅ .next build directory exists" -ForegroundColor Green
    
    # Check for the route in various possible locations
    $possiblePaths = @(
        "$nextBuildPath/server/app/super-admin/license-plans",
        "$nextBuildPath/static/chunks/app/super-admin/license-plans",
        "$nextBuildPath/server/app/super-admin/license-plans/page.js"
    )
    
    $found = $false
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            Write-Host "   ✅ Found built route: $path" -ForegroundColor Green
            $found = $true
        }
    }
    
    if (-not $found) {
        Write-Host "   ⚠️  License plans route not found in .next directory" -ForegroundColor Yellow
        Write-Host "   → This might mean the page wasn't included in the build" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️  .next build directory not found (might be in container)" -ForegroundColor Yellow
}

Write-Host ""

# 7. Check git status to see if files are committed
Write-Host "7. Checking git status for license-plans files..." -ForegroundColor Yellow
$gitStatus = git status --porcelain 2>&1 | Select-String -Pattern "license-plans|licensePlans"
if ($gitStatus) {
    Write-Host "   ⚠️  Uncommitted changes found:" -ForegroundColor Yellow
    $gitStatus | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
} else {
    Write-Host "   ✅ No uncommitted license-plans changes" -ForegroundColor Green
}

Write-Host ""

# 8. Check if files are actually in the git repository
Write-Host "8. Checking if license-plans files are tracked in git..." -ForegroundColor Yellow
$gitFiles = git ls-files | Select-String -Pattern "license-plans"
if ($gitFiles) {
    Write-Host "   ✅ License plans files are tracked in git:" -ForegroundColor Green
    $gitFiles | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
} else {
    Write-Host "   ❌ License plans files are NOT tracked in git!" -ForegroundColor Red
    Write-Host "   → Files might not have been committed and pushed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "If files are missing or not in git, you need to:"
Write-Host "1. Commit the license-plans files: git add frontend-nextjs/src/app/super-admin/license-plans/"
Write-Host "2. Commit the API config changes: git add frontend-nextjs/src/lib/api-config.ts"
Write-Host "3. Commit the super-admin page changes: git add frontend-nextjs/src/app/super-admin/page.tsx"
Write-Host "4. Push to remote: git push origin main"
Write-Host "5. Pull on production: git pull origin main"
Write-Host "6. Rebuild frontend: docker-compose -f docker-compose.production.yml build --no-cache frontend"
Write-Host "7. Restart frontend: docker-compose -f docker-compose.production.yml up -d frontend"

