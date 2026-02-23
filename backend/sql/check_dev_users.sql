-- Check dev database: super-admins and regular users
-- Run from host:
--   docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -f - < backend/sql/check_dev_users.sql
-- Or from repo root:
--   docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev < backend/sql/check_dev_users.sql

\echo '=== Super admins (super_admins) ==='
SELECT id, email, full_name, is_active, last_login, created_at FROM super_admins ORDER BY id;

\echo ''
\echo '=== Tenants ==='
SELECT id, name, subdomain_slug, is_active, created_at FROM tenants ORDER BY id;

\echo ''
\echo '=== Regular users (users) ==='
SELECT id, tenant_id, email, full_name, role, is_active, last_login, created_at FROM users ORDER BY id;

\echo ''
\echo '=== Row counts (main tables) ==='
SELECT 'tenants' AS tbl, count(*) FROM tenants
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'super_admins', count(*) FROM super_admins
UNION ALL SELECT 'runbooks', count(*) FROM runbooks
UNION ALL SELECT 'tickets', count(*) FROM tickets
UNION ALL SELECT 'execution_sessions', count(*) FROM execution_sessions;
