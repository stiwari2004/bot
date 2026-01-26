# Testing Guide - Step by Step

## 🚀 Quick Start Testing

### Step 1: Pre-Testing Checks ✅

#### 1.1 Database Connection & Verification (FIRST)
**Before running migrations, verify database connection and existence:**

**Step 1: Find your PostgreSQL container name**
```bash
# List running containers to find PostgreSQL container
docker ps | grep postgres

# Or list all containers (including stopped)
docker ps -a | grep postgres
```

**Common container names:**
- `bot-prod-postgres` (production)
- `bot-dev-postgres` (development)

**Step 2: Test PostgreSQL connection**
```bash
# Replace CONTAINER_NAME with your actual container name (e.g., bot-prod-postgres)
docker exec -i CONTAINER_NAME psql -U postgres -d postgres -c "SELECT version();"
```

**Step 3: Check if your database exists**
```bash
# List all databases
docker exec -i CONTAINER_NAME psql -U postgres -d postgres -c "\l"

# Look for 'troubleshooting_ai' in the list
```

**Step 4: Create database if it doesn't exist (if needed)**
```bash
# Only run this if troubleshooting_ai doesn't exist
docker exec -i CONTAINER_NAME psql -U postgres -d postgres -c "CREATE DATABASE troubleshooting_ai;"
```

**Step 5: Verify connection to your specific database**
```bash
# Test connection to troubleshooting_ai database
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -c "SELECT current_database();"
```

**Example with your setup (assuming container name is `bot-prod-postgres`):**
```bash
# Test connection
docker exec -i bot-prod-postgres psql -U postgres -d postgres -c "SELECT version();"

# Check databases
docker exec -i bot-prod-postgres psql -U postgres -d postgres -c "\l"

# Verify troubleshooting_ai database
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -c "SELECT current_database();"
```

#### 1.2 Database Migration (AFTER Connection Verified)
**Once connection is verified, run the migration:**

**Option 1: Copy SQL file into container and run (Recommended)**
```bash
# Copy the SQL file into the container
docker cp backend/sql/create_scheduled_reports_table.sql CONTAINER_NAME:/tmp/create_scheduled_reports_table.sql

# Run the migration
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -f /tmp/create_scheduled_reports_table.sql

# Clean up (optional)
docker exec -i CONTAINER_NAME rm /tmp/create_scheduled_reports_table.sql
```

**Option 2: Pipe SQL file directly (if file is accessible from host)**
```bash
# Run migration by piping SQL file
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai < backend/sql/create_scheduled_reports_table.sql
```

**Example with your setup:**
```bash
# Copy SQL file into container
docker cp backend/sql/create_scheduled_reports_table.sql bot-prod-postgres:/tmp/create_scheduled_reports_table.sql

# Run migration
docker exec -i bot-prod-postgres psql -U postgres -d troubleshooting_ai -f /tmp/create_scheduled_reports_table.sql
```

**Verify migration succeeded:**
```bash
# Check table exists
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -c "\d scheduled_reports"

# Check enum types
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -c "\dT+ reportfrequency"
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -c "\dT+ reportformat"
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -c "\dT+ reporttype"

# Check indexes
docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -c "\d scheduled_reports"
```

#### 1.3 Environment Variables
Check your `.env` file or environment:
```bash
ENABLE_REPORT_SCHEDULER=true  # Default: true
REPORT_SCHEDULER_INTERVAL=300  # Default: 300 seconds (5 minutes)
```

#### 1.4 Code Verification
- ✅ All imports verified (no linter errors)
- ✅ All components created
- ✅ All services refactored

---

### Step 2: Backend Testing

#### 2.1 Start Backend Server
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
- ✅ Server starts without errors
- ✅ Look for: `"Report scheduler service started (check interval: 300s)"`
- ✅ No import errors in logs

#### 2.2 Test Dashboard Overview Endpoint
```bash
# Get your auth token first, then:
curl -X GET "http://localhost:8000/api/v1/super-admin/dashboard/overview" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected:**
- ✅ Returns 200 OK
- ✅ Response includes: `summary`, `revenue`, `usage`, `alerts`, `plan_distribution`
- ✅ All aggregators working correctly

#### 2.3 Test Scheduled Reports API

**Create a scheduled report:**
```bash
curl -X POST "http://localhost:8000/api/v1/super-admin/reports/scheduled" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Weekly Report",
    "description": "Test report",
    "report_type": "overview",
    "format": "pdf",
    "frequency": "weekly",
    "schedule_config": {"time": "09:00", "timezone": "UTC"},
    "recipients": ["admin@example.com"]
  }'
```

**List scheduled reports:**
```bash
curl -X GET "http://localhost:8000/api/v1/super-admin/reports/scheduled" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Execute a report manually:**
```bash
curl -X POST "http://localhost:8000/api/v1/super-admin/reports/scheduled/1/execute" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
- ✅ All endpoints return 200 OK
- ✅ Reports are created/listed/executed correctly
- ✅ `next_run_at` is calculated correctly
- ✅ Email notifications sent (check email logs)

---

### Step 3: Frontend Testing

#### 3.1 Build Frontend
```bash
cd frontend-nextjs
npm install  # If needed
npm run build
```

**Expected:**
- ✅ No TypeScript errors
- ✅ No import errors
- ✅ Build completes successfully

#### 3.2 Start Frontend Dev Server
```bash
npm run dev
```

**Expected:**
- ✅ Server starts on http://localhost:3000
- ✅ No console errors
- ✅ All components load

#### 3.3 Test Dashboard UI

**3.3.1 Analytics Tab**
- [ ] Navigate to `/super-admin`
- [ ] Verify Analytics tab is active by default
- [ ] Check all summary cards display:
  - Total Tenants
  - Trial Tenants
  - Total Users
  - Total Nodes
- [ ] Verify Revenue Analytics section shows data
- [ ] Verify Usage Metrics section shows data
- [ ] Check WebSocket connection indicator (Live/Polling)

**3.3.2 Actions Tab**
- [ ] Click "Actions" tab
- [ ] Verify all quick action buttons display
- [ ] Test navigation links (should navigate to respective pages)
- [ ] Test "Refresh Dashboard" button

**3.3.3 Reports Tab**
- [ ] Click "Reports" tab
- [ ] Verify three sections display:
  - Quick Export
  - Custom Report Builder
  - Scheduled Reports

**Quick Export:**
- [ ] Click PDF/CSV buttons for each report type
- [ ] Verify files download with correct names
- [ ] Check file formats are correct

**Custom Report Builder:**
- [ ] Select different report types
- [ ] Select PDF/CSV format
- [ ] Set date ranges
- [ ] Click "Generate Report"
- [ ] Verify report generates and downloads

**Scheduled Reports:**
- [ ] Click "Create Schedule" button
- [ ] Fill in modal form:
  - Name: "Test Report"
  - Report Type: Overview
  - Format: PDF
  - Frequency: Weekly
  - Time: 09:00
  - Recipients: your-email@example.com
- [ ] Click "Create Schedule"
- [ ] Verify report appears in list
- [ ] Test "Execute Now" button
- [ ] Test "Edit" button (opens modal with pre-filled data)
- [ ] Test "Delete" button (with confirmation)

**3.3.4 Preferences Panel**
- [ ] Click Settings button
- [ ] Verify preferences panel opens
- [ ] Toggle "Auto Refresh"
- [ ] Change "Refresh Interval"
- [ ] Toggle widget visibility (if widgets exist)
- [ ] Close panel
- [ ] Reload page and verify preferences persist

---

### Step 4: Background Scheduler Testing

#### 4.1 Verify Scheduler Started
Check backend logs for:
```
Report scheduler service started (check interval: 300s)
```

#### 4.2 Test Scheduler Execution
1. Create a scheduled report with `next_run_at` set to past time:
   ```sql
   UPDATE scheduled_reports 
   SET next_run_at = NOW() - INTERVAL '1 hour'
   WHERE id = 1;
   ```

2. Wait for scheduler to run (or check logs)
3. Verify:
   - Report executed (check logs)
   - `last_run_at` updated
   - `next_run_at` recalculated
   - Email sent (check email service logs)

#### 4.3 Monitor Scheduler
Watch backend logs for:
- Periodic checks: `"Found X scheduled report(s) due for execution"`
- Execution logs: `"Executed scheduled report X and sent to Y recipients"`
- Error handling: Any errors should be logged but not crash scheduler

---

### Step 5: Integration Testing

#### 5.1 End-to-End Flow
1. Create scheduled report via UI
2. Verify it appears in list
3. Execute manually via UI
4. Verify email received
5. Check database for updated timestamps

#### 5.2 Error Handling
- [ ] Test with invalid report configuration
- [ ] Test with missing recipients
- [ ] Test with invalid date ranges
- [ ] Verify graceful error messages

---

## 🐛 Common Issues & Solutions

### Issue: Import Errors
**Solution:** Verify all new files are in correct directories and `__init__.py` files exist

### Issue: Database Migration Fails
**Solution:** Check PostgreSQL version, ensure enum types don't already exist

### Issue: Scheduler Not Starting
**Solution:** Check `ENABLE_REPORT_SCHEDULER` env var, check logs for errors

### Issue: Frontend Components Not Rendering
**Solution:** Check browser console for errors, verify imports are correct

### Issue: Reports Not Generating
**Solution:** Check backend logs, verify report service is working

---

## ✅ Success Criteria

### Backend
- ✅ All endpoints return correct responses
- ✅ Scheduler starts and runs periodically
- ✅ Reports execute successfully
- ✅ Emails are sent
- ✅ Database operations work correctly

### Frontend
- ✅ All components render correctly
- ✅ No console errors
- ✅ All interactions work (buttons, forms, modals)
- ✅ Data displays correctly
- ✅ Preferences persist

### Integration
- ✅ End-to-end flows work
- ✅ Error handling is graceful
- ✅ Performance is acceptable

---

## 📝 Testing Checklist

Use `TESTING_CHECKLIST.md` for detailed item-by-item testing.

---

## 🎯 Next Steps After Testing

1. **If all tests pass:** Deploy to staging/production
2. **If issues found:** Document and fix, then retest
3. **Performance testing:** Monitor under load
4. **User acceptance testing:** Get feedback from stakeholders

---

**Ready to begin testing! 🚀**
