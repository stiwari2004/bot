# Quick API Test Commands - Copy & Paste Ready

## Base URL
- **API Base**: `https://dev.resolvify.tech/api/v1`
- **Frontend**: `https://dev.resolvify.tech/super-admin` (for browser testing)

---

## Step 1: Login & Get Token

```bash
curl -X POST "https://dev.resolvify.tech/api/v1/super-admin/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@dev.resolvify.tech",
    "password": "dev123"
  }'
```

**Save the token from response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Set as variable:**
```bash
export TOKEN="paste_your_token_here"
```

---

## Step 2: Test Dashboard Overview

```bash
curl -X GET "https://dev.resolvify.tech/api/v1/super-admin/dashboard/overview" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

---

## Step 3: Test Scheduled Reports API

### Create a Scheduled Report
```bash
curl -X POST "https://dev.resolvify.tech/api/v1/super-admin/reports/scheduled" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Weekly Report",
    "description": "Test report for verification",
    "report_type": "overview",
    "format": "pdf",
    "frequency": "weekly",
    "schedule_config": {
      "time": "09:00",
      "timezone": "UTC"
    },
    "recipients": ["admin@dev.resolvify.tech"]
  }'
```

### List Scheduled Reports
```bash
curl -X GET "https://dev.resolvify.tech/api/v1/super-admin/reports/scheduled" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Single Report (replace 1 with actual ID)
```bash
curl -X GET "https://dev.resolvify.tech/api/v1/super-admin/reports/scheduled/1" \
  -H "Authorization: Bearer $TOKEN"
```

### Execute Report Manually
```bash
curl -X POST "https://dev.resolvify.tech/api/v1/super-admin/reports/scheduled/1/execute" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Step 4: Verify in Database

```bash
# Check reports in database
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, name, frequency, is_active, next_run_at FROM scheduled_reports;"
```

---

## Complete Test Sequence (Copy-Paste)

```bash
# 1. Login
TOKEN=$(curl -s -X POST "https://dev.resolvify.tech/api/v1/super-admin/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@dev.resolvify.tech", "password": "dev123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo "Token: $TOKEN"

# 2. Test Dashboard Overview
curl -X GET "https://dev.resolvify.tech/api/v1/super-admin/dashboard/overview" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# 3. Create Scheduled Report
curl -X POST "https://dev.resolvify.tech/api/v1/super-admin/reports/scheduled" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Weekly Report",
    "description": "Test report",
    "report_type": "overview",
    "format": "pdf",
    "frequency": "weekly",
    "schedule_config": {"time": "09:00", "timezone": "UTC"},
    "recipients": ["admin@dev.resolvify.tech"]
  }'

# 4. List Reports
curl -X GET "https://dev.resolvify.tech/api/v1/super-admin/reports/scheduled" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Frontend Testing (Browser)

1. **Open browser**: `https://dev.resolvify.tech/super-admin`
2. **Login** with credentials:
   - Email: `admin@dev.resolvify.tech`
   - Password: `dev123`
3. **Test dashboard**:
   - Analytics tab should show data
   - Reports tab should show scheduled reports
   - Create/edit/delete reports via UI

---

## Troubleshooting

### Getting HTML instead of JSON?
- ✅ You're using the API endpoint (`/api/v1/...`)
- ❌ You're hitting the frontend page (`/super-admin`)

### 401 Unauthorized?
- Token expired or invalid
- Get a new token by logging in again

### 404 Not Found?
- Check if backend is running
- Verify endpoint path is correct
