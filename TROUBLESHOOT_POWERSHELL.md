# PowerShell Troubleshooting Steps

## Step 1: Check Execution Policy

Open PowerShell as Administrator and run:
```powershell
Get-ExecutionPolicy -List
```

**Expected output:**
```
        Scope ExecutionPolicy
        ----- ---------------
MachinePolicy       Undefined
   UserPolicy       Undefined
      Process       Undefined
  CurrentUser       RemoteSigned
 LocalMachine       Undefined
```

**If CurrentUser is "Restricted":**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Step 2: Test Basic PowerShell Commands

In a regular PowerShell window (not Cursor), test:
```powershell
# Test 1: Basic command
Get-Date

# Test 2: Docker command
docker --version

# Test 3: Docker Compose
docker-compose --version

# Test 4: Navigate to project
cd C:\Users\Admin\Documents\bot
docker-compose ps
```

**If these work in regular PowerShell but not in Cursor:**
- The issue is Cursor-specific, not PowerShell itself
- Try changing Cursor's terminal settings

---

## Step 3: Check Cursor Terminal Settings

1. Open Cursor Settings (Ctrl+,)
2. Search for "terminal"
3. Check these settings:
   - `terminal.integrated.shell.windows` (should be PowerShell path)
   - `terminal.integrated.shellArgs.windows` (should be empty or `-NoProfile`)
   - `terminal.integrated.profiles.windows` (check if PowerShell is configured)

**Try changing terminal to Command Prompt:**
1. In Cursor terminal, click the dropdown next to "+"
2. Select "Command Prompt" instead of PowerShell
3. Test: `docker-compose ps`

---

## Step 4: Check Windows Defender Real-time Protection

Even with folder exclusion, real-time protection might block:
1. Open Windows Security
2. Virus & threat protection → Manage settings
3. Check if "Real-time protection" is ON
4. Temporarily turn OFF (for testing only!)
5. Test commands in Cursor
6. **Re-enable immediately after testing**

---

## Step 5: Check Firewall Rules

Run in PowerShell as Administrator:
```powershell
# Check if PowerShell is blocked
Get-NetFirewallApplicationFilter | Where-Object {$_.Program -like "*powershell*"}

# Allow PowerShell through firewall
New-NetFirewallRule -DisplayName "PowerShell - Allow Outbound" -Direction Outbound -Program "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -Action Allow
New-NetFirewallRule -DisplayName "PowerShell - Allow Inbound" -Direction Inbound -Program "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -Action Allow
```

---

## Step 6: Check for Other Security Software

Check if you have:
- McAfee
- Norton
- Kaspersky
- Bitdefender
- Any corporate security software

These might have their own blocking rules.

---

## Step 7: Test with Different Terminal in Cursor

### Option A: Use Command Prompt
1. In Cursor, open terminal
2. Click dropdown → Select "Command Prompt"
3. Test: `docker-compose ps`

### Option B: Use Git Bash (if installed)
1. In Cursor, open terminal
2. Click dropdown → Select "Git Bash"
3. Test: `docker-compose ps`

### Option C: Use WSL (if installed)
1. In Cursor, open terminal
2. Click dropdown → Select "WSL" or "Ubuntu"
3. Test: `docker-compose ps`

---

## Step 8: Check Cursor Permissions

Try running Cursor as Administrator (temporary test):
1. Right-click Cursor shortcut
2. "Run as Administrator"
3. Test commands
4. **Note**: Not recommended long-term, but helps diagnose

---

## Step 9: Check Event Viewer for Errors

1. Open Event Viewer (Win + X → Event Viewer)
2. Windows Logs → Application
3. Look for errors around the time you try to run commands
4. Check for:
   - PowerShell errors
   - Security/Defender blocks
   - Application errors

---

## Step 10: Test Docker Directly

In regular PowerShell (outside Cursor):
```powershell
cd C:\Users\Admin\Documents\bot
docker-compose ps
docker-compose logs backend --tail 10
```

**If this works:**
- Docker is fine
- Issue is Cursor terminal integration

**If this doesn't work:**
- Docker installation issue
- Need to check Docker Desktop

---

## Quick Diagnostic Commands

Run these in regular PowerShell (not Cursor) and share results:

```powershell
# 1. Execution Policy
Get-ExecutionPolicy -List

# 2. PowerShell Version
$PSVersionTable

# 3. Docker Status
docker --version
docker-compose --version

# 4. Check if Docker is running
docker ps

# 5. Test project commands
cd C:\Users\Admin\Documents\bot
docker-compose ps
```

---

## Alternative: Use Docker Desktop Terminal

If Cursor terminal continues to be blocked:
1. Open Docker Desktop
2. Use Docker Desktop's built-in terminal
3. Navigate to project folder
4. Run commands there

---

## Most Likely Solutions (In Order)

1. **Execution Policy** - Most common issue
2. **Cursor Terminal Settings** - Terminal integration problem
3. **Windows Defender** - Even with exclusions, might block
4. **Firewall Rules** - PowerShell blocked by firewall
5. **Other Security Software** - Third-party antivirus blocking

---

## Next Steps

1. Run Step 1 (Check Execution Policy) - Share the output
2. Run Step 2 (Test in regular PowerShell) - Does it work?
3. Try Step 7 (Different terminal in Cursor) - Does CMD work?

Based on results, we'll narrow down the issue!




