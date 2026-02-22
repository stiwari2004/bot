# Troubleshooting: Worker reported failure / Step failed on first command

When you see **"Worker worker-dev reported failure"** (or any worker) on the first command, use the following to find the **actual error** and fix it.

---

## 504 Gateway Timeout (all API calls)

If **POST /api/v1/executions/demo/sessions**, **GET /auth/me**, or other endpoints return **504 Gateway Timeout**:

1. **Backend / gateway** – The server or reverse proxy is not getting a response in time. Check:
   - Is the **backend container** running and healthy? (`docker ps`, backend logs.)
   - Is the **database** reachable from the backend? (Connection pool exhausted or DB down can block all requests.)
   - **Proxy timeout** (e.g. nginx, load balancer) – dev nginx uses 120s for `/api` (`nginx/dev.resolvify.tech.conf`); increase further if session create or other calls still time out.

2. **Where the request stalls** – Backend logs now include:
   - `Session create: credential hydration done, creating assignment record`
   - `Session create: assignment record flushed, publishing session.created event`
   - `Session create: publishing assignment to Redis (session_id=...)`
   - `Session create: assignment published, stream_id=...`
   If you see the first but not the second, the stall is around DB flush or event publish. If you see "publishing assignment to Redis" but not "assignment published", the stall is **Redis** (queue publish). Check Redis connectivity and latency.

3. **Credential hydration** – If 504 started after the credential_source change: credential resolution is wrapped in try/except so **failures** no longer break the request; only a **hang** (e.g. DB/Redis blocking) would still cause 504.

4. **Quick rollback** – To test whether credential resolution is the cause, you can temporarily stop copying `credential_source` in `orchestrator.py` (the two lines that set `request_metadata["credential_source"]` from `connection`). Session create will succeed again but the worker will not receive username/password until the fix is restored and any hang is resolved.

5. **Event loop blocking** – The backend uses sync SQLAlchemy. The full enqueue (session create, resolve connection, credential hydration, assignment, DB flush, Redis publish) used to run on the main async event loop and could block it for tens of seconds, causing **all** requests (including GET /auth/me) to get 504. The **entire** enqueue is now run in a **thread pool** (`_run_enqueue_session_in_thread` + `run_in_executor`), with a dedicated event loop and DB session in the thread and a separate Redis client so the main event loop stays free and other requests can be served.

---

## Step timed out (e.g. "Step 1 failed", "timed out", Duration ~60s)

If a step fails with **"timed out"** and duration around 60s (or 300s), the **command timeout** for that step was exceeded.

- **Default** – The worker uses a default command timeout of **300 seconds** (5 minutes), overridable with env **`WORKER_COMMAND_TIMEOUT`** (seconds). Set it in the worker’s environment (e.g. in Docker or systemd) if steps need longer.
- **Per-step** – In the runbook YAML you can set **`timeout: <seconds>`** on a step (e.g. `timeout: 600`). That value is stored and sent to the worker as `timeout_seconds` for that step.

## Connection failed / SSH connection timed out

If you see **"Connection failed"** with reason **"timed out"** or **"SSH connection timed out to host:port"**, the failure is at **SSH connect** (TCP/SSH handshake), not at command execution. The SSH connector uses a **connect timeout** (default 15s) so it fails fast if the host is unreachable.

### Interpreting worker SSH config lines

Worker logs show one line per assignment:  
`SSH config session_id=... host=... port=... username_set=... has_password=... has_private_key=...`

- **`host=None` or `username_set=False has_password=False`** – The assignment payload did not include a resolved connection or credentials. Common for older sessions created before credential hydration was fixed, or when the runbook/ticket has no infrastructure connection or credential. New sessions should have connection + credentials; if they don’t, check that the runbook’s target node has an infrastructure connection with a credential and that the backend is copying `credential_source` into request metadata before `prepare_metadata`.
- **`host=192.168.x.x port=22 username_set=True has_password=True`** but then **`SSH execution error: timed out`** – Credentials are present; the failure is **network**: the worker process cannot reach the target IP (e.g. the worker container has no route to `192.168.48.10`). Fix by giving the worker a network path to the target (see below).

### Fixing “credentials OK but connect times out”

- **Worker in Docker** – The **container** often cannot reach LAN IPs (e.g. `192.168.48.10`) even though the host can. Two options:
  1. **Run the worker with host network** so it shares the host’s network and can reach the same IPs. Example for dev: add to the worker service in `docker-compose.dev.yml`: `network_mode: host`, and set `BACKEND_BASE_URL=http://127.0.0.1:8001` and expose Redis (e.g. `ports: ["6380:6379"]`) with `REDIS_URL=redis://127.0.0.1:6380`. Then the worker talks to backend/Redis on localhost and can reach LAN hosts.
  2. **Run the worker on the host** (not in Docker), with `BACKEND_BASE_URL` and `REDIS_URL` pointing at your backend and Redis (e.g. over the host IP or tunnel).
- **Firewall / VLAN** – Ensure the machine running the worker can reach the target on port 22 (same VLAN, no firewall blocking, or use a bastion the worker can reach).

### Other checks

- **Connect vs command timeout** – Connect uses a short timeout (15s by default); the step timeout applies to the command run after connect. So "timed out" after ~15–30s usually means connect timed out; after 60–300s it usually means the command timed out.
- **Worker register at startup** – If worker logs show `httpx.ConnectError: All connection attempts failed` when POSTing to `/api/v1/agent/workers/register`, the worker could not reach the backend (e.g. backend not ready yet). The worker now retries registration (see `WORKER_REGISTER_RETRIES`, default 5) with backoff; ensure the backend is up and reachable at `BACKEND_BASE_URL`.

---

## Clear pending / queued execution sessions

If many sessions are stuck in **pending** or **queued**, you can mark them as failed so the queue is clear:

1. Run the SELECT in `backend/sql/clear_pending_execution_sessions.sql` to list affected sessions.
2. Uncomment and run the UPDATE in that file to set `status = 'failed'` and `completed_at = now()` for those sessions.

See the script for optional cleanup of `agent_worker_assignments`.

---

## Audit log: "Permission denied creating audit log directory"

If backend logs show **"Permission denied creating audit log directory uploads/logs"** and **"Failed to create audit log directory at fallback location"**:

- **Cause** – The process (e.g. in Docker as `appuser`) cannot create or write to `uploads/logs` or `/app/uploads/logs`. With dev compose, `./uploads-dev:/app/uploads` mounts a host directory; if it is not writable by the container user (UID 1000), both the default path and `/app/uploads/logs` fail.
- **Automatic fallback** – The audit log service now tries **`/tmp/audit.log`** after the first two paths. So audit logging continues; logs under `/tmp` may not survive container restarts.
- **Permanent fix** – On the host, create the directory and make it writable by the container user, e.g. `mkdir -p uploads-dev/logs && chmod 777 uploads-dev/logs` (or `chown 1000:1000 uploads-dev` so UID 1000 can write). Restart the backend so it uses the writable path.

---

## 1. See the error in the UI (event feed)

- Open the **execution session** (runbook execution) in the app.
- In the **event transcript** / activity feed, find the entry for **"Step 1 failed"** or **"Connection failed"**.
- The **summary** and **detail** now show the real error from the connector, for example:
  - `SSH connector requires host and username.`
  - `Authentication failed.`
  - `[Errno 111] Connection refused`
  - `Node 'my-server' is not configured in Infrastructure Connections.`

If you still see only a generic "Worker X reported failure", expand the event or check the step details (below).

---

## 2. See the error in the UI (step details)

- In the same execution session, open the **Steps** section.
- Click the **failed step** (e.g. Step 1).
- The step’s **Error** field shows the same message the connector returned (stored in `step.error`).

---

## 3. Get the error via API

```bash
# Replace {session_id} with your execution session ID
GET /api/v1/executions/sessions/{session_id}
```

Response includes a `steps` array. For the failed step, use:

- `steps[].error` – error message from the connector or execution layer.
- `steps[].output` – command stdout/stderr (if any).

---

## 4. Backend / worker logs

- **Backend** (step execution): logs when the step fails and what error was returned (e.g. from `step_execution_service`).
- **Worker** (e.g. `worker-dev`): logs the result of `connector.execute_command()` and publishes `execution.step.completed` with `success: false` and `detail: <error>`.

Search logs for the **session ID** or **step number** and the **error string** (e.g. "SSH connector requires", "Authentication failed", "Connection refused").

---

## Common causes (especially “first command” / SSH)

| Error / symptom | What to check |
|-----------------|----------------|
| **SSH connector requires host and username** | Connection config is missing `host` or `username`. You may now see a more specific error instead (see below). Otherwise: ensure the **Infrastructure Connection** has `target_host` set and is linked to a **Credential** that has **username** (and password or key). |
| **SSH node 'X' has no credential linked** | Edit the node in Settings → Infrastructure Connections and assign a credential (SSH type). |
| **SSH credential for node 'X' has no username set** | The credential has password but the **Username** field is empty. Edit the credential in Settings → Credentials and set the SSH username. |
| **SSH credential for node 'X' has no password or private key** | The credential has a username but no secret. Edit the credential and set the password (or paste the private key). |
| **Authentication failed** | Wrong password, wrong key, or key not in `private_key`/`api_key`. Check credential and that the app passes it (e.g. credential attached to the node, runbook uses that node). |
| **Node 'X' is not configured in Infrastructure Connections** | The server name (e.g. from runbook input `server_name` or ticket) doesn’t match any **Infrastructure Connection** name or `target_host`. Add a node for that server or fix the name. |
| **Connection refused** | Target host/port unreachable (firewall, SSH not on 22, wrong IP/hostname). Check `target_host`, `target_port`, and network from the worker/backend to the server. |
| **Using default local connector** | No matching infrastructure connection was found (e.g. `server_name` not resolved). Ensure runbook input or ticket provides the server name and that it matches an **Infrastructure Connection**. |

---

## Quick checklist for SSH connection

1. **Infrastructure Connection** exists for the server, with `connection_type = "ssh"`, `target_host` and (if needed) `target_port` set, and `credential_id` set.
2. **Credential** has `username` and either password (encrypted_password) or private key (encrypted_api_key).
3. **Server name** used at run time (e.g. from runbook input `server_name` or ticket) matches the connection’s **name** or **target_host**.
4. **Paramiko** is installed where the worker runs (otherwise SSH connector may use a simulated path and not really connect).
