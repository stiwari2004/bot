# Code Cleanup Plan

**Generated:** 2025-12-02  
**Objective:** Clean codebase, enforce MVC pattern, break down long files

---

## Executive Summary

### Issues Identified
1. **MVC Violations**: Controllers directly accessing database (41 instances)
2. **Long Files**: 10+ files exceed 400 lines (largest: 1364 lines)
3. **Code Duplication**: Potential duplication in similar services
4. **Separation of Concerns**: Business logic in controllers

---

## Phase 1: MVC Pattern Violations

### Critical Issues Found

#### 1. Controllers Directly Using Database Operations

**Files with violations:**
- `backend/app/controllers/ticket_controller.py` - 9 violations
- `backend/app/controllers/alert_controller.py` - 8 violations
- `backend/app/controllers/execution_controller.py` - 8 violations
- `backend/app/controllers/runbook_controller.py` - 6 violations
- `backend/app/controllers/connector_controller.py` - 3 violations
- `backend/app/controllers/agent_worker_controller.py` - 4 violations
- `backend/app/controllers/base_controller.py` - 1 violation

**Pattern to fix:**
```python
# ❌ BAD: Direct DB access in controller
self.db.add(ticket)
self.db.commit()
self.db.refresh(ticket)
runbook = self.db.query(Runbook).filter(...).first()

# ✅ GOOD: Use repository
ticket = self.ticket_repo.create(ticket_data)
runbook = self.runbook_repo.get_by_id(runbook_id)
```

### Action Items

#### Priority 1: Ticket Controller
- [ ] Move `db.add()`, `db.commit()`, `db.refresh()` to `TicketRepository`
- [ ] Create repository methods: `create()`, `update()`, `get_by_id()`
- [ ] Remove direct `db.query()` calls

#### Priority 2: Alert Controller
- [ ] Move database operations to `AlertRepository`
- [ ] Create repository methods for all CRUD operations
- [ ] Refactor query logic to repository

#### Priority 3: Execution Controller
- [ ] Move `db.query(Runbook)` to `RunbookRepository`
- [ ] Move `db.add(RunbookUsage)` to `RunbookUsageRepository`
- [ ] Ensure all DB operations go through repositories

#### Priority 4: Runbook Controller
- [ ] Move ticket queries to `TicketRepository`
- [ ] Move runbook updates to `RunbookRepository`
- [ ] Remove direct DB commits

#### Priority 5: Connector Controller
- [ ] Move infrastructure connection operations to repository
- [ ] Remove direct DB commits

#### Priority 6: Agent Worker Controller
- [ ] Move assignment queries to repository
- [ ] Remove direct DB commits

#### Priority 7: Base Controller
- [ ] Move `validate_tenant_access()` to a service or repository helper

---

## Phase 2: Long Files Breakdown

### Files Exceeding 500 Lines (High Priority)

#### 1. `runbook_generator_core.py` - 1364 lines ⚠️ CRITICAL
**Breakdown Plan:**
- Extract LLM prompt generation → `runbook_prompt_builder.py`
- Extract YAML validation → `runbook_yaml_validator.py`
- Extract citation processing → `runbook_citation_processor.py`
- Extract metadata extraction → `runbook_metadata_extractor.py`
- Keep core orchestration logic in main file (< 400 lines)

#### 2. `step_execution_service.py` - 1297 lines ⚠️ CRITICAL
**Breakdown Plan:**
- Extract command execution → `command_executor.py`
- Extract output parsing → `output_parser.py`
- Extract error handling → `step_error_handler.py`
- Extract retry logic → `step_retry_handler.py`
- Extract validation → `step_validator.py`
- Keep orchestration in main file (< 400 lines)

#### 3. `agent_execution.py` - 1276 lines ⚠️ CRITICAL
**Breakdown Plan:**
- Extract WebSocket handlers → `websocket_handlers.py`
- Extract session management → `session_handlers.py`
- Extract step approval → `approval_handlers.py`
- Extract event publishing → `event_publishers.py`
- Keep main router logic (< 400 lines)

#### 4. `ticketing_integration_service.py` - 725 lines
**Breakdown Plan:**
- Extract connector factory → `connector_factory.py`
- Extract polling logic → `ticket_poller.py`
- Extract normalization → `ticket_normalizer.py` (may already exist)
- Keep orchestration in main file (< 400 lines)

#### 5. `resolution_verification_service.py` - 684 lines
**Breakdown Plan:**
- Extract verification strategies → `verification_strategies.py`
- Extract alert checking → `alert_checker.py`
- Extract ticket closure → `ticket_closer.py`
- Keep orchestration in main file (< 400 lines)

### Files Exceeding 400 Lines (Medium Priority)

#### 6. `ticketing_connections.py` - 680 lines
**Breakdown Plan:**
- Extract connection CRUD → separate service
- Extract test logic → `connection_tester.py`
- Keep endpoint definitions (< 300 lines)

#### 7. `yaml_processor.py` - 665 lines
**Breakdown Plan:**
- Extract parsing logic → `yaml_parser.py`
- Extract validation → `yaml_validator.py`
- Extract transformation → `yaml_transformer.py`
- Keep main processor (< 300 lines)

#### 8. `yaml_generator.py` - 634 lines
**Breakdown Plan:**
- Extract step generation → `step_generator.py`
- Extract input generation → `input_generator.py`
- Extract verification generation → `verification_generator.py`
- Keep main generator (< 300 lines)

#### 9. `llm_service.py` - 591 lines
**Breakdown Plan:**
- Extract provider abstraction → `llm_provider.py`
- Extract prompt management → `prompt_manager.py`
- Extract response parsing → `response_parser.py`
- Keep main service (< 300 lines)

#### 10. `azure_connector.py` - 591 lines
**Breakdown Plan:**
- Extract VM operations → `azure_vm_operations.py`
- Extract resource operations → `azure_resource_operations.py`
- Extract authentication → `azure_auth.py`
- Keep main connector (< 300 lines)

#### 11. `decision.py` - 577 lines
**Breakdown Plan:**
- Extract recommendation endpoints → `recommendation_endpoints.py`
- Extract pattern endpoints → `pattern_endpoints.py`
- Extract context endpoints → `context_endpoints.py`
- Keep main router (< 200 lines)

#### 12. `execution_controller.py` - 566 lines
**Breakdown Plan:**
- Extract session management → `session_controller.py`
- Extract step management → `step_controller.py`
- Extract feedback handling → `feedback_controller.py`
- Keep main controller (< 300 lines)

#### 13. `runbooks.py` - 554 lines
**Breakdown Plan:**
- Extract CRUD endpoints → `runbook_crud_endpoints.py`
- Extract generation endpoints → `runbook_generation_endpoints.py`
- Extract version endpoints → `runbook_version_endpoints.py`
- Keep main router (< 200 lines)

---

## Phase 3: Code Quality Improvements

### 1. Remove Code Duplication

**Areas to check:**
- [ ] Similar query patterns across controllers
- [ ] Duplicate validation logic
- [ ] Repeated error handling patterns
- [ ] Common transformation logic

**Action:**
- Create shared utilities
- Extract common patterns to base classes
- Use decorators for repeated patterns

### 2. Improve Error Handling

**Current Issues:**
- Inconsistent error handling across controllers
- Some services raise exceptions, others return error dicts

**Action:**
- Standardize on exception-based error handling
- Use custom exception classes
- Implement error handling middleware

### 3. Improve Type Hints

**Action:**
- Add missing type hints
- Use `typing` module consistently
- Add return type annotations

### 4. Remove Dead Code

**Action:**
- Remove unused imports
- Remove commented-out code
- Remove unused functions/classes
- Remove backup files (`.backup.py`)

### 5. Improve Documentation

**Action:**
- Add docstrings to all public methods
- Document complex algorithms
- Add module-level documentation

---

## Phase 4: Repository Pattern Enforcement

### Missing Repositories

**Repositories to create:**
- [ ] `AlertRepository` (if missing)
- [ ] `RunbookUsageRepository` (if missing)
- [ ] `InfrastructureConnectionRepository` (if missing)
- [ ] `AgentWorkerAssignmentRepository` (if missing)

### Repository Methods to Add

**Standard CRUD methods needed:**
- `create(entity)` - Create new entity
- `get_by_id(id, tenant_id)` - Get by ID with tenant check
- `get_all(tenant_id, filters)` - Get all with filters
- `update(id, tenant_id, data)` - Update entity
- `delete(id, tenant_id)` - Delete entity
- `exists(id, tenant_id)` - Check existence

---

## Implementation Order

### Week 1: Critical MVC Fixes
1. Fix Ticket Controller (Priority 1)
2. Fix Alert Controller (Priority 2)
3. Fix Execution Controller (Priority 3)

### Week 2: Long Files Breakdown
1. Break down `runbook_generator_core.py`
2. Break down `step_execution_service.py`
3. Break down `agent_execution.py`

### Week 3: Remaining MVC Fixes
1. Fix Runbook Controller
2. Fix Connector Controller
3. Fix Agent Worker Controller
4. Fix Base Controller

### Week 4: Code Quality
1. Remove code duplication
2. Improve error handling
3. Add missing type hints
4. Remove dead code

---

## Success Criteria

### MVC Compliance
- ✅ Zero direct `db.query()` calls in controllers
- ✅ Zero direct `db.add()`, `db.commit()` in controllers
- ✅ All database operations go through repositories
- ✅ All business logic in services

### File Size
- ✅ No file exceeds 500 lines
- ✅ Most files under 400 lines
- ✅ Clear separation of concerns

### Code Quality
- ✅ No code duplication
- ✅ Consistent error handling
- ✅ Complete type hints
- ✅ No dead code

---

## Files to Review

### Controllers (MVC Violations)
- `backend/app/controllers/ticket_controller.py`
- `backend/app/controllers/alert_controller.py`
- `backend/app/controllers/execution_controller.py`
- `backend/app/controllers/runbook_controller.py`
- `backend/app/controllers/connector_controller.py`
- `backend/app/controllers/agent_worker_controller.py`
- `backend/app/controllers/base_controller.py`

### Long Files (Breakdown Needed)
- `backend/app/services/runbook/generation/runbook_generator_core.py` (1364 lines)
- `backend/app/services/execution/step_execution_service.py` (1297 lines)
- `backend/app/api/v1/endpoints/agent_execution.py` (1276 lines)
- `backend/app/services/ticketing_integration_service.py` (725 lines)
- `backend/app/services/resolution_verification_service.py` (684 lines)
- `backend/app/api/v1/endpoints/ticketing_connections.py` (680 lines)
- `backend/app/services/runbook/generation/yaml_processor.py` (665 lines)
- `backend/app/services/runbook/generation/yaml_generator.py` (634 lines)
- `backend/app/services/llm_service.py` (591 lines)
- `backend/app/services/infrastructure/azure_connector.py` (591 lines)
- `backend/app/api/v1/endpoints/decision.py` (577 lines)
- `backend/app/controllers/execution_controller.py` (566 lines)
- `backend/app/api/v1/endpoints/runbooks.py` (554 lines)

---

## Next Steps

1. **Start with Priority 1**: Fix Ticket Controller MVC violations
2. **Create missing repositories**: Ensure all models have repositories
3. **Break down largest files**: Start with `runbook_generator_core.py`
4. **Iterate**: Fix one file at a time, test, commit

---

## Notes

- All changes should maintain backward compatibility
- Each refactoring should be tested before moving to next
- Use feature branches for each major refactoring
- Document breaking changes if any








