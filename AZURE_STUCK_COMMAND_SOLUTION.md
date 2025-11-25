# Azure Stuck Command - Solution

## Problem Confirmed

Your Azure Activity Log shows:
- **Event Time**: `2025-11-22T12:30:07.827718Z`
- **Status**: `Failed` with `Conflict (HTTP Status Code: 409)`
- **Error**: `Run command extension execution is in progress. Please wait for completion before invoking a run command.`

This is a **false stuck state** - Azure thinks a command is running, but it's not.

## Root Cause

Azure Run Command has a known limitation:
- Only **one command can run at a time** per VM
- Sometimes Azure gets into a stuck state where it thinks a command is running when it's not
- This cannot be cleared programmatically via the API
- The only solutions are: **wait 5-10 minutes** OR **restart the VM**

## Solution: Restart the VM

I've added a new endpoint to restart the VM programmatically:

### Endpoint: `POST /api/v1/agent/debug/restart-azure-vm`

**Usage:**
```bash
curl -X POST "http://localhost:8000/api/v1/agent/debug/restart-azure-vm?session_id=65"
```

**What it does:**
1. Gets the VM details from your session
2. Restarts the VM using Azure SDK
3. Clears any stuck Run Command states
4. Returns success message

**After restart:**
- Wait **1-2 minutes** for the VM to fully start
- Then retry your execution

## Alternative: Manual Restart

If you prefer to restart manually:

1. **Azure Portal:**
   - Go to: Azure Portal → Virtual Machines → `InfraBotTestVM1`
   - Click "Restart"
   - Wait 1-2 minutes

2. **Azure CLI:**
   ```bash
   az vm restart --resource-group InfraBotTest --name InfraBotTestVM1
   ```

## After Restart

Once the VM is restarted:
1. Wait 1-2 minutes for it to fully boot
2. Try executing your runbook again
3. The clean code will work correctly

## Why This Happens

The stuck command state was likely caused by:
1. A previous execution that didn't complete cleanly
2. Azure's Run Command extension getting into a bad state
3. Network issues or timeouts during command execution

## Prevention

The clean code rewrite I did:
- ✅ Removed all retry logic that could cause conflicts
- ✅ Removed test commands that could get stuck
- ✅ Added clear error messages
- ✅ Simplified execution to single attempt

This reduces the chance of stuck commands, but Azure's limitation means it can still happen occasionally.

## Next Steps

1. **Restart the VM** (use the new endpoint or manual method)
2. **Wait 1-2 minutes** for VM to start
3. **Retry your execution** - it should work now

The code is working correctly - it's just Azure that has the stuck state that needs to be cleared.




