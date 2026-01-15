# TODO List - Prioritization Guide

## High Priority - Critical Functionality

### 1. ✅ LLM Analysis for Resolution Verification - COMPLETED
**File**: `backend/app/services/resolution_verification_service.py:878`
**Status**: ✅ **IMPLEMENTED**
**Description**: LLM analysis is fully implemented in `_analyze_resolution_with_llm()` method. It analyzes step outputs to determine if issues are resolved, providing more nuanced analysis than rule-based verification. The method is called from `verify_resolution()` and overrides rule-based results when LLM confidence is higher.
**Implementation Details**:
- Uses `_chat_once_with_system()` for LLM calls
- Includes proper error handling and JSON parsing
- Falls back gracefully if LLM analysis fails
- Added safety check for method existence
**Date Completed**: 2026-01-15

### 2. ✅ Embedding Model Loading - Non-blocking - COMPLETED
**File**: `backend/app/core/vector_store.py:23`
**Status**: ✅ **IMPLEMENTED**
**Description**: Embedding model loading is now fully async and non-blocking. The `get_shared_embedding_model()` function uses `asyncio.to_thread()` to load the SentenceTransformer model in a background thread, preventing blocking during application startup.
**Implementation Details**:
- Uses `asyncio.to_thread()` for non-blocking model loading
- Implements proper locking to prevent concurrent loads
- Includes timeout handling (5 minutes)
- Model is cached as singleton after first load
- All embedding operations are async
**Date Completed**: 2026-01-15

## Medium Priority - Feature Enhancements

### 3. Connector Service Implementations
**File**: `backend/app/services/connector_service.py:188-192`
**Context**:
```python
"zabbix": None,  # TODO: Implement
"solarwinds": None,  # TODO: Implement
"manageengine": None,  # TODO: Implement
"zendesk": None,  # TODO: Implement
"bmcremedy": None,  # TODO: Implement
```
**Description**: Multiple connector services are stubbed but not implemented.
**Impact**: Limited integration capabilities
**Effort**: High (5-10 days per connector)
**Dependencies**: Each connector needs API research and implementation
**Note**: ManageEngine is partially implemented elsewhere, may need consolidation

## Low Priority - Code Quality & Documentation

### 4. Metadata Usage in Execution Engine
**File**: `backend/app/api/v1/endpoints/agent_execution.py:103`
**Context**:
```python
# Note: metadata is not used in execution engine, but can be stored in session if needed
```
**Description**: Metadata parameter is accepted but not currently used. Should either implement usage or remove parameter.
**Impact**: Code clarity, potential feature enhancement
**Effort**: Low (1-2 hours)
**Dependencies**: None

### 5. Comment Addition for ManageEngine
**File**: `backend/app/services/ticketing_integration_service.py:308`
**Context**:
```python
# Note: Comment will be added in a future update if needed
```
**Description**: Comment functionality for ManageEngine ticket updates is deferred.
**Impact**: Limited ticketing integration features
**Effort**: Low (2-4 hours)
**Dependencies**: ManageEngine API documentation

## Informational Notes (Not TODOs)

These are documentation notes, not actionable TODOs:

- `backend/app/services/execution_engine.py:5` - NOTE: File kept for backward compatibility
- `backend/app/services/infrastructure_connectors.py:5` - NOTE: File kept for backward compatibility  
- `backend/app/services/runbook_generator.py:4` - NOTE: File kept for backward compatibility
- `backend/app/services/execution/step_execution_service.py:321` - Note about sequential execution
- `backend/app/services/execution/step_execution_service.py:413` - Note about cleanup timing
- `backend/app/services/execution/step_execution_service.py:1004` - NOTE about session status commit
- `backend/app/services/execution/step_execution_service.py:1013` - Note about verify_resolution
- `backend/app/services/infrastructure/azure_connector.py:110` - Note about conflict prevention
- `backend/app/services/ticketing_poller.py:210` - Note about json import
- `backend/app/services/runbook/generation/runbook_generator_core.py:1364` - Note about diagnostic runbooks
- `backend/app/services/duplicate_detector.py:55` - Note about document search
- `backend/app/core/vector_store.py:181,292` - Notes about pgvector casting
- `backend/app/models/credential.py:21` - Note about encryption
- `backend/sql/enable_rls.sql:88` - Note about tenant context

## Summary

**Total Actionable TODOs**: 5
- **High Priority**: 2
- **Medium Priority**: 1  
- **Low Priority**: 2

**Recommendation**: 
1. Start with #1 (LLM Analysis) - highest impact on core functionality
2. Then #2 (Non-blocking embedding) - improves user experience
3. #3 (Connectors) can be done incrementally as needed
4. #4 and #5 are quick wins for code quality




