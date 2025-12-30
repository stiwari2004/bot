#!/bin/bash
# Check if license-plans page is properly built in Next.js

echo "=== Checking Frontend Build ==="
echo ""

# 1. Check if page file exists in container
echo "1. Checking if page.tsx exists in container..."
docker-compose -f docker-compose.production.yml exec frontend test -f /app/src/app/super-admin/license-plans/page.tsx && echo "   ✅ page.tsx exists" || echo "   ❌ page.tsx missing"

# 2. Check if it's in the built .next directory
echo ""
echo "2. Checking if page is in .next build directory..."
docker-compose -f docker-compose.production.yml exec frontend find /app/.next -name "*license-plans*" -o -name "*license*" 2>/dev/null | head -10

# 3. Check if super-admin page has the navigation link
echo ""
echo "3. Checking super-admin page for license-plans link..."
docker-compose -f docker-compose.production.yml exec frontend grep -n "license-plans\|License Plans" /app/src/app/super-admin/page.tsx 2>/dev/null | head -5

# 4. Check API config
echo ""
echo "4. Checking API config for license plans endpoints..."
docker-compose -f docker-compose.production.yml exec frontend grep -n "licensePlans\|license-plans" /app/src/lib/api-config.ts 2>/dev/null | head -5

# 5. Check frontend logs for build errors
echo ""
echo "5. Checking frontend logs for errors..."
docker-compose -f docker-compose.production.yml logs frontend 2>&1 | grep -i "error\|failed\|license" | tail -10

# 6. Check when the container was last built
echo ""
echo "6. Checking container build time..."
docker inspect bot_frontend_1 --format='{{.Created}}' 2>/dev/null

# 7. Check if Next.js routes are registered
echo ""
echo "7. Checking Next.js route manifest..."
docker-compose -f docker-compose.production.yml exec frontend cat /app/.next/routes-manifest.json 2>/dev/null | grep -i "license\|super-admin" | head -5 || echo "   Routes manifest not found or not readable"

