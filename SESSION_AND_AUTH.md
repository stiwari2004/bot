# Session and auth during long runs

## Logout during runbook execution (by design)

- **Regular login** uses JWT with a fixed lifetime. Default is **30 minutes** (`ACCESS_TOKEN_EXPIRE_MINUTES` in backend config).
- When the token expires, the next API call returns **401 Unauthorized**. The frontend then clears the token and redirects to login (**by design** for security).
- **Execution continues on the server**; only the UI session is lost. So the runbook does not stop, but the dashboard can no longer poll for status until you log in again.

## Avoiding logout during long sessions

1. **Increase token lifetime** for dev or long-running use:
   - In `backend/.env` set: `ACCESS_TOKEN_EXPIRE_MINUTES=480` (8 hours) or higher.
   - Restart the backend so the new value is applied.
2. **Stuck session**: If you were logged out mid-execution, log in again and open the same ticket/runbook; the execution session is still in the database and may be viewable from the execution/history views if the app exposes them.

## Server/node not in commands

- Commands are built from **runbook inputs** (e.g. `{{server_name}}`, `{{host_ip}}`). Input extraction is **tool-agnostic**: the same logic runs for tickets from any source (ServiceNow, Zendesk, Jira, ManageEngine, api_poll, etc.).
- We now parse **description and short description** for:
  - **host_ip**: first IP address in the text.
  - **server_name**: “Host: name”, “Server: name”, “Node: name”, FQDN, or a hostname next to an IP (e.g. `srv640992 1.2.3.4`).
- Ensure the runbook YAML declares `inputs` with `name: server_name` and/or `name: host_ip` so the normalizer can substitute them. If the ticket has the node name and IP in the description/short description, they will be extracted and used in the commands.
