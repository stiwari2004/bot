# Create Production Environment in GitHub

## Step-by-Step Guide

### Step 1: Navigate to Environments Settings

1. Go to your GitHub repository
2. Click on **Settings** (top menu bar)
3. In the left sidebar, scroll down to **"Environments"** (under "Code and automation")
4. Click on **"Environments"**

### Step 2: Create New Environment

1. Click the **"New environment"** button (top right)
2. Enter the environment name: **`production`**
3. Click **"Configure environment"**

### Step 3: Configure Environment (No Protection Rules)

You'll see several sections. Here's what to configure:

#### Environment Details
- **Name:** `production` (already set)
- **Environment URL:** `https://resolvify.tech` (optional, but useful for tracking)

#### Protection Rules Section

**IMPORTANT:** Do NOT enable any protection rules if you want auto-deployment!

1. **Required reviewers**
   - ❌ **Leave this DISABLED** (no reviewers)
   - If you see any reviewers listed, click the X to remove them
   - This is what blocks auto-deployment - keep it empty!

2. **Wait timer**
   - ❌ **Leave this DISABLED** or set to `0` minutes
   - This adds a delay before deployment - not needed for auto-deploy

3. **Deployment branches**
   - ✅ **Enable this** and set to: **"Selected branches"**
   - Add branch: **`main`**
   - This ensures only the main branch can deploy to production (good security practice)

4. **Deployment protection rules** (if available)
   - ❌ **Leave all disabled** for auto-deployment

#### Secrets and Variables (Optional)

You can add environment-specific secrets here if needed, but the workflow already uses repository secrets, so this is optional.

### Step 4: Save the Environment

1. Scroll to the bottom
2. Click **"Save protection rules"** or **"Save environment"**
3. The environment is now created!

## Verification

After creating the environment:

1. Go back to **Settings** → **Environments**
2. You should see **`production`** listed
3. Click on it to verify:
   - ✅ No required reviewers
   - ✅ Wait timer disabled (or 0 minutes)
   - ✅ Deployment branches allows `main`

## What This Enables

With the environment created (and no protection rules):

- ✅ **Automatic deployment** after successful test runs
- ✅ **No manual approval required**
- ✅ **Deployment tracking** in GitHub (you can see deployment history)
- ✅ **Branch protection** (only `main` can deploy)
- ✅ **Deployment URL tracking** (links to https://resolvify.tech)

## Workflow Behavior

Once the environment exists, your workflow will:

1. ✅ Run tests automatically
2. ✅ Build images automatically
3. ✅ Merge dev to main automatically
4. ✅ **Deploy to production automatically** (no approval needed!)

## Troubleshooting

### "Environment not found" error
- **Cause:** Environment name mismatch
- **Fix:** Ensure the environment is named exactly `production` (lowercase, no spaces)

### "Deployment waiting for approval"
- **Cause:** Required reviewers are enabled
- **Fix:** Go to Settings → Environments → `production` → Remove all required reviewers

### "Branch not allowed"
- **Cause:** Deployment branches restriction
- **Fix:** Ensure `main` branch is added to allowed deployment branches

### "Environment doesn't appear in Settings"
- **Cause:** You might not have admin access
- **Fix:** Ensure you have repository admin permissions

## Visual Guide

```
GitHub Repository
    ↓
Settings (top menu)
    ↓
Environments (left sidebar, under "Code and automation")
    ↓
New environment (button, top right)
    ↓
Name: production
    ↓
Configure environment
    ↓
Protection Rules:
    - Required reviewers: ❌ DISABLED (empty)
    - Wait timer: ❌ DISABLED (0 minutes)
    - Deployment branches: ✅ ENABLED (main branch only)
    ↓
Save environment
```

## Alternative: Create via GitHub CLI

If you prefer command line:

```bash
gh api repos/:owner/:repo/environments/production \
  --method PUT \
  --field name=production \
  --field deployment_branch_policy='{"protected_branches":false,"custom_branches":true,"custom_branch_policies":[{"name":"main"}]}'
```

This creates the environment with:
- No required reviewers
- No wait timer
- Only `main` branch can deploy

## Summary

**Quick Steps:**
1. Settings → Environments → New environment
2. Name: `production`
3. **DO NOT enable required reviewers**
4. **DO NOT enable wait timer**
5. Enable deployment branches → Add `main`
6. Save

**Result:** Auto-deployment enabled! 🚀

