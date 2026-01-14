# Test Coverage Improvement Plan
**Date**: 2026-01-14  
**Current Coverage**: <5%  
**Target Coverage**: 70%+  
**Priority**: High

---

## Executive Summary

### Current State
- **Test Files**: 4 unit test files
- **Coverage**: <5% (critical gap)
- **Test Infrastructure**: ✅ pytest configured
- **Test Database**: ✅ Configured in conftest.py

### Target State
- **Unit Tests**: 70%+ coverage for services
- **Integration Tests**: All critical API endpoints
- **E2E Tests**: Critical user workflows
- **Test Infrastructure**: Enhanced fixtures and mocks

---

## 1. Test Coverage Strategy

### 1.1 Priority Levels

#### **P0 - Critical Services** (Must Test First)
1. **Authentication & Authorization** (`app/services/auth.py`)
   - User login/logout
   - Password reset
   - Session management
   - Token validation
   - **Target**: 80% coverage

2. **Execution Engine** (`app/services/execution/`)
   - Session creation
   - Step execution
   - Approval workflow
   - Rollback logic
   - **Target**: 75% coverage

3. **Runbook Generation** (`app/services/runbook/generation/`)
   - YAML generation pipeline
   - Validation pipeline
   - Quality validation
   - **Target**: 70% coverage

4. **Ticket Analysis** (`app/services/ticket_analysis_service.py`)
   - False positive detection
   - Ticket classification
   - **Target**: 70% coverage

#### **P1 - High Priority Services** (Test Next)
1. **Controllers** (`app/controllers/`)
   - ExecutionController
   - TicketController
   - RunbookController
   - **Target**: 70% coverage

2. **API Endpoints** (`app/api/v1/endpoints/`)
   - Authentication endpoints
   - Execution endpoints
   - Runbook endpoints
   - Ticket endpoints
   - **Target**: 60% coverage

3. **WebSocket Manager** (`app/services/execution/websocket_manager.py`)
   - Connection management
   - Notification system
   - **Target**: 75% coverage

#### **P2 - Medium Priority** (Test After P0/P1)
1. **Utility Services**
   - Command validation
   - YAML processing
   - Input extraction
   - **Target**: 65% coverage

2. **Integration Services**
   - Ticketing integrations
   - Monitoring connectors
   - Cloud providers
   - **Target**: 60% coverage

---

## 2. Test Implementation Plan

### Phase 1: Foundation (Week 1)
**Goal**: Set up test infrastructure and test critical auth services

#### Tasks:
1. ✅ Enhance `conftest.py` with additional fixtures
2. ✅ Create test utilities module
3. ✅ Test `auth.py` service (login, logout, password reset)
4. ✅ Test `super_admin_auth.py` service
5. ✅ Test session management

**Expected Coverage**: 15-20%

### Phase 2: Core Services (Week 2)
**Goal**: Test execution engine and runbook generation

#### Tasks:
1. ✅ Test `ExecutionEngine` class
2. ✅ Test `ExecutionController` class (expand existing)
3. ✅ Test `RunbookGeneratorService` class
4. ✅ Test validation pipelines
5. ✅ Test YAML generation pipeline

**Expected Coverage**: 40-50%

### Phase 3: API Endpoints (Week 3)
**Goal**: Test critical API endpoints

#### Tasks:
1. ✅ Test authentication endpoints
2. ✅ Test execution endpoints
3. ✅ Test runbook endpoints
4. ✅ Test ticket endpoints
5. ✅ Test WebSocket endpoints (mocked)

**Expected Coverage**: 60-65%

### Phase 4: Integration & E2E (Week 4)
**Goal**: Integration tests and end-to-end workflows

#### Tasks:
1. ✅ Test complete execution workflow
2. ✅ Test runbook generation workflow
3. ✅ Test ticket analysis workflow
4. ✅ Test multi-tenant isolation
5. ✅ Test error handling and edge cases

**Expected Coverage**: 70%+

---

## 3. Test Structure

### 3.1 Directory Structure
```
backend/tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── services/
│   │   ├── test_auth.py
│   │   ├── test_execution_engine.py
│   │   ├── test_runbook_generator.py
│   │   ├── test_ticket_analysis.py
│   │   └── test_websocket_manager.py
│   ├── controllers/
│   │   ├── test_execution_controller.py (existing)
│   │   ├── test_ticket_controller.py
│   │   └── test_runbook_controller.py
│   ├── utils/
│   │   ├── test_command_validator.py (existing)
│   │   └── test_yaml_processor.py
│   └── models/
│       └── test_models.py
├── integration/             # Integration tests
│   ├── test_auth_endpoints.py
│   ├── test_execution_endpoints.py
│   ├── test_runbook_endpoints.py
│   └── test_ticket_endpoints.py
└── e2e/                     # End-to-end tests
    ├── test_execution_workflow.py
    ├── test_runbook_generation_workflow.py
    └── test_multi_tenant_isolation.py
```

### 3.2 Test Categories

#### Unit Tests
- **Scope**: Single function/class in isolation
- **Tools**: pytest, unittest.mock
- **Speed**: Fast (<1s per test)
- **Coverage Target**: 70%+

#### Integration Tests
- **Scope**: Multiple components working together
- **Tools**: pytest, TestClient, test database
- **Speed**: Medium (1-5s per test)
- **Coverage Target**: 60%+

#### E2E Tests
- **Scope**: Complete user workflows
- **Tools**: pytest, TestClient, mocked external services
- **Speed**: Slow (5-30s per test)
- **Coverage Target**: Critical paths only

---

## 4. Test Implementation Guidelines

### 4.1 Test Naming Convention
```python
# Unit tests
def test_function_name_with_condition_returns_expected():
    """Test description"""
    pass

# Integration tests
@pytest.mark.integration
def test_endpoint_name_with_valid_input_returns_success():
    """Test description"""
    pass
```

### 4.2 Test Structure (AAA Pattern)
```python
def test_example():
    # Arrange - Set up test data
    user = create_test_user()
    
    # Act - Execute the function
    result = service.do_something(user)
    
    # Assert - Verify results
    assert result.status == "success"
    assert result.user_id == user.id
```

### 4.3 Mocking Guidelines
- **Mock external services**: LLM, databases, APIs
- **Use real database**: For integration tests (test DB)
- **Mock time-dependent**: Use freezegun for datetime
- **Mock file I/O**: Use tempfile or mock

### 4.4 Test Data Management
- **Fixtures**: Use pytest fixtures for common data
- **Factories**: Create test data factories for complex objects
- **Cleanup**: Always clean up test data in teardown

---

## 5. Critical Services Test Plan

### 5.1 Authentication Service Tests

#### Test Cases:
1. ✅ `test_login_with_valid_credentials_returns_token`
2. ✅ `test_login_with_invalid_credentials_raises_error`
3. ✅ `test_login_with_locked_account_raises_error`
4. ✅ `test_password_reset_creates_token`
5. ✅ `test_password_reset_with_invalid_token_raises_error`
6. ✅ `test_get_current_user_with_valid_token_returns_user`
7. ✅ `test_get_current_user_with_invalid_token_raises_401`
8. ✅ `test_get_current_user_with_revoked_session_raises_401`
9. ✅ `test_account_lockout_after_max_attempts`
10. ✅ `test_account_unlock_after_timeout`

**File**: `backend/tests/unit/services/test_auth.py`

### 5.2 Execution Engine Tests

#### Test Cases:
1. ✅ `test_create_execution_session_with_valid_runbook`
2. ✅ `test_create_execution_session_with_invalid_runbook_raises_error`
3. ✅ `test_start_execution_creates_steps`
4. ✅ `test_approve_step_continues_execution`
5. ✅ `test_reject_step_stops_execution`
6. ✅ `test_execute_step_with_approval_required_waits`
7. ✅ `test_execute_step_without_approval_executes_immediately`
8. ✅ `test_rollback_on_step_failure`
9. ✅ `test_resolution_verification_on_completion`
10. ✅ `test_self_healing_on_failure`

**File**: `backend/tests/unit/services/test_execution_engine.py`

### 5.3 Runbook Generator Tests

#### Test Cases:
1. ✅ `test_generate_runbook_with_valid_description`
2. ✅ `test_generate_agent_runbook_creates_yaml`
3. ✅ `test_yaml_generation_pipeline_extracts_yaml`
4. ✅ `test_yaml_generation_pipeline_cleans_yaml`
5. ✅ `test_validation_pipeline_validates_structure`
6. ✅ `test_validation_pipeline_validates_commands`
7. ✅ `test_validation_pipeline_critiques_runbook`
8. ✅ `test_generate_runbook_with_missing_remediation_fails`
9. ✅ `test_generate_runbook_with_invalid_yaml_attempts_autofix`
10. ✅ `test_generate_runbook_stores_citations`

**File**: `backend/tests/unit/services/test_runbook_generator.py`

### 5.4 WebSocket Manager Tests

#### Test Cases:
1. ✅ `test_add_connection_adds_to_active_connections`
2. ✅ `test_add_connection_respects_max_connections_limit`
3. ✅ `test_cleanup_connection_removes_connection`
4. ✅ `test_update_activity_updates_timestamp`
5. ✅ `test_notify_approval_needed_sends_message`
6. ✅ `test_notify_approval_needed_cleans_dead_connections`
7. ✅ `test_send_to_session_sends_to_all_clients`
8. ✅ `test_cleanup_idle_connections_closes_idle_connections`
9. ✅ `test_cleanup_idle_connections_removes_dead_connections`
10. ✅ `test_connection_limit_enforced_per_session`

**File**: `backend/tests/unit/services/test_websocket_manager.py`

### 5.5 API Endpoint Tests

#### Authentication Endpoints:
1. ✅ `test_login_endpoint_with_valid_credentials`
2. ✅ `test_login_endpoint_with_invalid_credentials`
3. ✅ `test_logout_endpoint_revokes_session`
4. ✅ `test_forgot_password_endpoint_creates_token`
5. ✅ `test_reset_password_endpoint_updates_password`

#### Execution Endpoints:
1. ✅ `test_start_execution_endpoint_creates_session`
2. ✅ `test_approve_step_endpoint_approves_step`
3. ✅ `test_get_execution_status_endpoint_returns_status`
4. ✅ `test_list_execution_sessions_endpoint_returns_sessions`
5. ✅ `test_cancel_execution_endpoint_cancels_session`

**File**: `backend/tests/integration/test_execution_endpoints.py`

---

## 6. Test Utilities

### 6.1 Test Fixtures (conftest.py)
- ✅ `db` - Database session
- ✅ `client` - FastAPI test client
- ✅ `mock_user` - Mock user object
- ✅ `mock_tenant` - Mock tenant object
- ✅ `mock_runbook` - Mock runbook object
- ✅ `mock_execution_session` - Mock execution session
- ✅ `mock_llm_service` - Mock LLM service
- ✅ `mock_vector_service` - Mock vector store service

### 6.2 Test Factories
- `UserFactory` - Create test users
- `RunbookFactory` - Create test runbooks
- `ExecutionSessionFactory` - Create test sessions
- `TicketFactory` - Create test tickets

### 6.3 Test Helpers
- `create_test_user()` - Helper to create user
- `create_test_runbook()` - Helper to create runbook
- `create_test_session()` - Helper to create session
- `assert_runbook_valid()` - Helper to validate runbook

---

## 7. Coverage Goals by Module

### Services (Target: 70%+)
- `app/services/auth.py`: 80%
- `app/services/execution/`: 75%
- `app/services/runbook/generation/`: 70%
- `app/services/ticket_analysis_service.py`: 70%
- `app/services/execution/websocket_manager.py`: 75%

### Controllers (Target: 70%+)
- `app/controllers/execution_controller.py`: 75%
- `app/controllers/ticket_controller.py`: 70%
- `app/controllers/runbook_controller.py`: 70%

### API Endpoints (Target: 60%+)
- `app/api/v1/endpoints/auth.py`: 70%
- `app/api/v1/endpoints/agent_execution.py`: 65%
- `app/api/v1/endpoints/runbooks.py`: 60%

### Utilities (Target: 65%+)
- `app/services/runbook/generation/yaml_processor.py`: 70%
- `app/services/infrastructure/command_validator.py`: 65%

---

## 8. Implementation Checklist

### Week 1: Foundation
- [ ] Enhance conftest.py with additional fixtures
- [ ] Create test utilities module
- [ ] Implement auth service tests (10 tests)
- [ ] Implement super admin auth tests (5 tests)
- [ ] Implement session management tests (5 tests)

### Week 2: Core Services
- [ ] Implement execution engine tests (10 tests)
- [ ] Expand execution controller tests (5 more tests)
- [ ] Implement runbook generator tests (10 tests)
- [ ] Implement validation pipeline tests (8 tests)
- [ ] Implement YAML generation pipeline tests (6 tests)

### Week 3: API Endpoints
- [ ] Implement auth endpoint tests (5 tests)
- [ ] Implement execution endpoint tests (8 tests)
- [ ] Implement runbook endpoint tests (6 tests)
- [ ] Implement ticket endpoint tests (5 tests)
- [ ] Implement WebSocket endpoint tests (5 tests, mocked)

### Week 4: Integration & E2E
- [ ] Implement execution workflow E2E test
- [ ] Implement runbook generation workflow E2E test
- [ ] Implement ticket analysis workflow E2E test
- [ ] Implement multi-tenant isolation tests (3 tests)
- [ ] Implement error handling tests (5 tests)

---

## 9. Running Tests

### Run All Tests
```bash
cd backend
pytest tests/ -v --cov=app --cov-report=html
```

### Run Unit Tests Only
```bash
pytest tests/unit/ -v -m unit
```

### Run Integration Tests Only
```bash
pytest tests/integration/ -v -m integration
```

### Run Specific Test File
```bash
pytest tests/unit/services/test_auth.py -v
```

### Run with Coverage Report
```bash
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
```

### Check Coverage Threshold
```bash
pytest tests/ -v --cov=app --cov-fail-under=70
```

---

## 10. Success Metrics

### Coverage Metrics
- **Overall Coverage**: 70%+
- **Critical Services**: 75%+
- **API Endpoints**: 60%+
- **Utilities**: 65%+

### Quality Metrics
- **Test Execution Time**: <5 minutes for full suite
- **Test Reliability**: 99%+ pass rate
- **Test Maintainability**: Clear, documented tests

### Process Metrics
- **Tests per PR**: New code must include tests
- **Coverage Gate**: PRs must maintain 70%+ coverage
- **Test Review**: All tests reviewed in PR process

---

## 11. Next Steps

1. **Start with Foundation** (Week 1)
   - Enhance test infrastructure
   - Test authentication services
   - Establish testing patterns

2. **Move to Core Services** (Week 2)
   - Test execution engine
   - Test runbook generation
   - Test validation pipelines

3. **Add API Tests** (Week 3)
   - Test critical endpoints
   - Test error handling
   - Test authentication flows

4. **Complete with Integration** (Week 4)
   - E2E workflows
   - Multi-tenant isolation
   - Error scenarios

---

**Status**: Ready to implement  
**Next Action**: Start with Phase 1 - Foundation tests

