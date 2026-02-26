# PAAS LLM Keys: Risk and Options (Central Fetch / Keep Hidden)

## Why this matters

Putting API keys (GEMINI_API_KEY, PERPLEXITY_API_KEY, etc.) in a `.env` file on each PAAS/client instance creates real risk:

- **Exposure**: Anyone with access to the server (SSH, backup, or compromise) can read the keys.
- **Financial**: Stolen keys can be abused until you rotate them; rotation today means touching every PAAS instance.
- **Idea exposure**: The presence of keys reveals which providers you use (Gemini, Perplexity, etc.).

You should not have to hand out keys to every PAAS deployment if you can avoid it.

---

## Option 1: Fetch keys from Central (recommended for future)

**Idea**: Keys live only on the central Resolvify server. PAAS edges never store them on disk; they fetch a minimal config at runtime from central and cache in memory.

### Flow

1. **Central** (resolvify.tech / your SaaS) stores LLM config in a secure way (env, secrets manager, or encrypted DB):
   - e.g. `GEMINI_API_KEY`, `GEMINI_MODEL`, optionally `PERPLEXITY_API_KEY`.
2. **Central** exposes an endpoint only for authenticated edges, e.g.:
   - `GET /api/v1/paas/edge-config`
   - Auth: `X-Paas-API-Key: <CENTRAL_API_KEY>` (same key edges already use for validate-login / billing).
   - Response (JSON): `{ "GEMINI_API_KEY": "...", "GEMINI_MODEL": "gemini-2.5-flash", "PERPLEXITY_API_KEY": "..." }`.
   - Central should only allow this for known PAAS tenants/edges (validate the API key and optionally tenant/edge id).
3. **Edge (PAAS)** at startup (or on first LLM use):
   - If `CENTRAL_SERVER_URL` and `CENTRAL_API_KEY` are set and `GEMINI_API_KEY` is *not* in env:
   - Calls `GET {CENTRAL_SERVER_URL}/api/v1/paas/edge-config` with `X-Paas-API-Key`.
   - On success, caches the returned keys **in process memory only** (never write to disk).
   - Uses this cache for LLM calls; falls back to env if central is unreachable and env is set.
4. **Result**: PAAS `.env` only needs `CENTRAL_SERVER_URL` and `CENTRAL_API_KEY` (already used for login/billing). No GEMINI or PERPLEXITY keys on the client.

### What to build

- **Central**: New endpoint e.g. in `paas_auth.py` or a new `paas_config.py`:
  - Validate `X-Paas-API-Key` (and optionally which edge/tenant).
  - Return a JSON object with only the keys the edge is allowed to use (e.g. GEMINI_API_KEY, GEMINI_MODEL, PERPLEXITY_API_KEY).
  - Prefer reading from existing central config (env or secrets manager), not from a DB of raw keys, so you don’t duplicate secret storage.
- **Edge**: In `central_client.py` add e.g. `fetch_edge_config() -> Optional[Dict[str, str]]`.
- **Edge**: In `llm_service.py` (and wherever LLM is used): if `GEMINI_API_KEY` not in env, call `fetch_edge_config()` once (or on first use), cache in memory, use returned values. Same for worker process if it uses LLM.
- **Security**: Use HTTPS for central; keep `PAAS_EDGE_API_KEY` strong and rotated; consider short-lived tokens later if you need tighter control.

This gives you “fetch from central” so PAAS never has to hold LLM keys in a file.

---

## Option 2: LLM proxy through Central

**Idea**: PAAS does not get any LLM key. When the edge needs an LLM call, it sends the request (e.g. prompt + model) to central; central calls Gemini/Perplexity with its own keys and returns the response.

- **Pros**: Keys only at central; PAAS cannot leak them.
- **Cons**: All LLM traffic goes through central (latency, single point of failure, central must scale and stay up). Requires a new central endpoint and request/response format.

Use this if you want maximum lock-down and accept the operational and latency tradeoffs.

---

## Option 3: Keep keys hidden on PAAS (short-term hardening)

If you keep keys on the PAAS instance for now, you can still reduce exposure:

1. **File permissions**: `chmod 600 .env` so only the process owner can read it; run the container as a dedicated user.
2. **Never commit**: Ensure `.env` is in `.gitignore` and is not in any image or backup that goes to untrusted hands.
3. **Secrets manager**: On the host (e.g. HashiCorp Vault, AWS Secrets Manager, Azure Key Vault), store the keys and inject them into the container at start (e.g. via entrypoint that fetches and sets env vars). The container then never has a `.env` file with keys on disk.
4. **Encrypted .env**: Store `.env` encrypted; decrypt at container start with a key that only your deployment system has (so casual SSH cannot decrypt without that key). More complex to operate.

These don’t remove keys from the machine entirely but make them harder to see and copy.

---

## Recommendation

- **Short term**: Use Option 3 (permissions + no commit; optionally secrets manager or encrypted .env) so current PAAS deployments are less exposed.
- **Medium term**: Implement Option 1 (fetch from central) so PAAS only needs `CENTRAL_SERVER_URL` and `CENTRAL_API_KEY` in `.env`, and LLM keys are only on central and in edge process memory.

If you want to proceed with Option 1, the next concrete steps are: (1) add `GET /api/v1/paas/edge-config` on central and (2) add `fetch_edge_config()` plus in-memory cache and wiring in the edge LLM service and worker.
