# Testing Next Steps - After Migration ✅

## ✅ Completed
- [x] Database connection verified
- [x] Database exists (`troubleshooting_ai_dev`)
- [x] Migration run successfully
- [x] Table `scheduled_reports` created

---

## Step 2: Backend Testing

### 2.1 Check Environment Variables
```bash
# Check if scheduler is enabled (should be true by default)
echo $ENABLE_REPORT_SCHEDULER

# Check scheduler interval (default: 300 seconds = 5 minutes)
echo $REPORT_SCHEDULER_INTERVAL
```

### 2.2 Start Backend Server

**If running locally:**
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**If running in Docker:**
```bash
# Check if backend container is running
docker ps | grep backend

# View backend logs
docker logs -f bot-backend-container-name

# Or restart backend if needed
docker-compose -f docker-compose.dev.yml restart backend
```

**What to look for in logs:**
- ✅ `"Report scheduler service started (check interval: 300s)"` ← **IMPORTANT!**
- ✅ `"Application startup complete"`
- ✅ No import errors
- ✅ No database connection errors

### 2.3 Test Backend Health

```bash
# Test if backend is responding
curl http://localhost:8000/health
# Or if using Docker/remote:
curl http://dev.resolvify.tech/health
```

**Expected:** `{"status":"ok"}` or similar

---

## Step 3: Get Authentication Token

### 3.1 Login as Super Admin

**IMPORTANT: Use the API endpoint, NOT the frontend URL!**

```bash
# Login endpoint (API endpoint - correct)
curl -X POST "https://dev.resolvify.tech/api/v1/super-admin/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@dev.resolvify.tech",
    "password": "dev123"
  }'
```

**NOT this (frontend page - wrong):**
```bash
# ❌ This is the frontend page, not the API
curl -X POST "https://dev.resolvify.tech/super-admin" ...
```

**Save the token from response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Set token as variable (for easier testing):**
```bash
export TOKEN="your_token_here"
```

---

## Step 4: Test Dashboard Overview API

```bash
# Test dashboard overview endpoint
curl -X GET "http://dev.resolvify.tech/api/v1/super-admin/dashboard/overview" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq .
```

**Expected response structure:**
```json
{
  "summary": {
    "total_tenants": 10,
    "active_tenants": 8,
    "total_users": 150,
    "total_nodes": 45,
    ...
  },
  "revenue": {
    "total_revenue": 50000,
    "fixed_revenue": 40000,
    ...
  },
  "usage": {
    "total_nodes": 45,
    "total_llm_tokens": 1000,
    ...
  },
  "alerts": [],
  "plan_distribution": {...}
}
```

**What to verify:**
- ✅ Status code: 200 OK
- ✅ Response contains all expected fields
- ✅ No errors in response
- ✅ Data looks reasonable

---

## Step 5: Test Scheduled Reports API

### 5.1 Create a Scheduled Report

```bash
curl -X POST "http://dev.resolvify.tech/api/v1/super-admin/reports/scheduled" \
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
  }' | jq .
```

**Expected:**
- ✅ Status code: 200 or 201
- ✅ Response includes `id`, `next_run_at` (calculated)
- ✅ `is_active` is `true`
- ✅ `created_by_id` matches your admin ID

### 5.2 List Scheduled Reports

```bash
curl -X GET "http://dev.resolvify.tech/api/v1/super-admin/reports/scheduled" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expected:**
- ✅ Returns array of reports
- ✅ Your test report appears in the list
- ✅ All fields are present

### 5.3 Get Single Report

```bash
# Replace 1 with the actual report ID from step 5.2
curl -X GET "http://dev.resolvify.tech/api/v1/super-admin/reports/scheduled/1" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### 5.4 Execute Report Manually

```bash
curl -X POST "http://dev.resolvify.tech/api/v1/super-admin/reports/scheduled/1/execute" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expected:**
- ✅ Status code: 200 OK
- ✅ Response indicates execution started
- ✅ Check backend logs for execution details
- ✅ Check email service logs (if email was sent)

### 5.5 Verify Database Updated

```bash
# Check if report was created in database
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, name, frequency, is_active, next_run_at FROM scheduled_reports;"

# Check if execution updated timestamps
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev -c "SELECT id, name, last_run_at, next_run_at FROM scheduled_reports WHERE id = 1;"
```

---

## Step 6: Test Frontend

### 6.1 Build Frontend (Check for Errors)

```bash
cd frontend-nextjs
npm install  # If needed
npm run build
```

**Expected:**
- ✅ No TypeScript errors
- ✅ No import errors
- ✅ Build completes successfully

### 6.2 Start Frontend Dev Server

```bash
npm run dev
```

**Expected:**
- ✅ Server starts on http://localhost:3000
- ✅ No console errors
- ✅ No build errors

### 6.3 Test Dashboard UI

1. **Navigate to Dashboard**
   - Go to: `http://dev.resolvify.tech/super-admin`
   - Login with super admin credentials
   - Should redirect to dashboard

2. **Test Analytics Tab**
   - [ ] Dashboard loads without errors
   - [ ] Summary cards display (Tenants, Users, Nodes, Trial Tenants)
   - [ ] Revenue Analytics section shows data
   - [ ] Usage Metrics section shows data
   - [ ] WebSocket connection indicator shows status

3. **Test Actions Tab**
   - [ ] Click "Actions" tab
   - [ ] All quick action buttons display
   - [ ] Navigation links work

4. **Test Reports Tab**
   - [ ] Click "Reports" tab
   - [ ] Quick Export section displays
   - [ ] Custom Report Builder displays
   - [ ] Scheduled Reports list displays

5. **Test Scheduled Reports**
   - [ ] Click "Create Schedule" button
   - [ ] Fill in form and create report
   - [ ] Verify report appears in list
   - [ ] Test "Execute Now" button
   - [ ] Test "Edit" button
   - [ ] Test "Delete" button

6. **Test Preferences Panel**
   - [ ] Click Settings button
   - [ ] Preferences panel opens
   - [ ] Toggle settings work
   - [ ] Preferences persist after reload

---

## Step 7: Test Background Scheduler

### 7.1 Verify Scheduler Started

**Check backend logs for:**
```
Report scheduler service started (check interval: 300s)
```

### 7.2 Test Scheduler Execution

**Option A: Wait for scheduled time**
- Create a report scheduled to run soon
- Wait for scheduler to execute
- Check logs and database

**Option B: Force immediate execution**
```bash
# Update report to run in the past
docker exec -i bot-dev-postgres psql -U postgres -d troubleshooting_ai_dev << 'EOF'
UPDATE scheduled_reports 
SET next_run_at = NOW() - INTERVAL '1 hour'
WHERE id = 1;
EOF

# Wait up to 5 minutes (scheduler check interval)
# Check backend logs for execution
```

**What to verify:**
- ✅ Scheduler picks up the report
- ✅ Report executes successfully
- ✅ `last_run_at` is updated
- ✅ `next_run_at` is recalculated
- ✅ Email is sent (check email logs)

---

## Step 8: Quick Verification Checklist

### Backend ✅
- [ ] Server starts without errors
- [ ] Scheduler starts (check logs)
- [ ] Dashboard overview endpoint works
- [ ] Scheduled reports CRUD works
- [ ] Report execution works

### Frontend ✅
- [ ] Build succeeds
- [ ] Dashboard loads
- [ ] All tabs work
- [ ] Scheduled reports UI works
- [ ] Preferences panel works

### Database ✅
- [ ] Migration completed
- [ ] Table exists
- [ ] Reports can be created
- [ ] Reports can be queried

### Integration ✅
- [ ] End-to-end flow works
- [ ] Reports execute successfully
- [ ] Emails are sent (if configured)

---

## Troubleshooting

### Backend won't start?
```bash
# Check logs
docker logs bot-backend-container-name

# Check for import errors
# Check for database connection errors
# Verify environment variables
```

### Scheduler not starting?
```bash
# Check environment variable
echo $ENABLE_REPORT_SCHEDULER

# Should be: true, 1, or yes
# If not set, scheduler won't start
```

### API returns 401?
```bash
# Token expired or invalid
# Get new token by logging in again
```

### Frontend shows errors?
```bash
# Check browser console (F12)
# Check for import errors
# Verify backend is running
# Check network tab for failed requests
```

---

## Next Steps After Testing

1. **If all tests pass:** ✅ Ready for production!
2. **If issues found:** Document issues and fix
3. **Performance testing:** Monitor under load
4. **User acceptance:** Get stakeholder feedback

---

**Ready to test! Start with Step 2 (Backend Testing) 🚀**
