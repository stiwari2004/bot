# Reporting System - Pending Tasks

## Status
✅ Dynamic reporting with custom filters - **Implemented**
✅ Scheduled reports CRUD - **Implemented**
✅ Frontend UI for report builder and scheduling - **Implemented**
✅ Database migration - **Completed**
✅ Background job scheduler - **Completed**
✅ Code quality review & MVC refactoring - **Completed**

---

## 1. Database Migration

### Task: Create migration for `scheduled_reports` table

**File to create:** `backend/alembic/versions/XXXX_create_scheduled_reports.py`

**Table Schema:**
```python
- id: Integer (PK)
- name: String(255)
- description: Text (nullable)
- report_type: Enum(ReportType)
- format: Enum(ReportFormat)
- filters: JSON (nullable)
- frequency: Enum(ReportFrequency)
- schedule_config: JSON (nullable)
- recipients: JSON
- is_active: Boolean (default=True)
- last_run_at: DateTime(timezone=True, nullable)
- next_run_at: DateTime(timezone=True, nullable)
- created_by_id: Integer (FK -> super_admins.id)
- created_at: DateTime(timezone=True)
- updated_at: DateTime(timezone=True)
```

**Indexes needed:**
- `created_by_id` (for filtering by admin)
- `is_active` (for querying active reports)
- `next_run_at` (for finding reports due for execution)

---

## 2. Background Job Scheduler

### Task: Set up automated execution of scheduled reports

**Options:**
1. **Celery + Redis/RabbitMQ** (recommended for production)
2. **APScheduler** (simpler, good for single-server setup)
3. **Cron job** calling FastAPI endpoint
4. **Background task in FastAPI** using `asyncio` or `BackgroundTasks`

**Implementation needed:**
- Periodic task that calls `ScheduledReportService.get_reports_due_for_execution()`
- Execute each due report using `ScheduledReportService.execute_scheduled_report(report_id)`
- Handle errors gracefully and log execution results
- Update `last_run_at` and `next_run_at` after execution

**Location:** `backend/app/services/reporting/report_scheduler.py` (new file)

**Integration point:** Add startup event in `backend/app/main.py` or create separate scheduler service

---

## 3. Code Quality Review & MVC Refactoring

### Issues Identified:
1. **Verbose code** - Some functions/classes have grown too large
2. **MVC pattern** - Need to ensure proper separation of concerns
3. **Service layer** - May need better abstraction

### Areas to Review:

#### Backend:
- `backend/app/api/v1/endpoints/reporting.py`
  - Response model serialization is repetitive
  - Consider using Pydantic's `from_orm` or `model_validate`
  
- `backend/app/services/reporting/scheduled_report_service.py`
  - `_calculate_next_run_time` method is complex - consider breaking down
  - `execute_scheduled_report` mixes concerns (generation + email + DB update)
  
- `backend/app/services/reporting/report_service.py`
  - Filter application logic could be extracted to separate filter classes
  - Report generation methods are similar - consider template pattern

#### Frontend:
- `frontend-nextjs/src/app/super-admin/page.tsx`
  - File is very large (1267 lines) - consider splitting into components:
    - `SuperAdminDashboard.tsx` (main component)
    - `DashboardAnalytics.tsx` (analytics tab)
    - `DashboardActions.tsx` (actions tab)
    - `DashboardReports.tsx` (reports tab)
    - `PreferencesPanel.tsx` (settings panel)
    - `ScheduledReportModal.tsx` (create/edit modal)
  - State management could use custom hooks:
    - `useScheduledReports.ts`
    - `useCustomReport.ts`
  - Form handling in modal could use React Hook Form

### Refactoring Plan:

1. **Extract Components:**
   - Break down large page component into smaller, focused components
   - Create reusable UI components for report cards, filters, etc.

2. **Extract Hooks:**
   - Move scheduled reports logic to `useScheduledReports` hook
   - Move custom report logic to `useCustomReport` hook

3. **Backend Service Layer:**
   - Extract filter logic to `ReportFilterService`
   - Extract email logic to separate method/service
   - Use dependency injection for better testability

4. **Response Models:**
   - Use Pydantic's `from_orm` to reduce boilerplate
   - Create base response models for common patterns

---

## 4. Additional Improvements

### Email Integration:
- Currently sends basic email notification
- Should attach actual report file (PDF/CSV) to email
- Need to integrate with export endpoints to generate file, then attach

### Report Execution:
- Add retry logic for failed executions
- Add execution history/logging
- Add notification on execution failure

### UI Enhancements:
- Add loading states for report generation
- Add success/error notifications
- Add preview functionality before scheduling
- Add report execution history view

---

## Files Created/Modified:

### Backend:
- ✅ `backend/app/models/scheduled_report.py` - Database model
- ✅ `backend/app/services/reporting/report_service.py` - Report generation service
- ✅ `backend/app/services/reporting/scheduled_report_service.py` - Scheduled reports service
- ✅ `backend/app/api/v1/endpoints/reporting.py` - API endpoints
- ✅ `backend/app/api/v1/api.py` - Router registration

### Frontend:
- ✅ `frontend-nextjs/src/lib/api-config.ts` - API endpoints config
- ✅ `frontend-nextjs/src/app/super-admin/page.tsx` - Main dashboard with reports tab

### Completed:
- ✅ Database migration file (`backend/sql/create_scheduled_reports_table.sql`)
- ✅ Background scheduler service (`backend/app/services/reporting/report_scheduler.py`)
- ✅ Component refactoring (extracted to `frontend-nextjs/src/components/dashboard/`)
- ✅ Hook extraction (`frontend-nextjs/src/hooks/useScheduledReports.ts`, `useCustomReport.ts`)
- ✅ Backend endpoint refactoring (reduced verbosity using `from_orm` helper)

---

## Notes:
- All core functionality is implemented and working
- Code is functional but needs refactoring for maintainability
- MVC pattern should be enforced more strictly
- Consider using a state management library (Zustand/Redux) if complexity grows
