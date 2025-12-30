#!/bin/bash
# Verify license-plans UI is accessible

echo "=== Verifying License Plans UI ==="
echo ""

# 1. Check if the page file exists
echo "1. Page file exists:"
docker-compose -f docker-compose.production.yml exec frontend test -f /app/src/app/super-admin/license-plans/page.tsx && echo "   ✅ YES" || echo "   ❌ NO"

# 2. Check if super-admin page has the button
echo ""
echo "2. Navigation button in super-admin page:"
docker-compose -f docker-compose.production.yml exec frontend grep -c "license-plans" /app/src/app/super-admin/page.tsx 2>/dev/null && echo "   ✅ YES" || echo "   ❌ NO"

# 3. Check if SparklesIcon is imported (needed for the button icon)
echo ""
echo "3. SparklesIcon import check:"
docker-compose -f docker-compose.production.yml exec frontend grep -q "SparklesIcon" /app/src/app/super-admin/page.tsx 2>/dev/null && echo "   ✅ YES" || echo "   ❌ NO"

# 4. Check Next.js build output
echo ""
echo "4. Checking if page is in Next.js build:"
docker-compose -f docker-compose.production.yml exec frontend find /app/.next -type f -name "*license*" 2>/dev/null | head -5
if [ $? -eq 0 ]; then
    echo "   ✅ Found in build"
else
    echo "   ⚠️  Not found in build (might need rebuild)"
fi

# 5. Check if the route is registered
echo ""
echo "5. Checking route registration:"
docker-compose -f docker-compose.production.yml exec frontend cat /app/.next/server/app-paths-manifest.json 2>/dev/null | grep -i "license" || echo "   ⚠️  Route not found in manifest"

# 6. Check frontend container logs for runtime errors
echo ""
echo "6. Recent frontend errors:"
docker-compose -f docker-compose.production.yml logs frontend 2>&1 | tail -30 | grep -i "error\|warn\|license" || echo "   No errors found"

# 7. Force rebuild suggestion
echo ""
echo "=== Next Steps ==="
echo "If the page isn't showing, try:"
echo "1. docker-compose -f docker-compose.production.yml stop frontend"
echo "2. docker-compose -f docker-compose.production.yml rm -f frontend"
echo "3. docker-compose -f docker-compose.production.yml build --no-cache frontend"
echo "4. docker-compose -f docker-compose.production.yml up -d frontend"
echo ""
echo "Or check browser console for JavaScript errors when accessing /super-admin"

