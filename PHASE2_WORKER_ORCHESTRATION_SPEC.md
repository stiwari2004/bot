# Phase 2 Worker Orchestration Requirements & Specification

## 1. Purpose & Goals
- Transform the POC execution flow into a distributed, enterprise-grade worker model.
- Ensure one active execution workspace per ticket with live operator visibility.
- Support human-in-the-loop checkpoints while enabling automation where risk allows.
- Align with `PHASE2_AGENT_ARCHITECTURE.md` section 3.4 (Human-in-the-Loop Execution Engine).

### 1.1 Objectives
- Provide deterministic lifecycle management for execution sessions, including queueing, worker assignment, retries, and completion.
- Deliver consistent data contracts across REST APIs, WebSocket events, and internal queues.
- Introduce mandatory sandbox profiles and guardrails per environment, ensuring least privilege.
- Make credential access transient, auditable, and Vault-backed.
- Expose observability signals (metrics, logs, traces) required for SRE operations.

### 1.2 Out of Scope (Phase 2 deferments)
- Ticket status update automation (tracked separately in `PHASE2_POC_STATUS_AND_NEXT_STEPS.md`).
- Credential management UI (future work once backend APIs stabilize).
- Production-grade SLA (e.g., multi-region HA); current scope targets single-region active/passive.

## 2. Lifecycle Model

### 2.1 Entities
- **ExecutionSession**: Represents a run against a specific ticket + runbook. States: `queued`, `assigning_worker`, `waiting_for_approval`, `executing`, `paused`, `rollback`, `completed`, `failed`, `cancelled`.
- **ExecutionStep**: Child of a session with sub-states: `pending`, `awaiting_approval`, `approved`, `running`, `succeeded`, `failed`, `rolled_back`.
- **AgentWorker**: Registered worker node. States: `idle`, `assigned`, `executing`, `errored`, `offline`, `draining`.
- **ApprovalTask**: Logical unit prompting human action. States: `pending`, `notified`, `approved`, `rejected`, `expired`.

### 2.2 Session Flow
1. **Create Session**: Ticket selection spawns session with derived runbook, environment profile, validation mode.
2. **Queue**: Session enters orchestrator queue (`pending_sessions` table + Redis/AMQP queue).
3. **Assign Worker**:
   - Orchestrator evaluates worker registry (capabilities, environment, load, health).
   - Publishes `session.assigned` event (REST + WebSocket + audit log) when match found.
4. **Pre-flight Checks**:
   - Worker performs sandbox setup, Vault credential fetch, dry-run validation (allow/deny lists).
   - If failure, session transitions to `failed` with `assignment_error` reason and optionally retries alternative worker.
5. **Approval Gates**:
   - If session `validation_mode` requires, orchestrator emits `approval.requested` event, transitions to `waiting_for_approval`.
   - Operator approves/rejects via REST. Auto-approval triggers when confidence thresholds (from runbook metadata) met.
6. **Execution**:
   - Worker streams `step.started` and `step.output` events via WebSocket channel → orchestrator publishes to UI and persists to Postgres (`execution_events` table).
   - On step success, orchestrator advances pointer (`current_step`). On failure, triggers rollback flow or awaits operator decision per policy.
7. **Rollback Handling**:
   - For steps flagged `requires_rollback`, orchestrator enqueues rollback actions immediately on failure or manual trigger.
8. **Completion**:
   - Orchestrator finalizes session (`completed`/`failed`), persists metrics, and publishes `session.completed` event.
   - Post-hooks (ticket update, resolution verification) run later per roadmap.

### 2.3 Worker Lifecycle
- **Registration**: Worker calls `POST /api/v1/agent/register` with capabilities, network segment, environment scopes. Certificates validated via mTLS.
- **Heartbeat**: Worker emits heartbeat every 15s; orchestrator marks worker `offline` after 45s without heartbeat.
- **Assignment**: Orchestrator sends assignment payload via queue (`session.assign` message). Worker ACK required within 5s; otherwise message re-queued.
- **Execution Loop**: Worker processes command queue, streams outputs, handles approvals.
- **Shutdown/Drain**: Worker sets state `draining`, finishes active sessions, unregisters.

## 3. Data Contracts

### 3.1 REST APIs (FastAPI)
- `POST /api/v1/executions` {ticket_id, runbook_id?, validation_mode, environment_profile} → returns session_id.
- `POST /api/v1/executions/{session_id}/approve` {step_number, approved, notes, approver_role}.
- `POST /api/v1/executions/{session_id}/rollback` {step_number?, reason}.
- `GET /api/v1/executions/{session_id}` → session detail including current step, approvals, outputs snapshot.
- `GET /api/v1/executions/{session_id}/events?since=<cursor>` → fallback polling when WS unavailable.
- Worker endpoints (internal, mTLS):
  - `POST /api/v1/agent/register`
  - `POST /api/v1/agent/heartbeat`
  - `POST /api/v1/agent/{worker_id}/complete-step` (final ack with result payload)

### 3.2 WebSocket Events
Route: `WS /ws/executions/{session_id}` (authenticated via JWT + tenant context).
Event envelope:
```json
{
  "event": "execution.step.output",  // string
  "session_id": 123,
  "step_number": 4,
  "timestamp": "2025-11-08T13:05:43.120Z",
  "payload": {
    "stream_seq": 17,
    "chunk_type": "stdout",  // stdout|stderr|status
    "data": "Service restarted successfully"
  },
  "meta": {
    "worker_id": "worker-prod-a-01",
    "environment": "prod",
    "sandbox_profile": "prod-critical"
  }
}
```
Event types:
- `session.created`
- `session.assigned`
- `approval.requested`
- `approval.resolved`
- `execution.step.started`
- `execution.step.output`
- `execution.step.completed`
- `execution.step.failed`
- `execution.rollback.started`
- `execution.rollback.completed`
- `session.completed`
- `session.failed`

Reconnect contract: clients supply `last_event_id` header; orchestrator replays from `execution_events` queue/table.

### 3.3 Queue Messages (Redis Streams / RabbitMQ)
- `session.assign`
```json
{
  "session_id": 123,
  "ticket_id": "INC-9081",
  "environment_profile": "prod-critical",
  "worker_requirements": {
    "capabilities": ["ssh", "database"],
    "network_segment": "vpc-a",
    "max_latency_ms": 2000
  },
  "runbook_steps": [...],
  "credentials": ["cred-prod-db-primary"],
  "sandbox_profile": "prod-strict"
}
```
- `session.command`
```json
{
  "session_id": 123,
  "step_number": 4,
  "command": "systemctl restart primary-db",
  "args": {"timeout": 60},
  "approval_token": "appr-456",  // included when human approval required
  "rollback": {
    "command": "systemctl restart replica-db",
    "conditions": ["failure"]
  }
}
```
- `session.result`
```json
{
  "session_id": 123,
  "step_number": 4,
  "status": "succeeded",
  "stdout": "...",
  "stderr": "",
  "exit_code": 0,
  "execution_ms": 3200,
  "sandbox_profile": "prod-strict",
  "credential_ids": ["cred-prod-db-primary"],
  "blast_radius": "medium"
}
```

### 3.4 Database Extensions
- `execution_sessions`: add columns `transport_channel`, `last_event_seq`, `assignment_retry_count`, `sandbox_profile`.
- `execution_steps`: add `sandbox_profile`, `blast_radius`, `approval_policy`, `command_payload` (JSON), `rollback_payload` (JSON).
- New table `execution_events` (append-only) for replay: columns (`event_id`, `session_id`, `step_number`, `event_type`, `payload`, `created_at`).
- New table `agent_worker_assignments`: track worker-session mappings, assignment status, ack timestamps, failure reasons.

## 4. Approval & Policy Engine

### 4.1 Validation Modes
- `per_step`: Every step gated. Default for `blast_radius=high` or `environment=prod`.
- `per_phase`: Prechecks/Main/Postchecks aggregated approvals.
- `critical_only`: Steps flagged `critical=true` require approval; others auto-approve if confidence ≥ threshold.
- `final_only`: Single approval pre-resolution; allowed only for `blast_radius=low` runbooks.

### 4.2 Auto-Approval Rules
- Step metadata includes `confidence_score` and `auto_approve_threshold`.
- Auto-approve permitted if `confidence_score >= threshold` **and** `blast_radius <= medium` **and** `environment in {dev, staging}`.
- Mandatory two-key rule for `blast_radius=high` or destructive commands (per OPA policies in architecture doc).

### 4.3 Approval SLA & Escalation
- Default SLA: 10 minutes for prod, 30 minutes for non-prod.
- If SLA breached → escalate via Slack/PagerDuty, session remains `waiting_for_approval` but event flagged `approval.expired`.
- Rejection triggers `session.paused` pending operator directive (`retry`, `rollback`, `cancel`).

## 5. Sandbox & Security Profiles

### 5.1 Environment Profiles
| Profile | Environment | Sandbox Controls | Command Scope | Rollback Requirement |
|---------|-------------|------------------|----------------|----------------------|
| `prod-critical` | prod | seccomp(AppArmor), read-only root FS, no internet egress | allow-list only | mandatory |
| `prod-standard` | prod | seccomp(default), limited capabilities | allow-list + deny-list | mandatory |
| `staging-standard` | staging | seccomp(default), ephemeral FS | allow-list + audit | optional |
| `dev-flex` | dev | basic isolation | deny-list only | optional |

### 5.2 Policy-as-Code Integration
- Use OPA policies from `PHASE2_AGENT_ARCHITECTURE.md` 5.9.x sections.
- Orchestrator evaluates policies before dispatch (e.g., verifying worker environment vs credential scope, command allow/deny).
- Worker enforces policy locally (fail-fast if command violates policy).

### 5.3 Credential Handling
- Workers authenticate to Vault via AppRole or cloud IAM (per environment).
- Credentials fetched with TTL ≤ 5 minutes, stored in memory (mlock), wiped after step completion.
- Orchestrator logs credential usage metadata (IDs only) to `execution_steps.credentials_used` for audit.
- Secrets redacted from command outputs using `OutputSanitizer` patterns.

## 6. Observability & Telemetry

### 6.1 Metrics (Prometheus)
- `worker_assignments_total{worker_id,status}`
- `session_state_transitions_total{from,to}`
- `execution_step_duration_seconds{environment,connector}` histogram
- `approval_wait_duration_seconds{environment}` histogram
- `sandbox_policy_violations_total{policy_id}`
- `credential_fetch_duration_seconds{vault_cluster}` histogram
- `websocket_active_sessions` gauge

### 6.2 Logging
- Structured JSON with fields: `tenant_id`, `session_id`, `worker_id`, `step_number`, `sandbox_profile`, `event_type`, `command_hash`, `approval_id`, `blast_radius`.
- Log levels aligned with `PHASE2_AGENT_ARCHITECTURE.md` (INFO for transitions, DEBUG for streaming chunks, WARN for retries, ERROR for failures).

### 6.3 Tracing (OpenTelemetry)
- Trace spans for: `session.create`, `worker.assign`, `step.execute`, `vault.fetch`, `approval.wait`, `rollback.execute`.
- Propagate trace context via queue messages and WebSocket metadata for end-to-end visibility.

## 7. Reliability & Retry Semantics

### 7.1 Assignment Retries
- Max 3 attempts per session (configurable). Exponential backoff (5s, 15s, 45s) before marking `failed_assignment`.
- Skip workers flagged `errored` or `offline` within last 60s.

### 7.2 Command Retries
- Step-level retry policy from runbook metadata. Default 0 retries for destructive commands, 1 retry for idempotent checks.
- Retries require operator approval if `blast_radius >= medium`.

### 7.3 Worker Failover
- On worker crash mid-step: orchestrator marks step `failed`, triggers rollback (if defined), and attempts reassignment after human confirmation.
- Heartbeat-based detection ensures failover within 30s.

### 7.4 Idempotency
- `idempotency_key` propagated through session lifecycle (from ticket ingestion). All APIs and queue messages include key to avoid duplicate executions.
- Worker must include `idempotency_key` in result payload; orchestrator discards duplicates.

## 8. Rollout Considerations

### 8.1 Feature Flags
- `worker_orchestration.enabled` (backend + frontend) → toggles new queue/worker execution path.
- `ui.task_workspace.enabled` → enables dual-pane UI; default off until feature complete.

### 8.2 Migration Steps
1. Migrate DB schema (add new columns/tables) via Alembic.
2. Deploy orchestrator queue integration (Redis/RabbitMQ) with feature flag off.
3. Stand up pilot worker pool (staging environment) to validate flow.
4. Enable WebSocket transport for beta tenants.
5. Enable feature flag in production after SRE sign-off and Game Day run (worker failover scenario).

### 8.3 Backout Plan
- Disable feature flag to revert to in-process execution engine (current behavior).
- Drain queues, mark in-flight sessions as `cancelled` or `failed` with `backout` reason.
- Workers go to `draining` state and unregister.

## 9. Deliverables
- Updated backend modules:
  - `backend/app/services/execution_orchestrator.py`
  - `backend/app/services/agent_worker_manager.py`
  - `backend/app/api/v1/endpoints/executions.py` (WebSocket + REST additions)
  - `backend/app/api/v1/endpoints/agent_workers.py`
- New worker service repository/module (`backend/worker/` or separate repo) with deployment manifests.
- Frontend updates:
  - WebSocket subscription hooks
  - Task workspace UI (`frontend-nextjs/src/app/page.tsx`, new components under `src/components/agent/`)
- Telemetry dashboards (Prometheus + Grafana) and alert rules for SRE runbooks.
- Documentation updates to `PHASE2_AGENT_ARCHITECTURE.md` (cross-reference) and runbook enablement guides.

## 10. Acceptance Criteria
- Session can progress end-to-end through distributed worker path in staging with controlled runbook.
- Operator can approve/reject steps via UI; approval state reflected within ≤2s via WebSocket.
- Rollback executes automatically on step failure for runbooks with rollback definitions.
- Sandbox policies enforce environment-specific restrictions (verified via automated tests).
- Credential access audited end-to-end with Vault logs correlated to `execution_steps.credentials_used`.
- Observability dashboards show worker assignment, session states, approval latency, and command execution SLOs.
- Feature flag toggling reverts to legacy execution without data corruption.

