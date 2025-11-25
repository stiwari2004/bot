# Fix: Zoho Not Returning Refresh Token

## Root Cause

**Zoho only returns `refresh_token` on the FIRST authorization.** If the OAuth app was already authorized before, Zoho will NOT return a new `refresh_token` in subsequent authorizations, even if you include `access_type=offline` in the authorization URL.

### Evidence from Backend Logs

```
Zoho token response keys: ['access_token', 'scope', 'api_domain', 'token_type', 'expires_in']
```

**Notice**: `refresh_token` is **NOT** in the response keys!

## Solution: Revoke Existing Authorization

To get a `refresh_token`, you must:

1. **Revoke the existing authorization** in Zoho
2. **Re-authorize** the app (this will be treated as the "first" authorization)
3. Zoho will then return `refresh_token` in the token exchange response

## Steps to Fix

### Option 1: Revoke via Zoho Account Settings (Recommended)

1. Go to [Zoho Accounts](https://accounts.zoho.in/) (use `.in` for Indian accounts, `.com` for others)
2. Sign in with your Zoho credentials
3. Navigate to **Sessions** (in the left-hand menu)
4. Scroll down to the **Connected Apps** section
5. Find your OAuth app (Client ID: `1000.WXEEIPQ1O5QX0BBAFOFOLSZMUCPFOK`)
   - It might show as "ServiceDesk Plus" or "ManageEngine" or just the app name
6. Hover over the application and click **Revoke Access**
7. Confirm by clicking **Yes, Proceed**
8. Go back to your application and click "Authorize" again
9. Complete the OAuth flow
10. **This time, Zoho should return `refresh_token`**

### Option 2: Revoke via API (If Available)

Zoho provides a revoke token endpoint, but it requires the existing `refresh_token` (which we don't have). So this option won't work in our case.

### Option 3: Create a New OAuth App

If revoking doesn't work:

1. Go to [Zoho API Console](https://api-console.zoho.in/)
2. Create a **new OAuth app** with the same scopes
3. Update the `client_id` and `client_secret` in your database
4. Authorize the new app (this will be the "first" authorization)
5. Zoho will return `refresh_token`

## Verification

After revoking and re-authorizing, check the backend logs:

```bash
docker-compose logs backend --tail 100 | grep -i "refresh_token"
```

You should see:
- ✅ `"Zoho token response keys: ['access_token', 'refresh_token', ...]"`
- ✅ `"✅ SUCCESS: Zoho returned refresh_token!"`
- ✅ `"refresh_token saved: True"`

Instead of:
- ❌ `"Zoho token response keys: ['access_token', 'scope', 'api_domain', 'token_type', 'expires_in']"`
- ❌ `"Zoho did not return refresh_token in token exchange response!"`
- ❌ `"refresh_token saved: False"`

## Why This Happens

According to Zoho's OAuth 2.0 documentation:

> **Refresh tokens are only issued on the first authorization.** If a user has already authorized your app, subsequent authorizations will NOT return a new refresh token, even if you include `access_type=offline`.

This is a security feature to prevent token proliferation. Once a refresh token is issued, it should be reused for all future token refreshes.

## Prevention

Once you have a `refresh_token`:

1. **Never delete it** from the database
2. **Always preserve it** during token refresh (our code already does this)
3. **Only revoke** if absolutely necessary (e.g., security breach)

## Current Code Status

✅ Our code already:
- Includes `access_type=offline` in authorization URL
- Preserves existing `refresh_token` during token refresh
- Logs detailed information about refresh token presence/absence

❌ What we can't fix:
- Zoho's behavior of not returning refresh_token on subsequent authorizations
- This requires manual revocation in Zoho account settings

