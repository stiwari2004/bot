# Troubleshooting: Worker reported failure / Step failed on first command

When you see **"Worker worker-dev reported failure"** (or any worker) on the first command, use the following to find the **actual error** and fix it.

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
| **SSH connector requires host and username** | Connection config is missing `host` or `username`. Ensure the **Infrastructure Connection** has `target_host` set and is linked to a **Credential** that has `username` (and password or key). |
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
