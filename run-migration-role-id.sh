#!/bin/bash
# Run migration to add role_id column to users table

echo "=== Running Migration: Add role_id to users table ==="
echo ""

# Run the migration SQL
docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai < backend/sql/add_role_id_to_users.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo ""
    echo "Verifying column exists..."
    docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -c "\d users" | grep role_id
else
    echo ""
    echo "❌ Migration failed!"
    exit 1
fi

