# Codebase Refactoring to MVC Architecture

## Current Issues
- Files with 1400-1500+ lines (violates best practices)
- Mixed concerns (business logic in endpoints, endpoints in services)
- No clear MVC separation
- Unused code accumulating
- Hard to maintain and test

## Target MVC Structure

```
backend/app/
├── models/          # Data models (SQLAlchemy) - ✅ Already exists
├── schemas/         # Pydantic schemas (request/response) - ✅ Already exists
├── controllers/     # NEW: Request handling, validation, response formatting
├── services/        # Business logic (refactored)
├── repositories/    # NEW: Data access layer (database operations)
├── core/           # Configuration, database, logging - ✅ Already exists
└── api/            # Route definitions only (thin layer)
```

## Refactoring Strategy

### Phase 1: Identify Large Files & Dependencies

**Large Files to Refactor:**
1. `services/execution_engine.py` (~700 lines)
2. `services/infrastructure_connectors.py` (~1155 lines)
3. `api/v1/endpoints/runbooks.py` (~600 lines)
4. `api/v1/endpoints/ticket_ingestion.py` (~634 lines)
5. `api/v1/endpoints/executions.py` (~635 lines)
6. `api/v1/endpoints/agent_execution.py` (~371 lines)
7. `api/v1/endpoints/connectors.py` (~500+ lines)

### Phase 2: Create MVC Structure

#### A. Controllers (Request/Response Handling)
```
controllers/
├── __init__.py
├── runbook_controller.py      # From runbooks.py endpoint
├── ticket_controller.py       # From ticket_ingestion.py
├── execution_controller.py    # From executions.py + agent_execution.py
├── connector_controller.py    # From connectors.py
└── base_controller.py         # Base class with common utilities
```

**Responsibilities:**
- Request validation
- Response formatting
- Error handling
- Authentication/authorization
- Call services (no business logic)

#### B. Repositories (Data Access)
```
repositories/
├── __init__.py
├── base_repository.py         # Base CRUD operations
├── runbook_repository.py
├── ticket_repository.py
├── execution_repository.py
├── credential_repository.py
└── infrastructure_repository.py
```

**Responsibilities:**
- Database queries
- Model operations
- Transaction management
- No business logic

#### C. Services (Business Logic - Refactored)
```
services/
├── execution/
│   ├── __init__.py
│   ├── execution_engine.py        # Core execution logic (reduced)
│   ├── execution_session_service.py
│   ├── step_execution_service.py
│   └── approval_service.py
├── infrastructure/
│   ├── __init__.py
│   ├── connector_factory.py       # Factory pattern
│   ├── ssh_connector.py
│   ├── azure_connector.py
│   ├── database_connector.py
│   └── local_connector.py
├── runbook/
│   ├── __init__.py
│   ├── runbook_generator.py
│   ├── runbook_search.py
│   ├── runbook_parser.py
│   └── runbook_normalizer.py
└── ticket/
    ├── __init__.py
    ├── ticket_analysis_service.py
    ├── ticket_status_service.py
    └── ticket_ingestion_service.py
```

### Phase 3: Break Down Large Files

#### 1. `infrastructure_connectors.py` (1155 lines) → Split into:

```
services/infrastructure/
├── __init__.py
├── base_connector.py              # InfrastructureConnector base class
├── connector_factory.py           # get_connector() function
├── ssh_connector.py               # SSHConnector (~200 lines)
├── azure_connector.py             # AzureBastionConnector (~400 lines)
├── database_connector.py          # DatabaseConnector (~200 lines)
├── api_connector.py               # APIConnector (~150 lines)
└── local_connector.py             # LocalConnector (~100 lines)
```

#### 2. `execution_engine.py` (~700 lines) → Split into:

```
services/execution/
├── __init__.py
├── execution_engine.py            # Main orchestrator (~200 lines)
├── session_service.py             # Session creation/management (~150 lines)
├── step_execution_service.py      # Step execution logic (~200 lines)
├── approval_service.py            # Approval workflow (~100 lines)
└── rollback_service.py            # Rollback logic (~50 lines)
```

#### 3. `runbooks.py` endpoint (~600 lines) → Split into:

```
controllers/runbook_controller.py  # Request handling (~150 lines)
repositories/runbook_repository.py # Data access (~100 lines)
services/runbook/                  # Business logic (already exists)
```

#### 4. `ticket_ingestion.py` (~634 lines) → Split into:

```
controllers/ticket_controller.py   # Request handling (~150 lines)
repositories/ticket_repository.py # Data access (~100 lines)
services/ticket/                   # Business logic (already exists)
```

### Phase 4: Remove Unused Code

**Files to Check for Unused Code:**
- `api/v1/endpoints/test.py`
- `api/v1/endpoints/test_auth.py`
- `api/v1/endpoints/demo.py` (if not used)
- `api/v1/endpoints/network.py` (if not used)
- Dead imports
- Unused functions/methods

## Implementation Steps

### Step 1: Create Directory Structure
```bash
mkdir -p backend/app/controllers
mkdir -p backend/app/repositories
mkdir -p backend/app/services/execution
mkdir -p backend/app/services/infrastructure
mkdir -p backend/app/services/runbook
mkdir -p backend/app/services/ticket
```

### Step 2: Create Base Classes
- `repositories/base_repository.py` - Generic CRUD
- `controllers/base_controller.py` - Common controller utilities

### Step 3: Refactor Infrastructure Connectors (Highest Priority)
- Split `infrastructure_connectors.py` into separate connector files
- Create factory pattern for connector selection

### Step 4: Refactor Execution Engine
- Split into focused services
- Move data access to repositories

### Step 5: Refactor Endpoints to Controllers
- Move business logic to services
- Move data access to repositories
- Keep controllers thin (validation + service calls)

### Step 6: Clean Up
- Remove unused code
- Update imports
- Fix tests

## File Size Targets

**Best Practice Limits:**
- Controllers: 100-200 lines max
- Services: 200-300 lines max
- Repositories: 100-200 lines max
- Models: 50-100 lines max

**Current → Target:**
- `infrastructure_connectors.py`: 1155 → 5 files × ~200 lines each
- `execution_engine.py`: 700 → 5 files × ~150 lines each
- `runbooks.py`: 600 → Controller (150) + Repository (100) + Service (existing)
- `ticket_ingestion.py`: 634 → Controller (150) + Repository (100) + Service (existing)

## Benefits

1. **Maintainability**: Smaller, focused files easier to understand
2. **Testability**: Isolated components easier to test
3. **Reusability**: Services can be reused across controllers
4. **Scalability**: Easy to add new features without touching existing code
5. **Team Collaboration**: Multiple developers can work on different layers

## Migration Strategy

1. **Incremental**: Refactor one module at a time
2. **Backward Compatible**: Keep old endpoints working during transition
3. **Test Coverage**: Ensure tests pass after each refactor
4. **Documentation**: Update API docs as we refactor

## Next Steps

1. Start with `infrastructure_connectors.py` (largest file)
2. Then `execution_engine.py` (most complex)
3. Then endpoints → controllers
4. Finally cleanup unused code


