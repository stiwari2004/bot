#!/bin/bash
# Script to apply performance indexes to database in Docker container
# Usage: ./apply_performance_indexes_docker.sh [container_name] [database_name]

set -e

CONTAINER_NAME="${1:-bot-dev-postgres}"
DB_NAME="${2:-troubleshooting_ai_dev}"
DB_USER="${3:-postgres}"

echo "Applying performance indexes to database: $DB_NAME"
echo "Container: $CONTAINER_NAME, User: $DB_USER"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: Container '$CONTAINER_NAME' is not running."
    echo "Available containers:"
    docker ps --format '{{.Names}}'
    exit 1
fi

# Copy SQL file into container (if not already there)
echo "Copying SQL file into container..."
docker cp backend/sql/add_performance_indexes.sql ${CONTAINER_NAME}:/tmp/add_performance_indexes.sql

# Execute SQL script inside container
echo "Executing SQL script..."
docker exec -i ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -f /tmp/add_performance_indexes.sql

if [ $? -eq 0 ]; then
    echo "✅ Performance indexes applied successfully!"
    # Clean up
    docker exec ${CONTAINER_NAME} rm -f /tmp/add_performance_indexes.sql
else
    echo "❌ Failed to apply performance indexes"
    exit 1
fi
