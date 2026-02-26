# Execution sessions: cancel and stuck runs

## Clearing stuck executions

If an execution is stuck (e.g. pre-check failed with "command not found" and the run never completes):

1. **From the UI**  
   Go to **Executions** → **Active Sessions**. Each active session has a **Cancel** button. Use it to mark the session as abandoned and clear it from the active list.

2. **Via API**  
   Cancel a session with:

   ```http
   POST /api/v1/agent/{session_id}/cancel
   ```

   Use the same auth as other API calls (e.g. `Authorization: Bearer <token>`). On success the session status is set to `abandoned` and it no longer appears as running.

   Example with curl (replace `SESSION_ID` and use your token):

   ```bash
   curl -X POST "https://your-app/api/v1/agent/SESSION_ID/cancel" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

## Perplexity / "sync taking too long"

Command validation uses the Perplexity API. If you see timeouts or "sync taking too long":

- Set **`PERPLEXITY_TIMEOUT`** (seconds) in `.env`. Default is `120`; allowed range 30–300. Example: `PERPLEXITY_TIMEOUT=180`.
- The service retries once on timeout; increasing the timeout can help when the API is slow.

## Pre-check "command not found"

If execution fails at the pre-check stage with "command not found", the runbook’s pre-check command may not exist on the target (e.g. different OS or path). Update the runbook so the pre-check command is valid on the target, or remove it if not required. After a pre-check failure the session should still complete (with errors); if it appears stuck, use **Cancel** above.
