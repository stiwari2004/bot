# Combined Implementation Plan
## User Management, Change Ticket Integration & Self-Healing

**Version:** 1.0  
**Date:** 2025-01-07  
**Status:** Planning Phase

---

## Executive Summary

This document outlines the implementation plan for three major feature areas:

1. **User Management Enhancements** - Security, profile management, and user experience improvements
2. **Change Ticket Integration** - Suppress tickets during change windows to reduce false positives
3. **Self-Healing System** - Post-execution analysis and dynamic remediation (cost-optimized)

**Total Timeline:** 8 weeks  
**Priority Order:** Security → Change Management → Self-Healing → User Experience

---

## Table of Contents

1. [Priority 1: User Management - Critical Security](#priority-1-user-management---critical-security)
2. [Priority 2: Change Ticket Integration](#priority-2-change-ticket-integration)
3. [Priority 3: Self-Healing System](#priority-3-self-healing-system)
4. [Priority 4: User Management - Enhancements](#priority-4-user-management---enhancements)
5. [Implementation Timeline](#implementation-timeline)
6. [Database Migrations](#database-migrations)
7. [API Endpoints](#api-endpoints)
8. [Success Metrics](#success-metrics)

---

## Priority 1: User Management - Critical Security

### 1.1 Password Reset / Forgot Password

**Priority:** CRITICAL  
**Effort:** Medium (3-5 days)  
**Files to Modify:**
- `backend/app/models/user.py` - Add password reset fields
- `backend/app/api/v1/endpoints/auth.py` - Add reset endpoints
- `backend/app/services/auth.py` - Add reset token generation
- `backend/app/services/email_service.py` - NEW - Email sending service
- `frontend-nextjs/src/app/login/page.tsx` - Add forgot password link
- `frontend-nextjs/src/app/reset-password/page.tsx` - NEW - Reset password page

**Database Migration:**
```sql
-- File: backend/sql/add_password_reset_fields.sql
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(255),
ADD COLUMN IF NOT EXISTS password_reset_expires TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(password_reset_token);
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(email_verification_token);
```

**API Endpoints:**
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password with token
- `POST /api/v1/auth/verify-email` - Verify email address

**Implementation Details:**
- Generate secure random token (32 chars, URL-safe)
- Token expires in 1 hour
- Rate limit: 5 requests/hour per email
- Email template with reset link
- Frontend: Forgot password form → Email sent confirmation → Reset form

---

### 1.2 Enhanced Password Validation

**Priority:** CRITICAL  
**Effort:** Low (1-2 days)  
**Files to Modify:**
- `backend/app/services/auth.py` - Add password validation logic
- `backend/app/api/v1/endpoints/auth.py` - Update change-password endpoint
- `backend/app/models/user.py` - Add password history fields

**Database Migration:**
```sql
-- File: backend/sql/add_password_history.sql
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_history JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS password_expires_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN users.password_history IS 'Array of last 5 password hashes to prevent reuse';
COMMENT ON COLUMN users.password_expires_at IS 'Password expiration date (90 days default)';
```

**Password Requirements:**
- Minimum 12 characters
- At least 1 uppercase, 1 lowercase, 1 number, 1 special character
- Cannot reuse last 5 passwords
- Expires after 90 days (configurable per tenant)

**Implementation:**
- Create `PasswordValidator` service
- Update `change_password` endpoint
- Store password hashes in `password_history` (max 5)
- Check expiration on login

---

### 1.3 Account Lockout Protection

**Priority:** CRITICAL  
**Effort:** Medium (2-3 days)  
**Files to Modify:**
- `backend/app/models/user.py` - Add lockout fields
- `backend/app/api/v1/endpoints/auth.py` - Update login endpoint
- `backend/app/api/v1/endpoints/super_admin.py` - Add unlock endpoint

**Database Migration:**
```sql
-- File: backend/sql/add_account_lockout_fields.sql
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS last_failed_login_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_users_locked ON users(locked_until) WHERE locked_until IS NOT NULL;
```

**Lockout Rules:**
- Lock after 5 failed attempts
- Auto-unlock after 30 minutes
- Reset attempts on successful login
- Admin can manually unlock

**Implementation:**
- Track failed attempts in login endpoint
- Check `locked_until` before authentication
- Admin unlock endpoint: `POST /api/v1/super-admin/users/{user_id}/unlock`

---

## Priority 2: Change Ticket Integration

### 2.1 Change Ticket Model & Database

**Priority:** HIGH  
**Effort:** Medium (3-4 days)  
**Files to Create:**
- `backend/app/models/change_ticket.py` - NEW - Change ticket model
- `backend/sql/create_change_tickets_table.sql` - NEW - Database schema

**Database Schema:**
```sql
-- File: backend/sql/create_change_tickets_table.sql
CREATE TABLE IF NOT EXISTS change_tickets (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    change_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'scheduled',
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    affected_services TEXT[],
    affected_environments TEXT[],
    suppression_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(tenant_id, external_id, source)
);

CREATE INDEX IF NOT EXISTS idx_change_tickets_tenant ON change_tickets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_change_tickets_time ON change_tickets(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_change_tickets_status ON change_tickets(status);
CREATE INDEX IF NOT EXISTS idx_change_tickets_active ON change_tickets(start_time, end_time) 
    WHERE status IN ('scheduled', 'in_progress');
```

**Model Implementation:**
- `ChangeTicket` class with relationships
- Methods: `is_active()`, `affects_service()`, `affects_environment()`

---

### 2.2 Change Ticket Sync Service

**Priority:** HIGH  
**Effort:** Medium (4-5 days)  
**Files to Create/Modify:**
- `backend/app/services/change_ticket_sync_service.py` - NEW - Sync service
- `backend/app/services/ticketing_poller.py` - Add change ticket polling
- `backend/app/services/ticketing_connectors/servicenow.py` - Add change ticket fetching
- `backend/app/services/ticketing_connectors/manageengine.py` - Add change ticket fetching

**Implementation:**
- Poll ServiceNow/ManageEngine for change tickets
- Sync every 15 minutes
- Map change ticket fields:
  - `number` → `external_id`
  - `start_date` → `start_time`
  - `end_date` → `end_time`
  - `type` → `change_type`
  - `state` → `status`
- Update status transitions: `scheduled` → `in_progress` → `completed`

**ServiceNow Change Ticket Query:**
```python
# Query: state IN (1,2,3) AND start_date >= today
# State: 1=scheduled, 2=in_progress, 3=completed
```

---

### 2.3 Ticket Suppression During Change Windows

**Priority:** HIGH  
**Effort:** Medium (3-4 days)  
**Files to Create/Modify:**
- `backend/app/services/change_window_service.py` - NEW - Suppression logic
- `backend/app/controllers/ticket_controller.py` - Add suppression check
- `backend/app/models/ticket.py` - Add suppression fields

**Database Migration:**
```sql
-- File: backend/sql/add_ticket_suppression_fields.sql
ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS suppressed_by_change_id INTEGER REFERENCES change_tickets(id),
ADD COLUMN IF NOT EXISTS suppressed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS unsuppressed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS suppression_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_tickets_suppressed ON tickets(suppressed_by_change_id) 
    WHERE suppressed_by_change_id IS NOT NULL;
```

**Suppression Logic:**
```python
async def should_suppress_ticket(
    ticket: Ticket,
    db: Session
) -> Tuple[bool, Optional[ChangeTicket]]:
    """
    Check if ticket should be suppressed due to active change window
    
    Criteria:
    1. Change window is active (start_time <= now <= end_time)
    2. Change status is 'scheduled' or 'in_progress'
    3. Ticket service matches change affected_services (or any if empty)
    4. Ticket environment matches change affected_environments (or any if empty)
    5. suppression_enabled = True
    
    Returns:
        (should_suppress, change_ticket)
    """
```

**Integration Points:**
- Check suppression when ticket is received (webhook/polling)
- Auto-unsuppress when change window ends
- Update ticket status to 'suppressed' (new status)

---

### 2.4 Change Window UI & Management

**Priority:** MEDIUM  
**Effort:** Medium (3-4 days)  
**Files to Create:**
- `backend/app/api/v1/endpoints/change_tickets.py` - NEW - API endpoints
- `frontend-nextjs/src/features/change-tickets/` - NEW - Frontend components

**API Endpoints:**
- `GET /api/v1/change-tickets` - List change tickets
- `GET /api/v1/change-tickets/{id}` - Get change ticket details
- `GET /api/v1/change-tickets/active` - Get active change windows
- `GET /api/v1/tickets/suppressed` - List suppressed tickets
- `POST /api/v1/tickets/{id}/unsuppress` - Manually unsuppress ticket

**Frontend Components:**
- Change tickets list page
- Active change windows dashboard
- Suppressed tickets view
- Change ticket details modal

---

## Priority 3: Self-Healing System

### 3.1 Post-Execution Output Analysis Service

**Priority:** HIGH  
**Effort:** Medium (4-5 days)  
**Files to Create:**
- `backend/app/services/self_healing/post_execution_analysis_service.py` - NEW - Analysis service

**Key Constraint:** Single LLM call per failed runbook (not per step)

**Implementation:**
```python
class PostExecutionAnalysisService:
    async def analyze_execution_results(
        self,
        session: ExecutionSession,
        db: Session
    ) -> Dict[str, Any]:
        """
        Analyze complete execution after runbook finishes
        
        Only called if:
        - Runbook execution completed but issue not resolved
        - OR execution failed
        - AND time remaining > threshold
        
        Returns:
            {
                "issue_resolved": bool,
                "needs_additional_steps": bool,
                "suggested_actions": List[str],
                "confidence": float,
                "reasoning": str,
                "failed_steps_analysis": Dict[str, Any],
                "output_patterns": Dict[str, Any]
            }
        """
        # Get all execution steps
        all_steps = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session.id
        ).order_by(ExecutionStep.step_number).all()
        
        # Build comprehensive context
        execution_context = {
            "session_id": session.id,
            "runbook_id": session.runbook_id,
            "ticket_id": session.ticket_id,
            "total_steps": len(all_steps),
            "successful_steps": len([s for s in all_steps if s.success]),
            "failed_steps": len([s for s in all_steps if not s.success]),
            "step_outputs": [
                {
                    "step_number": s.step_number,
                    "step_type": s.step_type,
                    "command": s.command,
                    "output": s.output[:1000] if s.output else None,  # Limit output size
                    "error": s.error_message,
                    "success": s.success,
                    "exit_code": s.exit_code if hasattr(s, 'exit_code') else None
                }
                for s in all_steps
            ],
            "ticket_context": await self._get_ticket_context(session, db),
            "resolution_verification": await self._get_resolution_verification(session, db)
        }
        
        # Single LLM call with full context
        return await self._llm_analyze_execution(execution_context)
```

**LLM Prompt Structure:**
- System prompt: Expert IT troubleshooting analyst
- User prompt: Complete execution context + ticket details
- Response: JSON with analysis and suggested remediation steps

---

### 3.2 Time Remaining Check

**Priority:** HIGH  
**Effort:** Low (1-2 days)  
**Files to Create:**
- `backend/app/services/self_healing/time_remaining_service.py` - NEW - Time check service

**Implementation:**
```python
class TimeRemainingService:
    def has_sufficient_time_for_self_healing(
        self,
        session: ExecutionSession,
        estimated_additional_time_minutes: int = 15
    ) -> bool:
        """
        Check if there's enough time remaining for post-execution self-healing
        
        Args:
            session: Execution session (must be completed)
            estimated_additional_time_minutes: Estimated time for remediation steps
            
        Returns:
            True if sufficient time remains
        """
        if session.status != "completed":
            return False
        
        if not session.started_at:
            return False
        
        # Calculate elapsed time
        elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds() / 60
        
        # Get session timeout (default 60 minutes, or from runbook)
        max_duration = getattr(session, 'max_duration_minutes', None) or 60
        
        # Check if we have enough time left (with buffer)
        time_remaining = max_duration - elapsed
        buffer_minutes = 5  # Safety buffer
        
        return time_remaining >= (estimated_additional_time_minutes + buffer_minutes)
```

**Integration:**
- Check before calling `PostExecutionAnalysisService`
- Skip self-healing if insufficient time

---

### 3.3 Dynamic Remediation Step Generator

**Priority:** MEDIUM  
**Effort:** High (5-7 days)  
**Files to Create:**
- `backend/app/services/self_healing/dynamic_remediation_generator.py` - NEW - Step generator

**Implementation:**
```python
class DynamicRemediationGenerator:
    async def generate_remediation_steps(
        self,
        analysis_result: Dict[str, Any],
        original_session: ExecutionSession,
        db: Session
    ) -> ExecutionSession:
        """
        Generate and create execution session for remediation steps
        
        Creates a new execution session linked to original
        
        Returns:
            New ExecutionSession for remediation
        """
        # Generate step definitions from analysis
        step_definitions = await self._generate_step_definitions(
            analysis_result,
            original_session
        )
        
        # Validate step definitions
        validated_steps = await self._validate_steps(step_definitions)
        
        # Create new execution session for remediation
        remediation_session = ExecutionSession(
            runbook_id=original_session.runbook_id,
            tenant_id=original_session.tenant_id,
            ticket_id=original_session.ticket_id,
            status="pending",
            parent_session_id=original_session.id,  # Track parent
            session_type="remediation",  # Mark as self-healing
            issue_description=f"Self-healing remediation for session {original_session.id}"
        )
        
        db.add(remediation_session)
        db.flush()
        
        # Create steps from definitions
        for idx, step_def in enumerate(validated_steps, start=1):
            step = ExecutionStep(
                session_id=remediation_session.id,
                step_number=idx,
                command=step_def["command"],
                step_type="remediation",
                notes=step_def.get("description", "Dynamic remediation step"),
                requires_approval=step_def.get("requires_approval", False),
                command_payload={
                    "generated_by": "self_healing",
                    "analysis_confidence": analysis_result.get("confidence", 0.0),
                    "original_step_failed": step_def.get("original_step_number")
                }
            )
            db.add(step)
        
        remediation_session.total_steps = len(validated_steps)
        db.commit()
        
        return remediation_session
```

**Step Generation Logic:**
- Parse `suggested_actions` from analysis
- Convert to executable commands
- Validate commands before creating steps
- Limit to 5 remediation steps per session

---

### 3.4 Self-Healing Integration

**Priority:** HIGH  
**Effort:** Medium (3-4 days)  
**Files to Modify:**
- `backend/app/services/resolution_verification_service.py` - Add self-healing trigger
- `backend/app/models/execution_session.py` - Add parent_session_id, session_type fields
- `backend/app/services/execution/execution_engine.py` - Handle remediation sessions

**Database Migration:**
```sql
-- File: backend/sql/add_self_healing_fields.sql
ALTER TABLE execution_sessions
ADD COLUMN IF NOT EXISTS parent_session_id INTEGER REFERENCES execution_sessions(id),
ADD COLUMN IF NOT EXISTS session_type VARCHAR(50) DEFAULT 'standard',
ADD COLUMN IF NOT EXISTS max_duration_minutes INTEGER DEFAULT 60;

CREATE INDEX IF NOT EXISTS idx_execution_sessions_parent ON execution_sessions(parent_session_id);
CREATE INDEX IF NOT EXISTS idx_execution_sessions_type ON execution_sessions(session_type);
```

**Integration Flow:**
```python
# In ResolutionVerificationService.verify_resolution()

# After verification determines issue not resolved:
if not resolved and confidence < 0.7:
    # Check time remaining
    if time_remaining_service.has_sufficient_time_for_self_healing(session, estimated_time=15):
        # Single LLM call for complete analysis
        analysis = await post_execution_analysis_service.analyze_execution_results(
            session, db
        )
        
        if analysis["needs_additional_steps"] and analysis["confidence"] > 0.6:
            # Generate and execute remediation
            remediation_session = await dynamic_remediation_generator.generate_remediation_steps(
                analysis, session, db
            )
            
            # Start remediation execution
            await execution_engine.start_execution(db, remediation_session.id)
            
            logger.info(
                f"Self-healing triggered for session {session.id}: "
                f"Created remediation session {remediation_session.id} "
                f"(confidence: {analysis['confidence']:.2f})"
            )
            
            return {
                "resolved": False,
                "confidence": confidence,
                "reasoning": reasoning,
                "self_healing_attempted": True,
                "remediation_session_id": remediation_session.id
            }
```

**Constraints:**
- Only one self-healing attempt per original session
- Minimum confidence threshold: 0.6
- Maximum remediation steps: 5
- Time remaining must be > 15 minutes

---

## Priority 4: User Management - Enhancements

### 4.1 User Profile Management

**Priority:** MEDIUM  
**Effort:** Low (2-3 days)  
**Files to Modify:**
- `backend/app/models/user.py` - Add profile fields
- `backend/app/api/v1/endpoints/auth.py` - Add profile endpoints
- `frontend-nextjs/src/app/profile/page.tsx` - NEW - Profile page

**Database Migration:**
```sql
-- File: backend/sql/add_user_profile_fields.sql
ALTER TABLE users
ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC',
ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en',
ADD COLUMN IF NOT EXISTS theme VARCHAR(20) DEFAULT 'light';
```

**API Endpoints:**
- `GET /api/v1/auth/profile` - Get user profile
- `PUT /api/v1/auth/profile` - Update user profile

---

### 4.2 User Preferences

**Priority:** MEDIUM  
**Effort:** Medium (3-4 days)  
**Files to Modify:**
- `backend/app/models/user.py` - Add preferences JSONB field
- `backend/app/api/v1/endpoints/auth.py` - Add preferences endpoints

**Database Migration:**
```sql
-- File: backend/sql/add_user_preferences.sql
ALTER TABLE users
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}';

COMMENT ON COLUMN users.preferences IS 'User preferences: notifications, dashboard layout, etc.';
```

**Preference Structure:**
```json
{
  "notifications": {
    "email": true,
    "slack": false,
    "execution_complete": true,
    "execution_failed": true
  },
  "dashboard": {
    "default_view": "tickets",
    "items_per_page": 25
  }
}
```

---

### 4.3 Login History & Activity Log

**Priority:** MEDIUM  
**Effort:** Medium (3-4 days)  
**Files to Create:**
- `backend/app/models/user_login_history.py` - NEW - Login history model
- `backend/app/models/user_activity_log.py` - NEW - Activity log model
- `backend/app/api/v1/endpoints/user_activity.py` - NEW - Activity endpoints

**Database Schema:**
```sql
-- File: backend/sql/create_user_login_history.sql
CREATE TABLE IF NOT EXISTS user_login_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    login_success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100),
    login_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_history_user ON user_login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_at ON user_login_history(login_at);
CREATE INDEX IF NOT EXISTS idx_login_history_success ON user_login_history(login_success);

-- File: backend/sql/create_user_activity_log.sql
CREATE TABLE IF NOT EXISTS user_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_log_user ON user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_action ON user_activity_log(action);
CREATE INDEX IF NOT EXISTS idx_activity_log_created ON user_activity_log(created_at);
```

---

### 4.4 Session Management

**Priority:** LOW  
**Effort:** Medium (3-4 days)  
**Files to Create:**
- `backend/app/models/user_session.py` - NEW - Active session tracking
- `backend/app/api/v1/endpoints/auth.py` - Add session management endpoints

**Database Schema:**
```sql
-- File: backend/sql/create_user_sessions.sql
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(user_id, revoked, expires_at) 
    WHERE revoked = FALSE AND expires_at > NOW();
```

**API Endpoints:**
- `GET /api/v1/auth/sessions` - List active sessions
- `DELETE /api/v1/auth/sessions/{session_id}` - Revoke specific session
- `POST /api/v1/auth/logout-all` - Revoke all sessions

---

## Implementation Timeline

### Phase 1: Weeks 1-2 (Critical Security)
**Goal:** Secure user authentication and password management

**Week 1:**
- Day 1-2: Password reset/forgot password (backend)
- Day 3: Password reset (frontend)
- Day 4-5: Enhanced password validation

**Week 2:**
- Day 1-2: Account lockout protection
- Day 3: Testing and bug fixes
- Day 4-5: Documentation

**Deliverables:**
- Password reset functionality
- Enhanced password validation
- Account lockout protection

---

### Phase 2: Weeks 2-3 (Change Management)
**Goal:** Integrate change tickets and suppress tickets during change windows

**Week 2 (overlap with Phase 1):**
- Day 3-5: Change ticket model & database

**Week 3:**
- Day 1-2: Change ticket sync service
- Day 3-4: Ticket suppression logic
- Day 5: Change window UI

**Deliverables:**
- Change ticket integration
- Automatic ticket suppression
- Change window management UI

---

### Phase 3: Weeks 3-5 (Self-Healing)
**Goal:** Post-execution analysis and dynamic remediation

**Week 3 (overlap with Phase 2):**
- Day 4-5: Post-execution analysis service (planning)

**Week 4:**
- Day 1-2: Post-execution analysis service (implementation)
- Day 3: Time remaining check
- Day 4-5: Dynamic remediation generator

**Week 5:**
- Day 1-2: Self-healing integration
- Day 3-4: Testing and refinement
- Day 5: Cost monitoring and optimization

**Deliverables:**
- Post-execution analysis
- Dynamic step generation
- Self-healing integration

---

### Phase 4: Weeks 4-6 (User Management Enhancements)
**Goal:** User profile, preferences, and activity tracking

**Week 4 (overlap with Phase 3):**
- Day 4-5: User profile management

**Week 5 (overlap with Phase 3):**
- Day 4-5: User preferences

**Week 6:**
- Day 1-2: Login history & activity log
- Day 3-4: Session management
- Day 5: Testing and documentation

**Deliverables:**
- User profile management
- User preferences
- Activity tracking
- Session management

---

## Database Migrations Summary

All migrations should be in `backend/sql/` directory:

1. `add_password_reset_fields.sql` - Password reset tokens
2. `add_password_history.sql` - Password history and expiration
3. `add_account_lockout_fields.sql` - Account lockout tracking
4. `create_change_tickets_table.sql` - Change ticket model
5. `add_ticket_suppression_fields.sql` - Ticket suppression fields
6. `add_self_healing_fields.sql` - Self-healing session tracking
7. `add_user_profile_fields.sql` - User profile fields
8. `add_user_preferences.sql` - User preferences JSONB
9. `create_user_login_history.sql` - Login history table
10. `create_user_activity_log.sql` - Activity log table
11. `create_user_sessions.sql` - Active session tracking

---

## API Endpoints Summary

### Authentication & User Management
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password with token
- `POST /api/v1/auth/verify-email` - Verify email address
- `GET /api/v1/auth/profile` - Get user profile
- `PUT /api/v1/auth/profile` - Update user profile
- `GET /api/v1/auth/sessions` - List active sessions
- `DELETE /api/v1/auth/sessions/{session_id}` - Revoke session
- `POST /api/v1/auth/logout-all` - Revoke all sessions

### Change Tickets
- `GET /api/v1/change-tickets` - List change tickets
- `GET /api/v1/change-tickets/{id}` - Get change ticket details
- `GET /api/v1/change-tickets/active` - Get active change windows
- `GET /api/v1/tickets/suppressed` - List suppressed tickets
- `POST /api/v1/tickets/{id}/unsuppress` - Manually unsuppress ticket

### User Activity
- `GET /api/v1/user-activity/login-history` - Get login history
- `GET /api/v1/user-activity/activity-log` - Get activity log

### Admin
- `POST /api/v1/super-admin/users/{user_id}/unlock` - Unlock user account

---

## Success Metrics

### User Management
- **Password Reset:** Success rate > 95%, completion time < 5 minutes
- **Account Security:** Lockout incidents reduced by 80%
- **User Experience:** Profile update adoption > 60%

### Change Management
- **Change Sync:** 100% of change tickets synced within 15 minutes
- **Suppression Accuracy:** > 95% accuracy in suppressing tickets during change windows
- **False Positives:** < 5% false positive suppression rate

### Self-Healing
- **Trigger Rate:** 20-30% of failed runbooks trigger self-healing
- **Success Rate:** > 60% of self-healing attempts resolve the issue
- **Cost Efficiency:** < $0.10 LLM cost per self-healing attempt
- **Time Improvement:** 25% average resolution time improvement when self-healing succeeds

---

## Risk Mitigation

### Self-Healing Risks
1. **Safety:** Validate all generated commands before execution
2. **Cost Control:** Single LLM call per failed runbook (not per step)
3. **Time Management:** Conservative time estimates to avoid timeouts
4. **Quality:** Minimum confidence threshold (0.6) before generating steps

### Change Suppression Risks
1. **False Positives:** Manual override capability for admins
2. **Sync Failures:** Retry logic and alerting for sync failures
3. **Time Zone Issues:** Store all times in UTC, convert for display

### Security Risks
1. **Password Reset:** Rate limiting and token expiration
2. **Account Lockout:** Admin override and auto-unlock
3. **Session Management:** Secure token storage and revocation

---

## Testing Strategy

### Unit Tests
- Password validation logic
- Change window suppression logic
- Time remaining calculations
- Step generation validation

### Integration Tests
- Password reset flow (end-to-end)
- Change ticket sync and suppression
- Self-healing trigger and execution
- Session management

### Performance Tests
- LLM call latency (self-healing)
- Change ticket sync performance
- Password reset email delivery

---

## Documentation Requirements

1. **API Documentation:** Update OpenAPI/Swagger docs
2. **User Guides:** Password reset, profile management
3. **Admin Guides:** Change ticket management, user unlock
4. **Developer Docs:** Self-healing architecture, change suppression logic

---

## Next Steps

1. Review and approve this plan
2. Set up project tracking (GitHub Issues/Jira)
3. Begin Phase 1 implementation
4. Weekly progress reviews and adjustments

---

**End of Plan Document**

