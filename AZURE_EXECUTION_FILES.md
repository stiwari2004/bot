# Azure Command Execution - File Analysis

## Files That Execute Azure Commands

### 1. `backend/app/services/infrastructure/azure_connector.py`
**Purpose:** Main Azure connector - executes commands via Azure Run Command API
**What it does:**
- Executes commands on Azure VMs
- Handles authentication
- Parses results
- **Status:** ✅ Clean rewrite completed - no retries, no workarounds

### 2. `backend/app/services/execution/step_execution_service.py`
**Purpose:** Executes individual runbook steps
**What it does:**
- Gets connection config
- Gets connector
- Calls `connector.execute_command()` for each step
- **Status:** ✅ Clean - no Azure-specific workarounds

### 3. `backend/app/services/execution/rollback_service.py`
**Purpose:** Rolls back executed steps
**What it does:**
- Executes rollback commands in reverse order
- Uses same connector as step execution
- **Status:** ✅ Clean - only executes on rollback, not before steps

### 4. `backend/app/api/v1/endpoints/agent_execution.py`
**Purpose:** API endpoints for execution management
**What it does:**
- `POST /debug/test-azure-connection` - **⚠️ EXECUTES A TEST COMMAND**
  - Line 837: `await connector.execute_command(command="echo 'Azure connectivity test successful'")`
  - This diagnostic endpoint executes a command that could cause conflicts!
- `GET /debug/check-azure-vm-status` - Only reads VM status, doesn't execute commands
- **Status:** ⚠️ Diagnostic endpoint may be causing conflicts

## Files That DON'T Execute Commands (But Interact with Azure)

### 5. `backend/app/services/execution/connection_service.py`
**Purpose:** Gets connection configuration
**What it does:**
- Extracts CI/server name from ticket
- Calls `CloudDiscoveryService.discover_azure_vm()` - **ONLY QUERIES Azure API, NO COMMANDS**
- Returns connection config
- **Status:** ✅ Safe - no command execution

### 6. `backend/app/services/cloud_discovery.py`
**Purpose:** Discovers Azure VMs from cloud accounts
**What it does:**
- Queries Azure API to find VMs (`compute_client.virtual_machines.get()`)
- Returns VM info (resource_id, os_type, etc.)
- **Status:** ✅ Safe - only reads VM metadata, no command execution

## Root Cause Analysis

**The Problem:**
Azure Run Command has a stuck command state that cannot be cleared programmatically.

**Possible Causes:**
1. **Diagnostic endpoint** (`/debug/test-azure-connection`) executes a test command that gets stuck
2. **Previous execution** left a stuck command state
3. **Azure limitation** - only one command at a time, and stuck states persist

**The Solution:**
The clean rewrite is working correctly. The error message now clearly explains:
- Azure only allows one command at a time
- If stuck, wait 5-10 minutes OR restart the VM
- Check Azure Portal Activity Logs

**What to Check:**
1. Are you calling `/debug/test-azure-connection` before executing steps? **This could be causing the conflict!**
2. Has the VM been restarted since the last stuck command?
3. Check Azure Portal > VM > Activity Logs to see what command is stuck

## Recommendation

**Disable or modify the diagnostic endpoint** to not execute commands, or add a warning that it will cause conflicts if Azure has a stuck command.




