## Worker Orchestration Rollout Checklist

### Feature Flag
- Backend flag: `WORKER_ORCHESTRATION_ENABLED`
  - default: `true`
  - set to `false` to fall back to in-process execution (sessions bypass Redis + workers)
- Frontend flag: `NEXT_PUBLIC_AGENT_WORKSPACE_ENABLED`
  - toggles the live Agent Workspace UI

### Pre-flight
- Ensure Redis is deployed and reachable (`REDIS_URL`)
- Deploy backend, worker, and frontend containers (`docker-compose` includes optional `worker` service)
- Expose Prometheus `/metrics` endpoint (`/metrics`) for scraping

### Enablement Steps
1. Deploy schema updates (`backend/sql/execution_tracking.sql`)
2. Deploy backend with feature flag disabled
3. Deploy worker service(s) with environment:
   - `WORKER_ID`
   - `BACKEND_BASE_URL`
   - `REDIS_URL`
4. Toggle `WORKER_ORCHESTRATION_ENABLED=true`
5. Monitor Prometheus metrics:
   - `worker_assignments_total`
   - `session_state_transitions_total`
   - `execution_step_duration_seconds`

### Game Day (Worker Failover)
1. Start execution session (`POST /api/v1/executions/demo/sessions`)
2. Kill active worker container
3. Watch metrics (`worker_assignments_total{status="pending"}`) and logs
4. Verify orchestrator re-queues assignment or fails gracefully
5. Restart worker; ensure assignment ack + completion events arrive

### Rollback
- Set `WORKER_ORCHESTRATION_ENABLED=false`
- Drain Redis streams (`session.assign`, `session.events`)
- Stop worker containers
- Sessions revert to legacy synchronous execution engine


### Cloud Connector Roadmap

#### Azure Bastion (SSH / PowerShell)
- **Metadata contract**
  - `connector_type: "azure_bastion"`
  - `connection.resource_id` (full Azure resource ID for the target VM)
  - `connection.bastion_host` or `connection.bastion_resource_id`
  - `connection.username` or `credentials.alias`
  - Optional `connection.port` (defaults to 22 for SSH, 5985/5986 for WinRM)
  - `environment`, `subscription_id`, `tenant_id` for policy tagging
- **Worker design**
  - Resolve credentials via Azure AD (service principal or managed identity)
  - Establish Bastion tunnel with `AzureBastion` SDK or `az network bastion tunnel`
  - Proxy command execution through existing SSH/WinRM connectors once tunnel established
  - Emit `agent.connection_established` / `agent.connection_failed` with Bastion metadata
- **Security**
  - Store Azure credentials in Vault and expose via credential aliases
  - Enforce MFA / just-in-time access by requesting tokens per session
  - Support policy overrides for production subscriptions (map to `prod-critical` sandbox profile)

#### GCP IAP (Secure TCP Tunnel)
- **Metadata contract**
  - `connector_type: "gcp_iap"`
  - `connection.project_id`, `connection.zone`, `connection.instance_name`
  - Optional `connection.port` (default 22) and `connection.username`
  - `environment`, `service`, and `risk` fields for policy engine
- **Worker design**
  - Use `google-auth` or `gcloud compute ssh --tunnel-through-iap` to create ephemeral tunnel
  - Reuse SSH connector once tunnel established (same execution + telemetry path)
  - Cache short-lived OAuth tokens per session; flush on completion/failure
- **Security**
  - Credentials delivered via alias mapped to Google service accounts
  - Enforce organization policy (allowed projects/zones) before queueing assignment
  - Emit structured telemetry (`connection.cloud: gcp`, `connection.project_id`) for audit

#### Rollout Considerations
- Extend `infrastructure_connectors.get_connector` to resolve `azure_bastion` and `gcp_iap`
- Update `ExecutionOrchestrator` metadata sanitization to redact cloud tokens
- Add pre-flight docs covering cloud SDK requirements on worker images
- Feature flag per connector (`ENABLE_AZURE_BASTION`, `ENABLE_GCP_IAP`) for staged rollout
- Document example metadata payloads and runbook templates in `CONNECTOR_STATUS.md`


