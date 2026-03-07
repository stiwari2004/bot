# Provisioning System — Implementation Plan

**Status:** Parked for later. Use this plan when resuming provisioning work.

---

## 1. Current State

### Backend (implemented)
- **API** (`backend/app/api/v1/endpoints/provisioning.py`):
  - `POST /provision` — create project and provision (Azure, GCP, AWS, Terraform, CloudFormation)
  - `GET /projects` — list projects (tenant-scoped)
  - `GET /projects/{id}` — get project + resources
  - `DELETE /projects/{id}` — destroy/delete project
  - `GET /templates`, `POST /templates` — template CRUD
  - `POST /validate` — validate variables
- **Providers:** Azure (VM + resource group), GCP (VM), AWS (EC2), Terraform, CloudFormation.
- **Credentials:** Inline in request or `credential_id` to use stored credentials.

### Frontend (implemented)
- **Provisioning** tab under System (tenant admin only).
- **ProvisioningDashboard** lists projects via `GET /projects` and has a **Provision Azure VM** modal:
  - Project name, description
  - Azure credentials (subscription_id, tenant_id, client_id, client_secret)
  - VM: location, optional resource group, VM name, VM size (hardcoded dropdown), OS (Linux/Windows), SSH key or admin password.

### Gaps to address later
- **VM sizes:** Currently a small hardcoded list. Need either a **catalogue** (static/DB) or **dynamic list from cloud API** (e.g. Azure `virtual_machine_sizes.list(location)`).
- **AWS / GCP / Terraform / CloudFormation:** No UI flows yet; only Azure VM form exists.
- **On-prem / network:** Not yet in scope; to be defined when expanding beyond cloud VMs.

---

## 2. Implementation Phases (when resuming)

### Phase A — VM size source of truth
- **Option 1 — Catalogue:** Maintain a list of VM sizes (e.g. JSON or DB), optionally per provider/region. Expose via API (e.g. `GET /provisioning/catalog/vm-sizes?provider=azure&location=eastus`) and use in UI dropdown.
- **Option 2 — Cloud API:** Backend endpoint that calls provider APIs (e.g. Azure `ComputeManagementClient.virtual_machine_sizes.list(location)`) using credentials; frontend calls it when location (and optionally credentials) are set.
- **Option 3 — Hybrid:** Curated “recommended” sizes in catalogue + “Load from cloud” to refresh from provider API.
- **Deliverable:** Provisioning UI uses a single, clear source for VM sizes (no ad‑hoc hardcoded list).

### Phase B — Azure polish
- Integrate VM size source from Phase A into Azure VM form.
- Optional: stored credentials / credential picker (use existing credential store) instead of only inline.
- Optional: project detail view (resources, state, outputs) from `GET /projects/{id}`.
- Optional: destroy from UI using `DELETE /projects/{id}`.

### Phase C — Other providers (AWS, GCP)
- AWS: UI form for EC2 (region, instance type, AMI, key, SG, subnet, etc.) using existing backend.
- GCP: UI form for VM (project, zone, machine type, etc.) using existing backend.
- Reuse same VM/instance size strategy (catalogue or API) per provider where applicable.

### Phase D — Terraform / CloudFormation
- UI to create projects from templates (template picker or upload), variable form, then provision.
- Optional: plan‑then‑apply flow for Terraform.

### Phase E — On‑prem and network (future)
- Define scope (e.g. bare metal, hypervisor, network devices) and add providers/connectors as needed; then add UI flows.

---

## 3. Testing (thorough validation)

Use this section to close weird errors and ensure everything works per expectations.

### 3.1 Execution WebSocket — fixed
- **Issue:** On starting an execution, the WebSocket `/api/v1/executions/ws/sessions/{id}` could raise:
  `UnboundLocalError: cannot access local variable 'SessionLocal' where it is not associated with a value`
- **Cause:** In `stream_execution_events`, `SessionLocal` was imported inside `if token:` and also used later outside that block. Python treated `SessionLocal` as a local name for the whole function, so when `token` was falsy, the later `db = SessionLocal()` ran before any assignment.
- **Fix applied:** Removed the redundant local `from app.core.database import SessionLocal` inside the `if token:` block in `backend/app/api/v1/endpoints/executions.py`. The handler now uses the module-level `SessionLocal` everywhere.
- **How to verify:** Start an execution from the UI and open the execution view (WebSocket). Connection should accept and stream events without the above error.

### 3.2 Execution flow — checklist
- [ ] Start execution from Executions / Ticket / Runbook path; session is created and appears in list.
- [ ] WebSocket connects (no UnboundLocalError); events stream (steps, logs, completion).
- [ ] Cancel works (session moves to cancelled/abandoned, no stuck state).
- [ ] Completed runs show correct status and duration; can view history.

### 3.3 Provisioning — checklist
- [ ] System → Provisioning visible for tenant admin; list loads (`GET /projects`).
- [ ] “Provision Infrastructure” opens Azure VM modal; submit with valid Azure credentials and variables.
- [ ] After success, new project appears in list; state moves to active (or failed with clear error).
- [ ] Invalid credentials or missing required fields return clear error in modal.

### 3.4 Auth and API
- [ ] Login / logout; token refresh or expiry handled.
- [ ] API calls use `authFetch` / Bearer token; 401 leads to re-auth or clear error.
- [ ] Tenant isolation: users only see their tenant’s data (e.g. projects, executions).

### 3.5 Other areas (as needed)
- [ ] Alerts: list, filters, detail, polling.
- [ ] Changes: list, polling.
- [ ] Runbooks: list, generate, approve.
- [ ] Settings: connectors, credentials (no regression).

---

## 4. Where to look when errors appear

| Symptom | Likely area |
|--------|--------------|
| WebSocket crash on execution start | `backend/app/api/v1/endpoints/executions.py` — `stream_execution_events` |
| Provisioning API 401/403 | Auth middleware, tenant_id, `get_current_user` |
| Provisioning “failed” with Azure error | Backend Azure provider; check logs for Azure SDK/API message |
| Frontend “Failed to fetch projects” | API base URL, CORS, auth header, `/api/v1/provisioning/projects` |

---

## 5. Doc ownership

- **Implementation plan (this doc):** Phases A–E and VM size strategy — to be completed when resuming provisioning.
- **Testing:** Section 3 is the master checklist for thorough testing; update it as you fix issues or add flows.
