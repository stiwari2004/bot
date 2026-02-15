# Prometheus, Grafana, and ServiceNow Integration Guide

This guide covers: (1) connecting Prometheus and Grafana to your Resolvify tool, and (2) linking the lab to ServiceNow for auto-ticket creation.

---

## Part 1: Prometheus + Grafana ↔ Your Tool

### 1.1 Prometheus scraping your backend

Your backend already exposes **`/metrics`** (Prometheus format) at:

- **Dev:** `https://dev.resolvify.tech/api` is under `/api`, so metrics are at **`https://dev.resolvify.tech/metrics`** (root of backend, not under `/api`). If nginx proxies only `/api` to the backend, ensure **`/metrics`** is also proxied to the backend, or that the backend is reachable at a URL that serves `/metrics`.
- **Local/Docker:** `http://localhost:8000/metrics` (or `http://backend:8000/metrics` from inside Docker).

**Steps:**

1. **Ensure `/metrics` is reachable**
   - If you use nginx and only `location /api` goes to the backend, add a `location /metrics` that proxies to the same backend (e.g. `proxy_pass http://127.0.0.1:8001;` for dev), or expose the backend port for Prometheus.
2. **Configure Prometheus to scrape the backend**
   - Add a job in `prometheus.yml`:
     ```yaml
     scrape_configs:
       - job_name: 'resolvify-backend'
         metrics_path: /metrics
         static_configs:
           - targets: ['<BACKEND_HOST>:<PORT>']   # e.g. backend:8000 (Docker) or your-server:8000
         scrape_interval: 15s
     ```
   - Replace `<BACKEND_HOST>` and `<PORT>` with the host/port where `/metrics` is served (e.g. `backend:8000` in Docker, or the host that serves dev).
3. **Reload Prometheus** (e.g. `curl -X POST http://localhost:9090/-/reload` if enabled, or restart Prometheus).

### 1.2 Grafana: add Prometheus data source

1. In **Grafana**: **Configuration** (gear) → **Data sources** → **Add data source**.
2. Choose **Prometheus**.
3. **URL**: your Prometheus server (e.g. `http://localhost:9090` or `http://prometheus:9090` if Prometheus runs in Docker).
4. **Save & test**.

### 1.3 Grafana: dashboards for your tool

1. **Create a new dashboard** or **Import** an existing one.
2. Add panels using Prometheus queries. Your backend and worker expose metrics such as:
   - `worker_assignments_total`
   - `session_state_transitions_total`
   - `execution_step_duration_seconds_*`
   - `llm_tokens_total`, `llm_budget_remaining_tokens`, `llm_budget_exceeded_total`
   - `connector_command_total`, `connector_command_latency_seconds_*`
3. Use these metric names in **Explore** or in panel **Query** to build dashboards.

---

## Part 2: Grafana → Your tool (alerts webhook)

Grafana can send alerts to your app so they appear as **Alerts** in the tool (and can be used for correlation or future auto-ticket creation).

### 2.1 Create a monitoring connection in the app (for tenant context)

1. In your app: go to **Settings** (or **Connections**) → **Monitoring connections**.
2. Add a **Prometheus** (or **custom**) connection with type **webhook**.
3. Note the **webhook URL** the app shows (e.g. `https://dev.resolvify.tech/api/v1/alerts/webhook/prometheus`).  
   - Base URL must be the public/base URL of your API (e.g. `https://dev.resolvify.tech`); the path is `/api/v1/alerts/webhook/prometheus`.

### 2.2 Configure Grafana to POST to the webhook

1. In **Grafana**: **Alerting** → **Contact points** → **New contact point**.
2. **Type**: **Webhook**.
3. **URL**: the webhook URL from step 2.1 (e.g. `https://dev.resolvify.tech/api/v1/alerts/webhook/prometheus`).
4. **HTTP Method**: POST.
5. Optional: set **Authorization** if your API requires it (e.g. Bearer token or basic auth).
6. **Save**.

Then attach this contact point to your **notification policies** (or to specific alert rules) so that when an alert fires, Grafana POSTs the payload to your app. The app will create an **Alert** record (not a ticket); tickets are created via ServiceNow (see Part 3).

**Webhook payload:** Grafana sends a JSON body. The app accepts a JSON object; it will parse it and create an alert. If you need a specific schema, refer to the alerts webhook handler in the codebase (`/api/v1/alerts/webhook/{source}`).

---

## Part 3: Link the lab to ServiceNow for auto-ticket creation

You have two ways to get tickets into ServiceNow: (A) **Pull** – app polls ServiceNow and shows tickets in the lab; (B) **Push** – create a ServiceNow incident when something happens (e.g. alert in the app or from Grafana).

### 3.1 ServiceNow connection in the app (pull + push)

1. In your app: **Settings** → **Ticketing connections** (or **Ticketing**).
2. **Add connection** → choose **ServiceNow**.
3. Fill in:
   - **Instance URL**: e.g. `https://your-instance.service-now.com`
   - **Auth**: Basic (username + password) or OAuth2 (client ID + client secret).
4. **Save** and **Test**. This connection is used to:
   - **Pull** tickets from ServiceNow into the app (polling).
   - **Push** (if you add or use “create ticket on alert”) to create incidents in ServiceNow from the app.

### 3.2 Pull: tickets from ServiceNow into the lab

1. With the ServiceNow connection saved and active, ensure **ticketing poller** is enabled (e.g. `ENABLE_TICKETING_POLLER=true` in backend env).
2. The app will periodically fetch incidents from ServiceNow and create/update **Tickets** in the lab. Users see them in the **Ticket Queue** / workspace.

### 3.3 Push: create a ServiceNow ticket when an alert fires (Grafana → App → ServiceNow)

Today the flow is:

1. **Grafana** → webhook → **App** creates an **Alert** (Part 2).
2. **ServiceNow** tickets are created by:
   - **Option A – From Grafana directly:** Use Grafana’s **ServiceNow** contact point (or a ServiceNow plugin/datasource) so that when an alert fires, Grafana also creates an incident in ServiceNow. No code change in your app.
   - **Option B – From the app:** Add a feature so that when the app receives a webhook and creates an Alert, it also calls the existing ServiceNow “create incident” API using the tenant’s ServiceNow ticketing connection (the app already has `ServiceNowConnector.create_ticket`). This would be a small backend change: “on webhook receive, if tenant has ServiceNow connection and ‘create ticket on alert’ is enabled, create incident in ServiceNow.”

**Steps for Option A (Grafana → ServiceNow):**

1. In Grafana: **Alerting** → **Contact points** → **New contact point**.
2. Choose **ServiceNow** (if available in your Grafana version) or a **Webhook** to a ServiceNow inbound integration (e.g. Inbound REST or Flow).
3. Configure instance URL and auth; save.
4. In **Notification policies**, add this contact point so that when alerts fire, Grafana creates a ServiceNow incident.

**Steps for Option B (App → ServiceNow):**

1. Ensure the tenant has a **ServiceNow ticketing connection** configured (3.1).
2. Request a backend change: when an alert is created via `/api/v1/alerts/webhook/prometheus` (or other source), optionally create a ServiceNow incident via the existing connector and link the alert to that ticket.

### 3.4 Summary: “Link the lab to ServiceNow for ticket creation”

| Goal                         | What to do |
|-----------------------------|------------|
| **See ServiceNow tickets in the lab** | Configure ServiceNow in **Settings → Ticketing**; enable ticketing poller. |
| **Create ServiceNow ticket when Grafana alerts** | Use Grafana ServiceNow contact point (Option A) or add “create ticket on alert” in app (Option B). |
| **Create ServiceNow ticket from the app**        | Use existing flow that calls `ServiceNowConnector.create_ticket` (e.g. from runbook or escalation); ensure tenant has ServiceNow connection configured. |

---

## Checklist

- [ ] Backend `/metrics` reachable; Prometheus scrape config added and reloaded.
- [ ] Grafana: Prometheus data source added and tested.
- [ ] Grafana: Dashboards created using backend/worker metrics.
- [ ] App: Monitoring connection (webhook) created; Grafana contact point URL set to `/api/v1/alerts/webhook/prometheus`.
- [ ] Grafana: Alert rules and contact point so alerts POST to the app (and optionally to ServiceNow).
- [ ] App: ServiceNow ticketing connection added and tested.
- [ ] Ticketing poller enabled so ServiceNow tickets appear in the lab.
- [ ] (Optional) Grafana → ServiceNow contact point **or** app “create ServiceNow ticket on alert” for auto-ticket creation.
