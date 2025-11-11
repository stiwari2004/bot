# Secrets Bootstrapping Playbook

This guide explains how operators deliver initial credentials (“secret zero”) to the troubleshooting agent without exposing sensitive material in logs or source control.

## 1. Control Objectives

1. **No static secrets in repository** – all secrets originate from Vault/KMS.
2. **Traceable issuance** – every credential fetch is auditable and mapped to a human/automation identity.
3. **Short-lived credentials** – secrets are rotated or revoked automatically after handoff.

## 2. Vault Onboarding Flow

1. **Initialize Vault AppRole**
   - Security/SRE provisions an AppRole named `troubleshooting-agent`.
   - Role is scoped to paths:
     ```
     secret/data/troubleshooting-agent/*
     secret/metadata/troubleshooting-agent/*
     ```
   - Configure token TTL (default 30m) and token max TTL (8h).

2. **Deliver Secret Zero**
   - During deployment, the platform team injects `VAULT_ROLE_ID` (`configmap` or `ansible vault`) and passes the `VAULT_SECRET_ID` via a one-time sealed envelope (Vault CLI `vault write -f auth/approle/role/.../secret-id`).
   - `VAULT_SECRET_ID` is loaded into the runtime via Kubernetes Secret / Docker secret and rotated post-deployment.

3. **Exchange for Wrapped Token**
   - Application exchanges `ROLE_ID` + `SECRET_ID` for a wrapped token using TLS-authenticated call:
     ```bash
     vault write -wrap-ttl=5m auth/approle/login role_id=$ROLE secret_id=$SECRET
     ```
   - Wrapper token is unwrapped in memory to obtain client token – never persisted to disk.

4. **Fetch Runtime Credentials**
   - `CredentialService` reads from `secret/data/troubleshooting-agent/<tenant>/<alias>` returning JSON payload (username/password, private keys, region hints, etc.).
   - Responses are decrypted and merged into session metadata without logging sensitive fields (see `_sanitize_metadata` in `execution_orchestrator.py`).

5. **Rotation & Revocation**
   - Security rotates AppRole secret IDs weekly (or on demand) and notifies pipeline to refresh.
   - Application detects rotation failure via 401 responses and triggers alert `secrets_bootstrap_token_expired`.

## 3. Local Development Mode

For contributors running the stack locally:

- Set `CREDENTIAL_ENCRYPTION_KEY` and mock Vault via `docker compose -f docker-compose.dev.yml`.
- Developers generate short-lived secrets with `vault kv put secret/troubleshooting-agent/dev/example ...`.
- Never commit generated keys; `.env.example` documents required environment variables.

## 4. Runtime Configuration

The worker and backend components expect the following Vault variables:

- `VAULT_ADDR` – HTTPS endpoint for the Vault cluster.
- `VAULT_ROLE_ID` – AppRole identifier injected via ConfigMap/Secret.
- `VAULT_SECRET_ID_FILE` – Path to the one-time secret ID (mounted as tmpfs, rotated after bootstrap).
- `VAULT_NAMESPACE` *(optional)* – Multi-tenant Vault namespace when applicable.

On startup the `CredentialService` unwraps a short-lived token, caches it in memory, and refreshes automatically before expiry. Tokens are never written to disk or echoed to logs.

## 4. Logging & Telemetry Guard Rails

- `CredentialEncryption` refuses to start without `CREDENTIAL_ENCRYPTION_KEY`; no fallback keys are logged.
- `execution_orchestrator._sanitize_metadata` recursively redacts any fields matching `password`, `secret`, `token`, etc., before events reach clients/metrics.
- Access is logged by `CredentialService.log_credential_usage` (stored in Postgres + forwarded to SIEM).
- The global logging pipeline applies a `RedactingFilter` (see `app/core/logging.py`) that masks secret-like values before they leave the process.

## 5. Action Items

1. Configure Vault AppRole and CI pipeline integration following steps above.
2. Populate `infra/policies/` manifests enforcing secrets injection via Kubernetes Secrets.
3. Enable alerting on `secrets_bootstrap_token_expired` and audit logs for credential alias resolution.


