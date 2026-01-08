# Database Migration Guide
## Implementation Steps for Combined Features

This guide provides step-by-step instructions for applying all database migrations for the new features.

---

## Migration Order

Migrations must be applied in the following order due to dependencies:

### Phase 1: User Security Features
1. `add_password_reset_fields.sql` - Password reset tokens and email verification
2. `add_password_history.sql` - Password history and expiration
3. `add_account_lockout_fields.sql` - Account lockout protection

### Phase 2: Change Management
4. `create_change_tickets_table.sql` - Change ticket tracking
5. `add_ticket_suppression_fields.sql` - Ticket suppression during change windows

### Phase 3: Self-Healing
6. `add_parent_session_id_to_execution_sessions.sql` - Link remediation sessions to parent

### Phase 4: User Enhancements
7. `add_user_profile_fields.sql` - User profile information
8. `add_user_preferences.sql` - User preferences (JSONB)
9. `create_user_login_history.sql` - Login attempt tracking
10. `create_user_activity_log.sql` - User activity audit log
11. `create_user_sessions.sql` - Session management

---

## Migration Steps

### For Development Environment

```bash
# Navigate to project directory
cd /opt/opsbot/bot  # or your project path

# Connect to dev database
docker-compose -f docker-compose.dev.yml -p bot-dev exec postgres psql -U postgres -d troubleshooting_ai_dev
```

Then run each migration in order:

```sql
-- Phase 1: User Security
\i backend/sql/add_password_reset_fields.sql
\i backend/sql/add_password_history.sql
\i backend/sql/add_account_lockout_fields.sql

-- Phase 2: Change Management
\i backend/sql/create_change_tickets_table.sql
\i backend/sql/add_ticket_suppression_fields.sql

-- Phase 3: Self-Healing
\i backend/sql/add_parent_session_id_to_execution_sessions.sql

-- Phase 4: User Enhancements
\i backend/sql/add_user_profile_fields.sql
\i backend/sql/add_user_preferences.sql
\i backend/sql/create_user_login_history.sql
\i backend/sql/create_user_activity_log.sql
\i backend/sql/create_user_sessions.sql
```

### Alternative: Using cat and docker-compose (Recommended)

```bash
# Phase 1: User Security
cat backend/sql/add_password_reset_fields.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev
cat backend/sql/add_password_history.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev
cat backend/sql/add_account_lockout_fields.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev

# Phase 2: Change Management
cat backend/sql/create_change_tickets_table.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev
cat backend/sql/add_ticket_suppression_fields.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev

# Phase 3: Self-Healing
cat backend/sql/add_parent_session_id_to_execution_sessions.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev

# Phase 4: User Enhancements
cat backend/sql/add_user_profile_fields.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev
cat backend/sql/add_user_preferences.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev
cat backend/sql/create_user_login_history.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev
cat backend/sql/create_user_activity_log.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev
cat backend/sql/create_user_sessions.sql | docker-compose -f docker-compose.dev.yml -p bot-dev exec -T postgres psql -U postgres -d troubleshooting_ai_dev
```

### For Production Environment

```bash
# Phase 1: User Security
cat backend/sql/add_password_reset_fields.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai
cat backend/sql/add_password_history.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai
cat backend/sql/add_account_lockout_fields.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai

# Phase 2: Change Management
cat backend/sql/create_change_tickets_table.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai
cat backend/sql/add_ticket_suppression_fields.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai

# Phase 3: Self-Healing
cat backend/sql/add_parent_session_id_to_execution_sessions.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai

# Phase 4: User Enhancements
cat backend/sql/add_user_profile_fields.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai
cat backend/sql/add_user_preferences.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai
cat backend/sql/create_user_login_history.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai
cat backend/sql/create_user_activity_log.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai
cat backend/sql/create_user_sessions.sql | docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai
```

---

## Verification Steps

After running migrations, verify they were applied correctly:

```sql
-- Check users table has new columns
\d users

-- Check change_tickets table exists
\d change_tickets

-- Check execution_sessions has parent_session_id
\d execution_sessions

-- Check new tables exist
\dt user_login_history
\dt user_activity_log
\dt user_sessions

-- Verify indexes
\di
```

---

## What Each Migration Does

### Phase 1: User Security

**add_password_reset_fields.sql**
- Adds `password_reset_token`, `password_reset_expires`, `email_verified`, `email_verification_token` to `users` table
- Creates indexes for efficient token lookups

**add_password_history.sql**
- Adds `password_history` (JSONB), `password_expires_at`, `password_changed_at` to `users` table
- Tracks last 5 passwords to prevent reuse

**add_account_lockout_fields.sql**
- Adds `failed_login_attempts`, `locked_until`, `last_failed_login_at` to `users` table
- Enables account lockout after 5 failed attempts

### Phase 2: Change Management

**create_change_tickets_table.sql**
- Creates `change_tickets` table for tracking change windows
- Includes fields for start/end times, affected services/environments
- Creates indexes for time-based queries

**add_ticket_suppression_fields.sql**
- Adds `suppressed`, `suppressed_by_change_ticket_id`, `suppressed_at`, `suppression_reason` to `tickets` table
- Enables ticket suppression during change windows

### Phase 3: Self-Healing

**add_parent_session_id_to_execution_sessions.sql**
- Adds `parent_session_id` to `execution_sessions` table
- Links remediation sessions to their parent failed execution

### Phase 4: User Enhancements

**add_user_profile_fields.sql**
- Adds profile fields: `avatar_url`, `phone_number`, `department`, `job_title`, `timezone`, `locale` to `users` table

**add_user_preferences.sql**
- Adds `preferences` JSONB field to `users` table
- Creates GIN index for efficient preference queries

**create_user_login_history.sql**
- Creates `user_login_history` table
- Tracks all login attempts (successful and failed)

**create_user_activity_log.sql**
- Creates `user_activity_log` table
- Tracks user actions for audit purposes

**create_user_sessions.sql**
- Creates `user_sessions` table
- Tracks active sessions for token management

---

## Post-Migration Steps

1. **Restart Backend Service**
   ```bash
   # Dev
   docker-compose -f docker-compose.dev.yml -p bot-dev restart backend
   
   # Production
   docker-compose -f docker-compose.production.yml restart backend
   ```

2. **Verify Backend Starts Successfully**
   ```bash
   # Check logs
   docker-compose -f docker-compose.dev.yml -p bot-dev logs backend --tail=50
   ```

3. **Test Key Endpoints**
   - `/api/v1/auth/login` - Should work with new lockout logic
   - `/api/v1/auth/forgot-password` - Should create reset tokens
   - `/api/v1/auth/profile` - Should return profile data
   - `/api/v1/change-tickets` - Should list change tickets (empty initially)

---

## Rollback (If Needed)

If you need to rollback, you can drop the new columns/tables:

```sql
-- Phase 4: User Enhancements (reverse order)
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS user_activity_log CASCADE;
DROP TABLE IF EXISTS user_login_history CASCADE;
ALTER TABLE users DROP COLUMN IF EXISTS preferences;
ALTER TABLE users DROP COLUMN IF EXISTS timezone, locale, job_title, department, phone_number, avatar_url;

-- Phase 3: Self-Healing
ALTER TABLE execution_sessions DROP COLUMN IF EXISTS parent_session_id;

-- Phase 2: Change Management
ALTER TABLE tickets DROP COLUMN IF EXISTS suppressed, suppressed_by_change_ticket_id, suppressed_at, suppression_reason;
DROP TABLE IF EXISTS change_tickets CASCADE;

-- Phase 1: User Security
ALTER TABLE users DROP COLUMN IF EXISTS failed_login_attempts, locked_until, last_failed_login_at;
ALTER TABLE users DROP COLUMN IF EXISTS password_history, password_expires_at, password_changed_at;
ALTER TABLE users DROP COLUMN IF EXISTS password_reset_token, password_reset_expires, email_verified, email_verification_token;
```

---

## Notes

- All migrations use `IF NOT EXISTS` and `IF EXISTS` clauses to be idempotent
- Migrations can be run multiple times safely
- Indexes are created for performance
- Foreign key constraints ensure data integrity
- All new columns have appropriate defaults or are nullable

---

## Troubleshooting

### Error: "column already exists"
- This is normal if migration was already run
- The `IF NOT EXISTS` clause should prevent this, but if it occurs, the migration is safe to skip

### Error: "relation already exists"
- Table already created
- Safe to skip that migration

### Error: "permission denied"
- Ensure you're using the correct database user (postgres)
- Check Docker container permissions

### Backend won't start after migration
- Check backend logs for specific errors
- Verify all migrations completed successfully
- Ensure database connection is working

---

## Quick Migration Script

Save this as `migrate_all.sh`:

```bash
#!/bin/bash

DB_NAME="troubleshooting_ai_dev"  # Change to troubleshooting_ai for production
COMPOSE_FILE="docker-compose.dev.yml"  # Change to docker-compose.production.yml for production
PROJECT_NAME="bot-dev"  # Remove for production

echo "Starting database migrations..."

# Phase 1
echo "Phase 1: User Security..."
cat backend/sql/add_password_reset_fields.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/add_password_history.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/add_account_lockout_fields.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME

# Phase 2
echo "Phase 2: Change Management..."
cat backend/sql/create_change_tickets_table.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/add_ticket_suppression_fields.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME

# Phase 3
echo "Phase 3: Self-Healing..."
cat backend/sql/add_parent_session_id_to_execution_sessions.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME

# Phase 4
echo "Phase 4: User Enhancements..."
cat backend/sql/add_user_profile_fields.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/add_user_preferences.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/create_user_login_history.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/create_user_activity_log.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME
cat backend/sql/create_user_sessions.sql | docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T postgres psql -U postgres -d $DB_NAME

echo "All migrations completed!"
```

Make it executable and run:
```bash
chmod +x migrate_all.sh
./migrate_all.sh
```

