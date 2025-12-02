# Configuration Cleanup Summary

## Overview
Moved hardcoded values to centralized configuration files to improve maintainability and flexibility.

## Changes Made

### 1. Created Centralized Runbook Configuration
**File**: `backend/app/config/runbook_config.py`

- **RunbookStructureConfig**: Defines runbook structure requirements
  - Section names (prechecks, steps, postchecks, inputs)
  - Required counts (prechecks: 3, steps: 5-6, postchecks: 1)
  - Remediation requirements (min: 4, max diagnostic-only: 2)

- **RunbookValidationConfig**: Defines validation rules
  - Stop words for keyword matching
  - Metric keywords (CPU, memory, disk, network, etc.)
  - Allowed step purposes and phase ordering
  - Remediation and diagnostic keywords

- **RunbookProcessingConfig**: Defines processing rules
  - YAML section indicators
  - PowerShell parameter fixes

### 2. Updated Core Configuration
**File**: `backend/app/core/config.py`

Added URL/endpoint configuration:
- `FRONTEND_BASE_URL`: Frontend application URL (default: http://localhost:3000)
- `BACKEND_BASE_URL`: Backend API URL (default: http://localhost:8000)
- `OAUTH_CALLBACK_URL`: OAuth callback URL (default: http://localhost:8000/oauth/callback)

### 3. Updated Files to Use Configuration

#### `backend/app/services/runbook/generation/runbook_quality_validator.py`
- Uses `runbook_structure` for section names and counts
- Uses `runbook_validation` for stop words, metric keywords, remediation/diagnostic keywords
- All hardcoded values replaced with config references

#### `backend/app/services/runbook/generation/runbook_generator_core.py`
- Uses `runbook_structure` for section names and validation counts
- Replaced hardcoded section names with config constants

#### `backend/app/services/runbook/generation/yaml_processor.py`
- Uses `runbook_structure` for section names
- Replaced hardcoded section name lists with config constants

#### `backend/app/api/v1/endpoints/ticketing_connections.py`
- Uses `settings.FRONTEND_BASE_URL` instead of hardcoded `http://localhost:3000`
- Uses `settings.OAUTH_CALLBACK_URL` instead of hardcoded `http://localhost:8000/oauth/callback`
- All redirect URLs now use configuration

## Benefits

1. **Maintainability**: All configuration values in one place
2. **Flexibility**: Easy to change requirements without code changes
3. **Environment-specific**: URLs can be set via environment variables
4. **Consistency**: Same values used across all code
5. **Testability**: Easy to override configs for testing

## Usage

### Accessing Runbook Configuration
```python
from app.config import runbook_structure, runbook_validation, runbook_processing

# Use structure config
prechecks_count = runbook_structure.PRECHECKS_COUNT  # 3
steps_min = runbook_structure.STEPS_MIN  # 5
steps_max = runbook_structure.STEPS_MAX  # 6

# Use validation config
stop_words = runbook_validation.STOP_WORDS
metric_keywords = runbook_validation.METRIC_KEYWORDS
remediation_keywords = runbook_validation.REMEDIATION_KEYWORDS
```

### Accessing URL Configuration
```python
from app.core.config import settings

frontend_url = settings.FRONTEND_BASE_URL
backend_url = settings.BACKEND_BASE_URL
oauth_callback = settings.OAUTH_CALLBACK_URL
```

## Environment Variables

Set these in `.env` or `docker-compose.yml`:
```bash
FRONTEND_BASE_URL=http://localhost:3000
BACKEND_BASE_URL=http://localhost:8000
OAUTH_CALLBACK_URL=http://localhost:8000/oauth/callback
```

## Future Improvements

1. Move more hardcoded values to config (thresholds, timeouts, etc.)
2. Create tenant-specific configuration overrides
3. Add configuration validation on startup
4. Create admin UI for configuration management




