# PowerShell Command Execution Blocked - Troubleshooting Guide

## Issue
PowerShell commands executed by Cursor AI are being blocked, preventing commands from running successfully.

## Possible Causes

### 1. Windows Execution Policy
Windows PowerShell has execution policies that can block script execution.

**Check current policy:**
```powershell
Get-ExecutionPolicy -List
```

**Fix (Run PowerShell as Administrator):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Or for all users (requires admin):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

### 2. Windows Defender / Antivirus
Windows Defender or other antivirus software may be blocking PowerShell execution.

**Check Windows Defender:**
1. Open Windows Security
2. Go to "Virus & threat protection"
3. Check "Protection history" for blocked items
4. Add exclusions if needed:
   - `C:\Users\Admin\Documents\bot` (project folder)
   - `C:\Program Files\Cursor` (Cursor installation)

### 3. Firewall Rules
Windows Firewall may be blocking PowerShell network access.

**Check Firewall:**
1. Open Windows Defender Firewall
2. Go to "Advanced settings"
3. Check "Inbound Rules" and "Outbound Rules"
4. Look for PowerShell-related rules that might be blocking

**Allow PowerShell through Firewall:**
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "PowerShell - Allow" -Direction Outbound -Program "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -Action Allow
```

### 4. Group Policy Restrictions
If on a corporate/managed PC, Group Policy might be restricting PowerShell.

**Check Group Policy:**
```powershell
# Run as Administrator
gpresult /H gpresult.html
# Open gpresult.html and search for "PowerShell" or "Script"
```

### 5. Cursor-Specific Issues
Cursor might need specific permissions or settings.

**Check Cursor Settings:**
1. Open Cursor Settings (Ctrl+,)
2. Search for "terminal" or "shell"
3. Check if PowerShell path is correct
4. Try changing terminal to Command Prompt temporarily to test

## Quick Fixes to Try

### Option 1: Run PowerShell as Administrator (Temporary)
1. Right-click PowerShell
2. Select "Run as Administrator"
3. Navigate to project: `cd C:\Users\Admin\Documents\bot`
4. Run commands manually

### Option 2: Use Command Prompt Instead
In Cursor, you can change the default terminal:
1. Open terminal in Cursor (Ctrl+`)
2. Click the dropdown next to "+" button
3. Select "Command Prompt" instead of PowerShell
4. Commands should work in CMD

### Option 3: Add Project Folder to Exclusions
1. Open Windows Security
2. Go to "Virus & threat protection"
3. Click "Manage settings" under "Virus & threat protection settings"
4. Scroll to "Exclusions"
5. Click "Add or remove exclusions"
6. Add folder: `C:\Users\Admin\Documents\bot`

### Option 4: Disable Real-time Protection Temporarily (For Testing)
⚠️ **Only for testing, re-enable after!**
1. Open Windows Security
2. Go to "Virus & threat protection"
3. Click "Manage settings"
4. Temporarily turn off "Real-time protection"
5. Test if commands work
6. **Re-enable immediately after testing**

## Recommended Solution (Safest)

### Step 1: Set Execution Policy (One-time, as Admin)
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 2: Add Project Folder to Windows Defender Exclusions
1. Windows Security → Virus & threat protection → Manage settings
2. Exclusions → Add folder → `C:\Users\Admin\Documents\bot`

### Step 3: Verify PowerShell Works
```powershell
# Test in PowerShell
Get-ExecutionPolicy
docker --version
docker-compose --version
```

## Alternative: Use Docker Desktop Terminal

If PowerShell continues to be blocked, you can:
1. Use Docker Desktop's built-in terminal
2. Or use WSL (Windows Subsystem for Linux) if installed
3. Or use Git Bash terminal in Cursor

## Testing After Fix

Once fixed, test with a simple command:
```powershell
docker-compose ps
```

If this works, the blocking issue is resolved.

## Still Having Issues?

If none of the above work:
1. Check Windows Event Viewer for specific error messages
2. Check if any security software (McAfee, Norton, etc.) is installed
3. Try running Cursor as Administrator (not recommended long-term)
4. Check if you're on a managed/corporate PC with restrictions

## Notes for Development Environment

Since this is a **development/test environment**:
- Execution policy can be more permissive
- Firewall rules can be less restrictive
- Antivirus exclusions are acceptable for dev folders
- Security is still important, but can be balanced with development needs




