#!/bin/bash
# Check frontend connectivity configuration

echo "=========================================="
echo "Frontend Connectivity Check"
echo "=========================================="
echo ""

echo "1. Checking environment variables..."
docker exec bot-dev-frontend env | grep -E "DOCKER|API|NEXT"

echo ""
echo "2. Checking if frontend can reach backend..."
docker exec bot-dev-frontend node -e "
const http = require('http');
const options = {
  hostname: 'backend',
  port: 8000,
  path: '/health',
  method: 'GET',
  timeout: 5000
};

const req = http.request(options, (res) => {
  console.log('Status:', res.statusCode);
  res.on('data', (d) => {
    process.stdout.write(d);
  });
  res.on('end', () => {
    console.log('\n✅ Frontend can reach backend!');
  });
});

req.on('error', (e) => {
  console.error('❌ Error:', e.message);
  console.error('   Cannot reach backend at backend:8000');
});

req.on('timeout', () => {
  console.error('❌ Timeout connecting to backend');
  req.destroy();
});

req.end();
"

echo ""
echo "3. Checking Next.js config (internalApiBase)..."
docker exec bot-dev-frontend node -e "
const isDocker = process.env.IN_DOCKER === '1' || process.env.IN_DOCKER === 'true' || process.env.DOCKER === '1';
const internalApiBase = process.env.NEXT_INTERNAL_API_BASE_URL || (isDocker ? 'http://backend:8000' : 'http://localhost:8000');
console.log('isDocker:', isDocker);
console.log('DOCKER env:', process.env.DOCKER);
console.log('IN_DOCKER env:', process.env.IN_DOCKER);
console.log('internalApiBase:', internalApiBase);
"

echo ""
echo "4. Checking frontend logs for errors..."
docker-compose -f docker-compose.dev.yml logs frontend --tail=30 | grep -i "error\|warn\|rewrite\|proxy" || echo "No obvious errors in recent logs"

echo ""
echo "=========================================="
