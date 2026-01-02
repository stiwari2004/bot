# Create Dev Admin User

## Option 1: Use the Script (Recommended)

```bash
# Create a dev admin user
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend python scripts/create_admin_user.py admin@dev.resolvify.tech dev123

# Or with custom email/password
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend python scripts/create_admin_user.py your-email@example.com your-password
```

## Option 2: Check Existing Users

```bash
# Check what users exist in dev database
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, email, role, is_active FROM users;"

# Check what tenants exist
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, name, is_active FROM tenants;"
```

## Option 3: Create Super Admin (if RBAC is enabled)

```bash
# Check if super admin script exists
docker-compose -f docker-compose.dev.yml -p bot-dev exec backend python scripts/create_super_admin.py --help
```

## About User Management

**Dev and Production are Separate:**
- ✅ **Correct Behavior**: Dev database (`troubleshooting_ai_dev`) is separate from production (`troubleshooting_ai`)
- ✅ **Super Admin Page**: Will work in dev, but only shows/manages users in the dev database
- ✅ **Isolation**: Users created in dev won't appear in production and vice versa

**This is the intended behavior** - dev should be completely isolated for testing.

