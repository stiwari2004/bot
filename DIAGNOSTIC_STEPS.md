# Diagnostic Steps for Azure Command Execution

## Problem
Commands are not executing. Need to diagnose systematically:
1. Server connectivity
2. Command execution
3. Telemetry

## Diagnostic Endpoints Created

### 1. Test Azure Connection
**Endpoint:** `POST /api/v1/agent/debug/test-azure-connection?session_id={session_id}`

This endpoint tests connectivity step by step:
- Step 1: Finds first step
- Step 2: Gets connection config
- Step 3: Gets connector
- Step 4: Tests with simple command (`echo 'Azure connectivity test successful'`)

**Usage:**
```bash
curl -X POST "http://localhost:8000/api/v1/agent/debug/test-azure-connection?session_id=55"
```

### 2. Check Azure VM Status (NEW - Check for Stuck Commands)
**Endpoint:** `GET /api/v1/agent/debug/check-azure-vm-status?session_id={session_id}`

This endpoint checks the actual Azure VM instance view to see:
- VM power state (running/stopped)
- VM provisioning state
- **Extensions status** (including Run Command extension)
- **Whether there's actually a command running** (vs false conflict)

**Usage:**
```bash
curl "http://localhost:8000/api/v1/agent/debug/check-azure-vm-status?session_id=57"
```

**What to look for:**
- `running_command_detected: true` → There IS a real command running
- `running_command_detected: false` → No command running (false conflict!)
- Check `extensions` array for Run Command extension status
- Check `vm_power_state` - VM must be "running" for commands to work

### 3. Debug Execution State
**Endpoint:** `GET /api/v1/agent/debug/execution-state?session_id={session_id}`

Shows current session state, steps, connection config, etc.

## Changes Made

### 1. Temporarily Disabled Clear Command
- The `clear_run_command_state` call before first step is now disabled
- This was added recently and might be causing issues
- Location: `backend/app/services/execution/step_execution_service.py` line 113-122

### 2. Added Extensive Logging
- Added detailed logging at every step of execution
- Logs connection config details, credentials, command, etc.
- Location: `backend/app/services/execution/step_execution_service.py` and `azure_connector.py`

### 3. Enhanced Azure Connector Logging
- Logs each retry attempt
- Logs conflict detection
- Logs result processing

## Next Steps

1. **Check if there's actually a stuck command:**
   ```bash
   curl "http://localhost:8000/api/v1/agent/debug/check-azure-vm-status?session_id=57"
   ```
   This will show:
   - VM power state (must be "running")
   - Whether Run Command extension shows a running command
   - Extension status details
   - **If `running_command_detected: false` → It's a false conflict!**

2. **Test Connectivity:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/agent/debug/test-azure-connection?session_id=57"
   ```
   This will tell us:
   - Can we get connection config?
   - Can we get the connector?
   - Can we execute a simple test command?

2. **Check Backend Logs:**
   Look for:
   - `[EXECUTE_STEP]` - Step execution logs
   - `[AZURE_CONNECTOR]` - Azure connector logs
   - Connection config details
   - Credential availability

3. **If Test Command Fails:**
   - Check if resource_id is set correctly
   - Check if Azure credentials are available
   - Check if VM is running
   - Check Azure permissions

4. **If Test Command Succeeds but Real Commands Fail:**
   - Check command format
   - Check timeout settings
   - Check conflict detection logic

## Log Patterns to Look For

### Successful Execution:
```
[EXECUTE_STEP] ===== STARTING COMMAND EXECUTION =====
[AZURE_CONNECTOR] ===== STARTING AZURE RUN COMMAND =====
[AZURE_CONNECTOR] ===== ATTEMPT 1/5 =====
[AZURE_CONNECTOR] ===== COMMAND EXECUTION SUCCESS =====
[AZURE_CONNECTOR] ===== PROCESSING RESULT =====
[EXECUTE_STEP] ===== COMMAND EXECUTION COMPLETED =====
```

### Failure Patterns:
- `Azure connector requires resource_id` → Connection config issue
- `Azure credentials required` → Credential issue
- `Conflict` → Command already running (real or false)
- `Timeout` → Command taking too long
- `Permission denied` → Azure RBAC issue

