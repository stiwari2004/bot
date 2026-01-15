# Guide to Apply Performance Indexes

## Issue
The database is running in Docker, so we need to execute the SQL script inside the Docker container.

## Solution

### Step 1: Ensure Docker Desktop is Running
1. Open Docker Desktop application
2. Wait for it to fully start (whale icon in system tray)
3. Verify containers are running:
   ```powershell
   docker ps
   ```

### Step 2: Apply Indexes Using Docker Exec

**Option A: Using docker-compose (Recommended)**
```powershell
# Copy SQL file into container
docker cp backend/sql/add_performance_indexes.sql bot-dev-postgres:/tmp/add_performance_indexes.sql

# Execute the script
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d troubleshooting_ai_dev -f /tmp/add_performance_indexes.sql
```

**Option B: Using docker exec directly**
```powershell
# Copy SQL file into container
docker cp backend/sql/add_performance_indexes.sql bot-dev-postgres:/tmp/add_performance_indexes.sql

# Execute the script
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -f /tmp/add_performance_indexes.sql
```

**Option C: Using PowerShell script**
```powershell
# Run the PowerShell script
.\backend\scripts\apply_performance_indexes.ps1
```

### Step 3: Verify Indexes Were Created

```powershell
# Check indexes on runbooks table
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\d runbooks"

# Check all indexes
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "\di"
```

### Alternative: Execute SQL Directly

If copying files doesn't work, you can pipe the SQL directly:

```powershell
Get-Content backend/sql/add_performance_indexes.sql | docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev
```

### For Production Database

If you need to apply to production:

```powershell
# For production (adjust container name)
docker cp backend/sql/add_performance_indexes.sql bot-postgres:/tmp/add_performance_indexes.sql
docker exec -i bot-postgres psql -U postgres -d troubleshooting_ai -f /tmp/add_performance_indexes.sql
```

---

## Troubleshooting

### Error: "Docker Desktop is not running"
- Start Docker Desktop application
- Wait for it to fully initialize
- Check system tray for Docker icon

### Error: "Container not found"
- Check container name: `docker ps`
- Use correct container name from the list

### Error: "Permission denied"
- Ensure you're using the correct database user (postgres)
- Check database password if required

### Error: "File not found"
- Ensure you're in the project root directory
- Verify file exists: `Test-Path backend/sql/add_performance_indexes.sql`

---

## Expected Output

When successful, you should see:
```
CREATE INDEX
CREATE INDEX
CREATE INDEX
...
ANALYZE
ANALYZE
...
✅ Performance indexes applied successfully!
```
