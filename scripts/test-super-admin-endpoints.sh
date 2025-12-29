#!/bin/bash
# Quick test script to check if super-admin endpoints are registered

echo "🔍 Testing Super Admin Endpoints"
echo "================================="
echo ""

# Test 1: Check if overview endpoint exists (should return 401, not 404)
echo "📋 Test 1: Checking /api/v1/super-admin/overview"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/super-admin/overview 2>/dev/null)
if [ "$RESPONSE" = "401" ]; then
    echo "   ✅ Endpoint exists (401 = needs authentication)"
elif [ "$RESPONSE" = "404" ]; then
    echo "   ❌ Endpoint NOT FOUND (404)"
    echo "   → Backend may need to be rebuilt or there's an import error"
else
    echo "   ⚠️  Unexpected response: $RESPONSE"
fi
echo ""

# Test 2: Check if tenants endpoint exists
echo "📋 Test 2: Checking /api/v1/super-admin/tenants"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/super-admin/tenants 2>/dev/null)
if [ "$RESPONSE" = "401" ]; then
    echo "   ✅ Endpoint exists (401 = needs authentication)"
elif [ "$RESPONSE" = "404" ]; then
    echo "   ❌ Endpoint NOT FOUND (404)"
else
    echo "   ⚠️  Unexpected response: $RESPONSE"
fi
echo ""

# Test 3: Check backend logs for super-admin related messages
echo "📋 Test 3: Checking backend logs for super-admin messages"
echo "   (Looking for 'super-admin' or 'super_admin' in logs)"
docker-compose -f docker-compose.production.yml logs backend 2>/dev/null | grep -i "super" | tail -5
if [ $? -ne 0 ]; then
    echo "   ⚠️  No super-admin related messages found in logs"
fi
echo ""

# Test 4: Check for import errors
echo "📋 Test 4: Checking for import/loading errors"
ERRORS=$(docker-compose -f docker-compose.production.yml logs backend 2>/dev/null | grep -i "error.*super\|import.*super\|super.*error" | tail -5)
if [ -n "$ERRORS" ]; then
    echo "   ⚠️  Found errors:"
    echo "$ERRORS" | sed 's/^/      /'
else
    echo "   ✅ No obvious errors found"
fi
echo ""

echo "💡 If endpoints return 404, try:"
echo "   1. Rebuild backend: docker-compose -f docker-compose.production.yml build backend"
echo "   2. Restart backend: docker-compose -f docker-compose.production.yml restart backend"
echo "   3. Check logs: docker-compose -f docker-compose.production.yml logs backend | grep -i error"
echo ""



