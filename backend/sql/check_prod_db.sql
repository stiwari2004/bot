-- Check PRODUCTION database: super_admin IDs, tenant IDs, users (read-only).
-- Use this to verify what exists before changing anything.
--
-- Run against production Postgres (docker-compose.production.yml):
--   From repo root:
--     docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -f - < backend/sql/check_prod_db.sql
--   Or copy this file into the container and run:
--     docker cp backend/sql/check_prod_db.sql bot-prod-postgres:/tmp/
--     docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -f /tmp/check_prod_db.sql
--
-- Production DB name: troubleshooting_ai (same as standalone; they use different hosts/volumes.)

\echo '=== Super admins (super_admins) - IDs and emails ==='
SELECT id, email, full_name, is_active, last_login, created_at FROM super_admins ORDER BY id;

\echo ''
\echo '=== Tenants - IDs and names ==='
SELECT id, name, subdomain_slug, is_msp, is_active, created_at FROM tenants ORDER BY id;

\echo ''
\echo '=== Regular users (users) - first 50 ==='
SELECT id, tenant_id, email, full_name, role, is_active, last_login, created_at FROM users ORDER BY id LIMIT 50;

\echo ''
\echo '=== Row counts (main tables) ==='
SELECT 'tenants' AS tbl, count(*) FROM tenants
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'super_admins', count(*) FROM super_admins
UNION ALL SELECT 'tenant_subscriptions', count(*) FROM tenant_subscriptions
UNION ALL SELECT 'runbooks', count(*) FROM runbooks
UNION ALL SELECT 'tickets', count(*) FROM tickets
UNION ALL SELECT 'execution_sessions', count(*) FROM execution_sessions;
