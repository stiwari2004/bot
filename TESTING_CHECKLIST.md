# Testing Checklist - Reporting System & Refactoring

## Pre-Testing Setup

### 1. Database Connection & Verification (FIRST)
- [ ] Find PostgreSQL container: `docker ps | grep postgres`
- [ ] Test PostgreSQL connection: `docker exec -i CONTAINER_NAME psql -U postgres -d postgres -c "SELECT version();"`
- [ ] Check if database exists: `docker exec -i CONTAINER_NAME psql -U postgres -d postgres -c "\l"`
- [ ] Create database if it doesn't exist: `docker exec -i CONTAINER_NAME psql -U postgres -d postgres -c "CREATE DATABASE troubleshooting_ai;"`
- [ ] Verify connection to specific database: `docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -c "SELECT current_database();"`

### 2. Database Migration (AFTER Connection Verified)
- [ ] Copy SQL file into container: `docker cp backend/sql/create_scheduled_reports_table.sql CONTAINER_NAME:/tmp/create_scheduled_reports_table.sql`
- [ ] Run SQL migration: `docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -f /tmp/create_scheduled_reports_table.sql`
- [ ] Verify table `scheduled_reports` exists: `docker exec -i CONTAINER_NAME psql -U postgres -d troubleshooting_ai -c "\d scheduled_reports"`
- [ ] Verify enum types created: `reportfrequency`, `reportformat`, `reporttype`
- [ ] Verify indexes are created:
  - `idx_scheduled_reports_created_by_id`
  - `idx_scheduled_reports_is_active`
  - `idx_scheduled_reports_next_run_at`
  - `idx_scheduled_reports_created_at`

### 3. Environment Variables
- [ ] Set `ENABLE_REPORT_SCHEDULER=true` (or leave default)
- [ ] Optionally set `REPORT_SCHEDULER_INTERVAL=300` (5 minutes, default)

### 4. Backend Startup
- [ ] Start backend server
- [ ] Verify scheduler starts: Look for log message "Report scheduler service started"
- [ ] Check for any import errors or missing dependencies

### 5. Frontend Build
- [ ] Run `npm install` (if needed)
- [ ] Verify no TypeScript errors: `npm run build` or check IDE
- [ ] Verify all components are properly imported

---

## Functional Testing

### Dashboard Analytics Tab
- [ ] Dashboard loads without errors
- [ ] Analytics tab displays:
  - [ ] Summary cards (Tenants, Users, Nodes, Trial Tenants)
  - [ ] Revenue Analytics section
  - [ ] Usage Metrics section
  - [ ] Critical Alerts (if any)
  - [ ] Plan Distribution (if available)
- [ ] WebSocket connection indicator shows correct status
- [ ] Settings button opens/closes preferences panel

### Dashboard Actions Tab
- [ ] Actions tab displays quick action buttons
- [ ] All navigation links work:
  - [ ] Manage Tenants
  - [ ] User Management
  - [ ] Billing Management
  - [ ] Subscription Management
  - [ ] License Plans
  - [ ] Refresh Dashboard

### Dashboard Reports Tab

#### Quick Export
- [ ] Quick Export section displays three report cards
- [ ] PDF export buttons work for:
  - [ ] Platform Overview
  - [ ] Tenant Report
  - [ ] Revenue Report
- [ ] CSV export buttons work for:
  - [ ] Platform Overview
  - [ ] Tenant Report
  - [ ] Revenue Report
- [ ] Files download with correct names and formats

#### Custom Report Builder
- [ ] Form fields are displayed:
  - [ ] Report Type dropdown
  - [ ] Format dropdown (PDF/CSV)
  - [ ] Start Date input
  - [ ] End Date input
- [ ] "Generate Report" button works
- [ ] Error messages display if generation fails
- [ ] Successfully generates and downloads reports

#### Scheduled Reports
- [ ] "Create Schedule" button opens modal
- [ ] Modal form includes all fields:
  - [ ] Report Name
  - [ ] Description
  - [ ] Report Type
  - [ ] Format
  - [ ] Frequency (Daily/Weekly/Monthly)
  - [ ] Time
  - [ ] Recipients (email list)
- [ ] Can create new scheduled report
- [ ] Can edit existing scheduled report
- [ ] Can delete scheduled report (with confirmation)
- [ ] Can execute scheduled report manually
- [ ] Scheduled reports list displays correctly:
  - [ ] Report name, description
  - [ ] Active/Inactive status badge
  - [ ] Report type, frequency, next run time
  - [ ] Recipient count
- [ ] Empty state displays when no reports exist

### Preferences Panel
- [ ] Opens/closes correctly
- [ ] Auto Refresh toggle works
- [ ] Refresh Interval input works
- [ ] Widget Visibility toggles work (if widgets exist)
- [ ] Preferences persist after page reload

---

## Backend API Testing

### Scheduled Reports Endpoints
- [ ] `POST /api/v1/super-admin/reports/scheduled` - Create report
- [ ] `GET /api/v1/super-admin/reports/scheduled` - List reports
- [ ] `GET /api/v1/super-admin/reports/scheduled/{id}` - Get single report
- [ ] `PUT /api/v1/super-admin/reports/scheduled/{id}` - Update report
- [ ] `DELETE /api/v1/super-admin/reports/scheduled/{id}` - Delete report
- [ ] `POST /api/v1/super-admin/reports/scheduled/{id}/execute` - Execute report

### Custom Report Generation
- [ ] `POST /api/v1/super-admin/reports/generate` - Generate custom report
- [ ] Returns correct format (PDF/CSV)
- [ ] Applies filters correctly

---

## Background Scheduler Testing

### Scheduler Functionality
- [ ] Scheduler starts on backend startup
- [ ] Scheduler checks for due reports periodically
- [ ] Executes reports that are due
- [ ] Updates `last_run_at` and `next_run_at` after execution
- [ ] Sends email notifications to recipients
- [ ] Logs execution results
- [ ] Handles errors gracefully (doesn't crash)

### Manual Testing
- [ ] Create a scheduled report with `next_run_at` in the past
- [ ] Verify scheduler picks it up and executes
- [ ] Verify email is sent (check email logs/service)
- [ ] Verify `last_run_at` is updated
- [ ] Verify `next_run_at` is recalculated

---

## Code Quality Verification

### Frontend
- [ ] No console errors in browser
- [ ] No TypeScript errors
- [ ] Components are properly separated
- [ ] Hooks are reusable
- [ ] Code follows React best practices

### Backend
- [ ] No Python syntax errors
- [ ] No import errors
- [ ] Endpoints use proper error handling
- [ ] Response models use `from_orm` helper
- [ ] Code follows MVC pattern

---

## Performance Testing

- [ ] Dashboard loads within acceptable time (< 2 seconds)
- [ ] Report generation completes within reasonable time
- [ ] Scheduled reports execute without blocking other operations
- [ ] No memory leaks (check over extended period)

---

## Edge Cases

- [ ] Handle missing authentication token
- [ ] Handle network errors gracefully
- [ ] Handle invalid report configurations
- [ ] Handle missing recipients
- [ ] Handle invalid date ranges
- [ ] Handle scheduler failures (service unavailable, etc.)

---

## Notes
- Test with different user roles/permissions
- Test with various report configurations
- Monitor logs during testing
- Check database state after operations
