# Disaster Recovery Game Day Plan

Quarterly game-days validate that the troubleshooting platform can be recovered within the organisation’s RTO/RPO. Use this runbook to execute and document each exercise.

## 1. Scope

- Backend API (`backend` container + Postgres)
- Worker service (Redis backed)
- Frontend (Next.js)
- Immutable audit log (`logs/audit.log` and S3 archive)

## 2. Pre-checks

1. Confirm the latest production backup exists (Postgres snapshot + S3 audit log copy).
2. Verify `AUDIT_LOG_PATH` writable on standby cluster.
3. Ensure Vault credentials (AppRole secret ID) valid.

## 3. Game Day Steps

1. **Simulate Outage**
   - Disable primary Postgres instance or drop active database.
   - Stop backend+worker containers.
2. **Recovery Execution**
   - Restore Postgres from latest snapshot into staging DR namespace.
   - Replay Redis command backlog if available; otherwise redeploy worker.
   - Bootstrap application containers using infrastructure-as-code (Terraform/Helm).
   - Rehydrate audit log: sync `logs/audit.log` from S3 and verify hash chain.
3. **Validation**
   - Create test execution session; ensure metrics and audit entries populate.
   - Run smoke test: invoke `/api/v1/executions/demo/sessions` and confirm worker command.
   - Verify audit log hash chain using `scripts/run_dr_checklist.sh --verify-audit`.
   - Confirm immutable S3 archive has same-day records with `scripts/run_dr_checklist.sh --verify-s3`.
4. **Rollback / Cutover**
   - If satisfied, decommission DR environment; otherwise cut traffic via load balancer.

## 4. Post-Game Documentation

- Capture RTO / RPO achieved.
- Record gaps and remediation tasks in Jira.
- Upload logs and screenshots to Confluence DR page.

## 5. Automation Hooks

- `scripts/run_dr_checklist.sh` – orchestrates verification (audit hash check, API smoke).
- Schedule `scripts/run_dr_checklist.sh --verify-s3 --verify-audit --api-smoke` weekly via CI to catch regressions between formal exercises.
- GitHub Action `dr-game-day.yml` (future) – scheduled dry run on staging nightly.

## 6. Success Criteria

- Recovery < 30 minutes.
- No audit log gaps (hash chain intact).
- Vault credential rotation validated.
- Telemetry (Prometheus, logs) available within 5 minutes.


