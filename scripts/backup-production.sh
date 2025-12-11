#!/bin/bash
# Automated backup script for production database
# Run daily via cron: 0 2 * * * /opt/troubleshooting-ai-demo/scripts/backup-production.sh

set -e

APP_DIR="/opt/troubleshooting-ai-demo"
COMPOSE_FILE="docker-compose.production.yml"
BACKUP_DIR="$APP_DIR/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/demo_data_backup_${TIMESTAMP}.sql"
RETENTION_DAYS=7

# Create backups directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

cd "$APP_DIR"

echo "🔄 Starting automated backup..."
echo "📦 Backup file: $BACKUP_FILE"

# Check if postgres is running
if ! docker compose -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
    echo "❌ Error: PostgreSQL container is not running"
    exit 1
fi

# Create database backup
echo "📥 Exporting database..."
docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U postgres troubleshooting_ai > "$BACKUP_FILE"

# Verify backup
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file was not created"
    exit 1
fi

FILE_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
if [ "$FILE_SIZE" -lt 1000 ]; then
    echo "❌ Error: Backup file is too small (${FILE_SIZE} bytes)"
    exit 1
fi

# Compress backup
echo "🗜️  Compressing backup..."
gzip "$BACKUP_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Clean up old backups (keep last 7 days)
echo "🧹 Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "demo_data_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup completed successfully!"
echo "📊 File size: $(du -h "$BACKUP_FILE" | cut -f1)"
echo "📍 Location: $BACKUP_FILE"

# Optional: Upload to remote storage (S3, etc.)
# aws s3 cp "$BACKUP_FILE" s3://your-bucket/backups/

