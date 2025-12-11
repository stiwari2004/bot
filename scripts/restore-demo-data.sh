#!/bin/bash
# Restore demo data to production server
# Usage: ./scripts/restore-demo-data.sh [backup_file.sql]

set -e

if [ -z "$1" ]; then
    # Find the most recent backup file
    BACKUP_FILE=$(ls -t backups/demo_data_backup_*.sql 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        echo "❌ Error: No backup file found"
        echo "   Usage: $0 [backup_file.sql]"
        echo "   Or place backup file in ./backups/ directory"
        exit 1
    fi
    echo "📦 Using most recent backup: $BACKUP_FILE"
else
    BACKUP_FILE="$1"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "🔄 Starting database restoration..."
echo "📦 Backup file: $BACKUP_FILE"

# Check if docker-compose is running
COMPOSE_FILE="docker-compose.production.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="docker-compose.yml"
fi

if ! docker compose -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
    echo "❌ Error: PostgreSQL container is not running"
    echo "   Please start it with: docker compose -f $COMPOSE_FILE up -d postgres"
    exit 1
fi

# Wait for postgres to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Check if database exists, create if not
echo "🔍 Checking database..."
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'troubleshooting_ai'" | grep -q 1 || \
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -c "CREATE DATABASE troubleshooting_ai;"

# Restore data
echo "📥 Restoring data from backup..."
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres troubleshooting_ai < "$BACKUP_FILE"

# Verify restoration
echo "✅ Verifying restoration..."
TENANT_COUNT=$(docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -t troubleshooting_ai -c "SELECT COUNT(*) FROM tenants;" | tr -d ' ')
USER_COUNT=$(docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -t troubleshooting_ai -c "SELECT COUNT(*) FROM users;" | tr -d ' ')

echo "✅ Restoration completed successfully!"
echo "📊 Tenants: $TENANT_COUNT"
echo "📊 Users: $USER_COUNT"
echo ""
echo "💡 Next steps:"
echo "   1. Verify data in the application"
echo "   2. Test login with demo@example.com"
echo "   3. Check that all demo data is visible"

