#!/bin/bash
# Test if API connectivity actually works

echo "Testing API connectivity..."
echo ""

echo "1. Test /health (should work)..."
curl -s http://localhost:3005/health | jq . || curl -s http://localhost:3005/health

echo ""
echo ""
echo "2. Test /api/v1/auth/login (should get 422 Unprocessable Entity, not 404)..."
curl -s -X POST http://localhost:3005/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=test" | jq . || curl -s -X POST http://localhost:3005/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=test"

echo ""
echo ""
echo "3. Test backend directly (for comparison)..."
curl -s http://localhost:8001/health | jq . || curl -s http://localhost:8001/health

echo ""
echo ""
echo "✅ If you see responses (even 422 errors), the proxy IS working!"
echo "❌ If you see connection refused or timeouts, there's a connectivity issue"
