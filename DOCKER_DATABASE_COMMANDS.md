# Docker Database Commands - Quick Reference

## Your Setup
- **Container Name**: Find with `docker ps | grep postgres` 
  - **Dev**: `bot-dev-postgres` → Database: `troubleshooting_ai_dev`
  - **Prod**: `bot-prod-postgres` → Database: `troubleshooting_ai`
- **User**: `postgres`
- **Password**: `fJ0_90Zat_PbKGcgdrsw-1`

---

## Step 1: Find Container Name
```bash
docker ps | grep postgres
```

**Expected output:**
```
CONTAINER ID   IMAGE                    STATUS         NAMES
abc123def456   postgres:15             Up 2 hours     bot-prod-postgres
```

---

## Step 2: Test Connection
```bash
# Replace CONTAINER_NAME with your actual container name
docker exec -i CONTAINER_NAME psql -U postgres -d postgres -c "SELECT version();"
```

**Example:**
```bash
docker exec -i bot-prod-postgres psql -U postgres -d postgres -c "SELECT version();"
```

---

## Step 3: Check if Database Exists
```bash
docker exec -i CONTAINER_NAME psql -U postgres -d postgres -c "\l"
```

**Look for `troubleshooting_ai` in the output.**

**Example:**
```bash
docker exec -i bot-prod-postgres psql -U postgres -d postgres -c "\l"
```

---

## Step 4: Verify Connection to Your Database

**For DEV environment:**
```bash
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT current_database();"
```

**For PROD environment:**
```bash
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT current_database();"
```

**Expected output (DEV):**
```
 current_database 
-------------------
 troubleshooting_ai_dev
(1 row)
```

**Expected output (PROD):**
```
 current_database 
-------------------
 troubleshooting_ai
(1 row)
```

---

## Step 5: Run Migration

### Option A: Copy file into container (Recommended)
```bash
# Copy SQL file into container
docker cp backend/sql/create_scheduled_reports_table.sql CONTAINER_NAME:/tmp/create_scheduled_reports_table.sql

# Run migration
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -f /tmp/create_scheduled_reports_table.sql

# Clean up (optional)
docker exec -i CONTAINER_NAME rm /tmp/create_scheduled_reports_table.sql
```

**Example:**
```bash
docker cp backend/sql/create_scheduled_reports_table.sql bot-prod-postgres:/tmp/create_scheduled_reports_table.sql
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -f /tmp/create_scheduled_reports_table.sql
```

### Option B: Pipe from host (if file accessible)
```bash
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai < backend/sql/create_scheduled_reports_table.sql
```

---

## Step 6: Verify Migration Succeeded

**For DEV environment:**
```bash
# Check table exists
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\d scheduled_reports"

# Check enum types
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\dT+ reportfrequency"
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\dT+ reportformat"
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\dT+ reporttype"
```

**For PROD environment:**
```bash
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "\d scheduled_reports"
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "\dT+ reportfrequency"
```

---

## Complete Example (Copy-Paste Ready)

### For DEV Environment (`bot-dev-postgres` → `troubleshooting_ai_dev`):

```bash
# 1. Find container
docker ps | grep postgres

# 2. Test connection
docker exec -i bot-dev-postgres psql -U postgres -d postgres -c "SELECT version();"

# 3. Check databases
docker exec -i bot-dev-postgres psql -U postgres -d postgres -c "\l"

# 4. Verify troubleshooting_ai_dev database
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT current_database();"

# 5. Check if SQL file exists on server
ls -la backend/sql/create_scheduled_reports_table.sql

# 6. Run migration (if file exists)
docker cp backend/sql/create_scheduled_reports_table.sql bot-dev-postgres:/tmp/create_scheduled_reports_table.sql
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -f /tmp/create_scheduled_reports_table.sql

# 7. Verify migration
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\d scheduled_reports"
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\dT+ reportfrequency"
```

### For PROD Environment (`bot-prod-postgres` → `troubleshooting_ai`):

```bash
# Same steps but use bot-prod-postgres and troubleshooting_ai
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT current_database();"
docker cp backend/sql/create_scheduled_reports_table.sql bot-prod-postgres:/tmp/create_scheduled_reports_table.sql
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -f /tmp/create_scheduled_reports_table.sql
```

---

## Troubleshooting

### Container not found?
```bash
# List all containers (including stopped)
docker ps -a | grep postgres

# Start container if stopped
docker start CONTAINER_NAME
```

### Permission denied?
```bash
# Make sure you're running from the project root directory
cd /path/to/bot

# Verify SQL file exists
ls -la backend/sql/create_scheduled_reports_table.sql
```

### Database doesn't exist?
```bash
# Create it
docker exec -i CONTAINER_NAME psql -U postgres -d postgres -c "CREATE DATABASE troubleshooting_ai;"
```

---

## Notes
- Replace `CONTAINER_NAME` with your actual container name (e.g., `bot-prod-postgres`)
- All commands assume you're in the project root directory
- The password is not needed in commands as it's set in the container environment
