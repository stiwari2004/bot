#!/bin/bash
# Script to apply performance indexes to database
# Usage: ./apply_performance_indexes.sh [database_name] [host] [port] [user]

set -e

DB_NAME="${1:-troubleshooting_ai_dev}"
DB_HOST="${2:-localhost}"
DB_PORT="${3:-5432}"
DB_USER="${4:-postgres}"

echo "Applying performance indexes to database: $DB_NAME"
echo "Host: $DB_HOST, Port: $DB_PORT, User: $DB_USER"

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "Error: psql command not found. Please install PostgreSQL client."
    exit 1
fi

# Apply indexes
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f backend/sql/add_performance_indexes.sql

if [ $? -eq 0 ]; then
    echo "✅ Performance indexes applied successfully!"
else
    echo "❌ Failed to apply performance indexes"
    exit 1
fi
