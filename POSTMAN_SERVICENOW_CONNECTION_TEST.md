# Postman Test Guide for ServiceNow Connection

## Step 1: Get Authentication Token

### Request: Login
- **Method**: `POST`
- **URL**: `https://demo.resolvify.tech/api/v1/auth/login`
- **Headers**: 
  ```
  Content-Type: application/x-www-form-urlencoded
  ```
- **Body**: Select `x-www-form-urlencoded` tab (NOT raw JSON)
  - **Key**: `username` → **Value**: `demo@example.com`
  - **Key**: `password` → **Value**: `demo123`

**Important**: The backend expects form data, not JSON. Use `username` field (not `email`), even though the value is an email address.

### Response:
You'll get a token like:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Copy the `access_token` value.**

---

## Step 2: Create ServiceNow Connection

### Request: Create Connection
- **Method**: `POST`
- **URL**: `https://demo.resolvify.tech/api/v1/settings/ticketing-connections`
- **Headers**:
  ```
  Content-Type: application/json
  Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
  ```
- **Body** (raw JSON):

**Option A: Basic Auth (Username/Password)**
```json
{
  "tool_name": "servicenow",
  "connection_type": "api_poll",
  "api_base_url": "https://dev316876.service-now.com",
  "api_username": "resolvify.int",
  "api_password": "YOUR_SERVICENOW_PASSWORD",
  "sync_interval_minutes": 5
}
```

**Option B: OAuth (Client Credentials)**
```json
{
  "tool_name": "servicenow",
  "connection_type": "api_poll",
  "api_base_url": "https://dev316876.service-now.com",
  "sync_interval_minutes": 5,
  "meta_data": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  }
}
```

### Expected Response:
```json
{
  "id": 1,
  "tool_name": "servicenow",
  "connection_type": "api_poll",
  "is_active": true,
  "webhook_url": null,
  "message": "Ticketing tool connection created successfully"
}
```

---

## Step 3: Test the Connection

### Request: Test Connection
- **Method**: `POST`
- **URL**: `https://demo.resolvify.tech/api/v1/settings/ticketing-connections/{connection_id}/test`
- **Headers**:
  ```
  Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
  ```

Replace `{connection_id}` with the ID from Step 2.

### Expected Response (Success):
```json
{
  "status": "success",
  "message": "Connection test successful. Fetched X tickets.",
  "tickets_fetched": 10
}
```

### Expected Response (Error):
```json
{
  "status": "error",
  "message": "Connection test failed: Failed to fetch incidents from ServiceNow: 401",
  "tickets_fetched": 0
}
```

---

## Troubleshooting

### If you get 401 on Step 2 or 3:
1. **Check token expiration**: The token might be expired. Get a new one from Step 1.
2. **Check token format**: Make sure it's `Bearer <token>` (with space after Bearer)
3. **Check backend logs**: See what error the backend is returning

### If you get 401 from ServiceNow (in Step 3):
1. **Check credentials**: Verify username/password work in ServiceNow UI
2. **Check user permissions**: User needs `itil` role and REST API access
3. **Try OAuth**: If Basic Auth doesn't work, use OAuth Client Credentials

---

## Check Backend Logs

On your server, check what error the backend is returning:

```bash
docker compose -f docker-compose.production.yml logs --tail=50 backend | grep -i "401\|unauthorized\|jwt\|token"
```

This will show you why the token is being rejected.

