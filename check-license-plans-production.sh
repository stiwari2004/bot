#!/bin/bash
# Diagnostic script to check License Plans setup in production

echo "=== License Plans Production Diagnostic ==="
echo ""

# 1. Check if license-plans page exists
echo "1. Checking if license-plans page file exists..."
LICENSE_PAGE_PATH="frontend-nextjs/src/app/super-admin/license-plans/page.tsx"
if [ -f "$LICENSE_PAGE_PATH" ]; then
    echo "   ✅ License plans page exists: $LICENSE_PAGE_PATH"
    FILE_SIZE=$(stat -f%z "$LICENSE_PAGE_PATH" 2>/dev/null || stat -c%s "$LICENSE_PAGE_PATH" 2>/dev/null || echo "unknown")
    echo "   File size: $FILE_SIZE bytes"
else
    echo "   ❌ License plans page NOT FOUND: $LICENSE_PAGE_PATH"
    echo "   → File is missing! Need to pull from git or check git status"
fi

echo ""

# 2. Check if navigation link exists in super-admin page
echo "2. Checking super-admin dashboard for license plans link..."
SUPER_ADMIN_PAGE="frontend-nextjs/src/app/super-admin/page.tsx"
if [ -f "$SUPER_ADMIN_PAGE" ]; then
    if grep -q "license-plans\|License Plans" "$SUPER_ADMIN_PAGE"; then
        echo "   ✅ License Plans link found in super-admin page"
        MATCH_COUNT=$(grep -o "license-plans\|License Plans" "$SUPER_ADMIN_PAGE" | wc -l)
        echo "   Found $MATCH_COUNT references"
    else
        echo "   ❌ License Plans link NOT FOUND in super-admin page"
    fi
else
    echo "   ❌ Super admin page not found: $SUPER_ADMIN_PAGE"
fi

echo ""

# 3. Check API config for license plans endpoints
echo "3. Checking API config for license plans endpoints..."
API_CONFIG_PATH="frontend-nextjs/src/lib/api-config.ts"
if [ -f "$API_CONFIG_PATH" ]; then
    if grep -q "licensePlans\|license-plans" "$API_CONFIG_PATH"; then
        echo "   ✅ License plans endpoints found in API config"
    else
        echo "   ❌ License plans endpoints NOT FOUND in API config"
    fi
else
    echo "   ❌ API config not found: $API_CONFIG_PATH"
fi

echo ""

# 4. Check if frontend container is running
echo "4. Checking frontend container status..."
FRONTEND_STATUS=$(docker-compose -f docker-compose.production.yml ps frontend 2>&1)
if echo "$FRONTEND_STATUS" | grep -q "Up\|running"; then
    echo "   ✅ Frontend container is running"
    echo "$FRONTEND_STATUS"
else
    echo "   ❌ Frontend container is NOT running"
    echo "$FRONTEND_STATUS"
fi

echo ""

# 5. Check frontend build logs for errors
echo "5. Checking recent frontend build logs..."
BUILD_LOGS=$(docker-compose -f docker-compose.production.yml logs frontend --tail 50 2>&1 | grep -i "error\|failed\|license" || echo "No errors found")
if [ "$BUILD_LOGS" != "No errors found" ]; then
    echo "   Found relevant log entries:"
    echo "$BUILD_LOGS" | sed 's/^/   /'
else
    echo "   No errors found in recent logs"
fi

echo ""

# 6. Check if the built page exists in .next directory
echo "6. Checking if license-plans is in the built output..."
NEXT_BUILD_PATH="frontend-nextjs/.next"
if [ -d "$NEXT_BUILD_PATH" ]; then
    echo "   ✅ .next build directory exists"
    
    # Check for the route in various possible locations
    FOUND=false
    for path in "$NEXT_BUILD_PATH/server/app/super-admin/license-plans" \
                "$NEXT_BUILD_PATH/static/chunks/app/super-admin/license-plans" \
                "$NEXT_BUILD_PATH/server/app/super-admin/license-plans/page.js"; do
        if [ -e "$path" ]; then
            echo "   ✅ Found built route: $path"
            FOUND=true
        fi
    done
    
    if [ "$FOUND" = false ]; then
        echo "   ⚠️  License plans route not found in .next directory"
        echo "   → This might mean the page wasn't included in the build"
    fi
else
    echo "   ⚠️  .next build directory not found (might be in container)"
fi

echo ""

# 7. Check git status to see if files are committed
echo "7. Checking git status for license-plans files..."
GIT_STATUS=$(git status --porcelain 2>&1 | grep -i "license-plans\|licensePlans" || echo "")
if [ -n "$GIT_STATUS" ]; then
    echo "   ⚠️  Uncommitted changes found:"
    echo "$GIT_STATUS" | sed 's/^/   /'
else
    echo "   ✅ No uncommitted license-plans changes"
fi

echo ""

# 8. Check if files are actually in the git repository
echo "8. Checking if license-plans files are tracked in git..."
GIT_FILES=$(git ls-files | grep -i "license-plans" || echo "")
if [ -n "$GIT_FILES" ]; then
    echo "   ✅ License plans files are tracked in git:"
    echo "$GIT_FILES" | sed 's/^/   /'
else
    echo "   ❌ License plans files are NOT tracked in git!"
    echo "   → Files might not have been committed and pushed"
fi

echo ""
echo "=== Summary ==="
echo "If files are missing or not in git, you need to:"
echo "1. Commit the license-plans files: git add frontend-nextjs/src/app/super-admin/license-plans/"
echo "2. Commit the API config changes: git add frontend-nextjs/src/lib/api-config.ts"
echo "3. Commit the super-admin page changes: git add frontend-nextjs/src/app/super-admin/page.tsx"
echo "4. Push to remote: git push origin main"
echo "5. Pull on production: git pull origin main"
echo "6. Rebuild frontend: docker-compose -f docker-compose.production.yml build --no-cache frontend"
echo "7. Restart frontend: docker-compose -f docker-compose.production.yml up -d frontend"

