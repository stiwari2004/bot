-- Check infrastructure connections and their linked credentials (DB-level verification)
-- Run against your app DB (e.g. troubleshooting_ai_dev or troubleshooting_ai).
--
-- Dev (Docker):
--   docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -f - < backend/sql/check_credentials_and_connections.sql
-- Or paste the queries below into psql.

-- 1) Infrastructure connections (nodes): show credential_id and target_host
SELECT
  id AS connection_id,
  tenant_id,
  name AS node_name,
  connection_type,
  target_host,
  target_port,
  credential_id,
  is_active
FROM infrastructure_connections
ORDER BY id;

-- 2) Join nodes to credentials: see if username (and secret) exist for each node
SELECT
  ic.id AS connection_id,
  ic.name AS node_name,
  ic.target_host,
  ic.credential_id,
  c.id AS cred_id,
  c.name AS credential_name,
  c.credential_type,
  c.username,
  CASE WHEN c.encrypted_password IS NOT NULL AND c.encrypted_password != '' THEN 'yes' ELSE 'no' END AS has_password,
  CASE WHEN c.encrypted_api_key IS NOT NULL AND c.encrypted_api_key != '' THEN 'yes' ELSE 'no' END AS has_api_key
FROM infrastructure_connections ic
LEFT JOIN credentials c ON c.id = ic.credential_id AND c.tenant_id = ic.tenant_id
ORDER BY ic.id;

-- 3) Credential id = 1: can we "load" username from DB? (no decryption here, just that the row exists and username is set)
SELECT
  id,
  tenant_id,
  name,
  credential_type,
  username,
  LENGTH(encrypted_password) AS encrypted_password_length,
  LENGTH(encrypted_api_key) AS encrypted_api_key_length,
  is_active
FROM credentials
WHERE id = 1;

-- 4) Tenant match: app only decrypts credential when credential.tenant_id = session.tenant_id. If these differ, username won't be added to config.
SELECT
  c.id AS cred_id,
  c.tenant_id AS cred_tenant_id,
  ic.tenant_id AS connection_tenant_id,
  CASE WHEN c.tenant_id = ic.tenant_id THEN 'match' ELSE 'MISMATCH' END AS tenant_match,
  c.username
FROM credentials c
JOIN infrastructure_connections ic ON ic.credential_id = c.id
WHERE c.id = 1;
