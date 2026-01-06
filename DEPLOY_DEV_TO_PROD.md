# Deploy Changes from Dev to Production

## How Auto-Deployment Works

Your workflow is configured to **automatically deploy to production** when:

1. ✅ Changes are pushed to `dev` branch
2. ✅ Dev deployment workflow runs and **succeeds**
3. ✅ Production workflow is **automatically triggered**
4. ✅ Tests pass in production workflow
5. ✅ Dev is automatically merged to `main`
6. ✅ Production deployment happens automatically

## Check Current Status

### Step 1: Check if Dev Deployment Completed

1. Go to your GitHub repository
2. Click on **"Actions"** tab (top menu)
3. Look for the workflow run: **"Deploy to Dev Environment"**
4. Check if it shows:
   - ✅ **Green checkmark** = Dev deployment succeeded → Production should have triggered
   - ⏳ **Yellow circle** = Still running
   - ❌ **Red X** = Failed → Production won't trigger

### Step 2: Check if Production Workflow Ran

1. Still in **"Actions"** tab
2. Look for workflow run: **"Deploy to Production"**
3. Check the status:
   - ✅ **Green checkmark** = Already deployed to production!
   - ⏳ **Yellow circle** = Currently deploying
   - ❌ **Red X** = Failed (check logs)
   - ⏸️ **Waiting** = Waiting for approval (if environment protection is enabled)

## If Production Workflow Hasn't Run Yet

### Option 1: Wait for Auto-Trigger (Recommended)

If dev deployment just completed:
- **Wait 1-2 minutes** - GitHub needs time to trigger the production workflow
- Check the **"Actions"** tab again
- The production workflow should appear automatically

### Option 2: Manually Trigger Production Deployment

If you want to deploy immediately:

1. Go to **"Actions"** tab
2. Click on **"Deploy to Production"** workflow (left sidebar)
3. Click **"Run workflow"** button (top right)
4. Select branch: **`dev`** (or `main` if already merged)
5. Optionally check **"Skip tests"** (not recommended)
6. Click **"Run workflow"**

### Option 3: Push to Main Branch (Emergency)

For emergency deployments, you can push directly to `main`:

```bash
git checkout main
git merge dev
git push origin main
```

This will trigger the production workflow directly (bypasses dev deployment).

## What Happens During Auto-Deployment

```
Your changes in dev
    ↓
Push to dev branch
    ↓
"Deploy to Dev Environment" workflow runs
    ↓
Tests pass ✅
    ↓
Build dev images ✅
    ↓
Deploy to dev server ✅
    ↓
[WORKFLOW COMPLETES SUCCESSFULLY]
    ↓
"Deploy to Production" workflow automatically triggers
    ↓
Run tests ✅
    ↓
Build production images ✅
    ↓
Merge dev → main automatically ✅
    ↓
Deploy to production server ✅
    ↓
DONE! 🚀
```

## Verify Deployment

### Check Production Server

1. SSH into your production server
2. Check if containers are running:
   ```bash
   cd /opt/opsbot/bot
   docker-compose -f docker-compose.production.yml ps
   ```
3. Check recent git commits:
   ```bash
   git log --oneline -5
   ```
4. Check container logs:
   ```bash
   docker-compose -f docker-compose.production.yml logs --tail=50 backend
   ```

### Check GitHub Actions

1. Go to **Actions** tab
2. Find the latest **"Deploy to Production"** run
3. Click on it to see detailed logs
4. Check each job:
   - ✅ **test** - Tests passed
   - ✅ **build** - Images built
   - ✅ **merge-to-main** - Dev merged to main
   - ✅ **deploy-production** - Deployed to server

## Troubleshooting

### "Production workflow didn't trigger"

**Possible causes:**
1. Dev deployment didn't complete successfully
2. Dev deployment is still running
3. Workflow trigger delay (wait 1-2 minutes)

**Solution:**
- Check dev deployment status
- Wait a few minutes
- Manually trigger if needed

### "Production workflow is waiting for approval"

**Cause:** Environment protection rules require approval

**Solution:**
- Go to Settings → Environments → `production`
- Remove required reviewers
- Disable wait timer

### "Deployment failed"

**Check:**
1. Production workflow logs
2. SSH secrets configured correctly
3. Production server accessible
4. Docker compose file exists

## Quick Status Check

Run this to see if your changes are in production:

```bash
# On production server
cd /opt/opsbot/bot
git log --oneline -1
git diff HEAD~1 HEAD --stat
```

Compare with your dev branch to see if changes are synced.

## Summary

**If dev deployment succeeded:**
- ✅ Production workflow should have triggered automatically
- ✅ Check **Actions** tab to see status
- ✅ If it's running/waiting, let it complete
- ✅ If it failed, check logs and fix issues

**If you need to deploy now:**
- Use **"Run workflow"** button in Actions tab
- Or push directly to `main` branch (emergency only)

**Your changes are automatically synced** once the production workflow completes successfully! 🎉

