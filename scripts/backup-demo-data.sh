#!/bin/bash
# Backup demo data from local development database
# Usage: ./scripts/backup-demo-data.sh

set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="demo_data_backup_${TIMESTAMP}.sql"
BACKUP_DIR="./backups"

# Create backups directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting database backup..."
echo "📦 Backup file: $BACKUP_DIR/$BACKUP_FILE"

# Check if docker-compose is running
if ! docker-compose ps postgres | grep -q "Up"; then
    echo "❌ Error: PostgreSQL container is not running"
    echo "   Please start it with: docker-compose up -d postgres"
    exit 1
fi

# Create database backup
echo "📥 Exporting database..."
docker-compose exec -T postgres pg_dump -U postgres troubleshooting_ai > "$BACKUP_DIR/$BACKUP_FILE"

# Verify backup file was created and has content
if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file was not created"
    exit 1
fi

FILE_SIZE=$(stat -f%z "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null)
if [ "$FILE_SIZE" -lt 1000 ]; then
    echo "❌ Error: Backup file is too small (${FILE_SIZE} bytes). Backup may have failed."
    exit 1
fi

echo "✅ Backup completed successfully!"
echo "📊 File size: $(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)"
echo "📍 Location: $BACKUP_DIR/$BACKUP_FILE"
echo ""
echo "💡 To restore on server:"
echo "   scp $BACKUP_DIR/$BACKUP_FILE user@server:/opt/troubleshooting-ai-demo/"
echo "   Then run: scripts/restore-demo-data.sh on the server"

