#!/bin/bash
# Comprehensive diagnostic script for production database sequence issue
# Run this on the production server to understand the root cause

set -e

echo "=== PRODUCTION DIAGNOSTIC SCRIPT ==="
echo ""

echo "1. Checking current code version..."
cd /opt/opsbot/bot
echo "Current branch: $(git branch --show-current)"
echo "Current commit: $(git rev-parse HEAD)"
echo "Latest commit message: $(git log -1 --pretty=%B)"
echo ""

echo "2. Checking database.py line 117 (where error occurs)..."
if grep -q "Base.metadata.create_all(bind=engine)" backend/app/core/database.py; then
    echo "❌ OLD CODE DETECTED: Line 117 calls create_all directly without try-except"
    grep -n "Base.metadata.create_all" backend/app/core/database.py | head -3
else
    echo "✅ NEW CODE DETECTED: Has error handling"
    grep -n "try:" backend/app/core/database.py | grep -A 2 "create_all" | head -5
fi
echo ""

echo "3. Checking database state..."
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "
SELECT 
    CASE WHEN EXISTS (SELECT 1 FROM pg_class WHERE relname = 'parameter_tunings_id_seq' AND relkind = 'S') 
         THEN 'EXISTS' ELSE 'NOT EXISTS' END as sequence_status,
    CASE WHEN EXISTS (SELECT 1 FROM pg_class WHERE relname = 'parameter_tunings' AND relkind = 'r') 
         THEN 'EXISTS' ELSE 'NOT EXISTS' END as table_status;
"
echo ""

echo "4. Checking for orphaned sequences..."
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "
SELECT 
    s.relname as sequence_name,
    CASE WHEN t.relname IS NULL THEN 'ORPHANED' ELSE 'LINKED' END as status
FROM pg_class s
LEFT JOIN pg_depend d ON d.objid = s.oid
LEFT JOIN pg_class t ON d.refobjid = t.oid AND t.relkind = 'r'
WHERE s.relkind = 'S' 
AND s.relname LIKE '%_id_seq'
AND s.relname = 'parameter_tunings_id_seq';
"
echo ""

echo "5. Checking if code has been pulled..."
echo "Git status:"
git status --short | head -10
echo ""

echo "=== DIAGNOSIS COMPLETE ==="
echo ""
echo "RECOMMENDED FIXES:"
echo ""
echo "If OLD CODE detected:"
echo "  1. git pull origin dev  (or git pull origin main)"
echo "  2. docker-compose -f docker-compose.production.yml -p bot-prod build --no-cache backend"
echo "  3. docker-compose -f docker-compose.production.yml -p bot-prod up -d"
echo ""
echo "If ORPHANED SEQUENCE detected:"
echo "  docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c \"DROP SEQUENCE IF EXISTS parameter_tunings_id_seq CASCADE;\""
echo "  docker-compose -f docker-compose.production.yml -p bot-prod restart backend"
echo ""
