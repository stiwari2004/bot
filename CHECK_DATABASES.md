# Database Consistency Check

## Problem
Multiple databases named `troubleshooting_ai` exist with different data:
- One shows 2 super_admin users
- Another shows 3 super_admin users

## Diagnostic Commands

Run these commands to identify all databases:

```bash
# 1. Check all PostgreSQL containers
docker ps -a --filter "name=postgres" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# 2. Check production database (bot-prod-postgres)
docker exec bot-prod-postgres psql -U postgres -c "\l" | grep troubleshooting_ai
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT COUNT(*) as total FROM users WHERE role = 'super_admin';"
docker exec bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT id, email, role, tenant_id FROM users WHERE role = 'super_admin' ORDER BY id;"

# 3. Check development database (bot-dev-postgres)
docker exec bot-dev-postgres psql -U postgres -c "\l" | grep troubleshooting
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT COUNT(*) as total FROM users WHERE role = 'super_admin';"
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, role, tenant_id FROM users WHERE role = 'super_admin' ORDER BY id;"

# 4. Check if troubleshooting_ai exists in dev container (shouldn't, but checking)
docker exec bot-dev-postgres psql -U postgres -d troubleshooting_ai -c "SELECT COUNT(*) FROM users WHERE role = 'super_admin';" 2>&1

# 5. Check which database backend containers are connecting to
docker exec bot-prod-backend env | grep DATABASE_URL
docker exec bot-dev-backend env | grep DATABASE_URL

# 6. Run the diagnostic script
chmod +x check_databases.sh
./check_databases.sh
```

## Expected Configuration

- **Production**: `bot-prod-postgres` → Database: `troubleshooting_ai`
- **Development**: `bot-dev-postgres` → Database: `troubleshooting_ai_dev`

## Next Steps

After identifying which databases have which users:
1. Determine which is the "correct" database (likely production)
2. Check if frontend is connecting to wrong database
3. Merge or sync user data if needed
4. Remove duplicate databases if they exist
