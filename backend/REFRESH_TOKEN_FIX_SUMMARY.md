# ManageEngine Token Refresh Fix - Implementation Summary

## Problem Identified

The refresh_token was being lost after the first token refresh, causing subsequent refreshes to fail with "requires OAuth credentials" error.

### Root Causes:
1. **`refresh_access_token()` didn't return `refresh_token`** - When Zoho refreshed the token, the refresh_token wasn't included in the response, so it got overwritten with None
2. **Tokens not persisted if API call failed** - Even if refresh succeeded, if `fetch_tickets()` failed, refreshed tokens were lost
3. **No preservation of existing refresh_token** - If Zoho didn't return a new refresh_token, we didn't preserve the existing one

## Fixes Implemented

### 1. Fixed `refresh_access_token()` Method (`zoho_oauth.py`)

**Changes:**
- Added `existing_refresh_token` parameter to preserve existing refresh_token
- Always includes `refresh_token` in return dictionary
- If Zoho returns a new refresh_token, uses it
- If Zoho doesn't return one, preserves the existing refresh_token
- Enhanced error handling and logging

**Compliance with Zoho OAuth 2.0:**
- ✅ Follows Zoho's OAuth 2.0 refresh token flow
- ✅ Handles cases where Zoho may or may not return a new refresh_token
- ✅ Preserves refresh_token as per Zoho documentation (refresh tokens don't expire)

### 2. Updated Token Refresh in Fetchers

**Files Updated:**
- `manageengine.py` - Updated `_get_valid_token()` to pass `existing_refresh_token`
- `zoho.py` - Updated `_get_valid_token()` to pass `existing_refresh_token`

**Changes:**
- Both now pass the existing refresh_token to preserve it
- Enhanced error messages to distinguish between missing vs invalid refresh_token
- Better logging of refresh_token preservation

### 3. Fixed Token Persistence in Poller (`ticketing_poller.py`)

**Changes:**
- Tracks if tokens were refreshed before making API call
- Persists refreshed tokens even if `fetch_tickets()` fails
- Prevents token loss due to API errors, network issues, etc.

**Flow:**
1. Before API call: Store original meta_data
2. Token refresh happens (if needed) → updates meta_data in memory
3. API call succeeds or fails
4. If tokens were refreshed: Always persist to database, even if API failed
5. This ensures refreshed tokens are never lost

## Testing Recommendations

### 1. Verify Refresh Token is Preserved
```sql
-- Before refresh
SELECT meta_data::json->>'refresh_token' as refresh_token_before 
FROM ticketing_tool_connections WHERE tool_name = 'manageengine';

-- Wait for token to expire (or manually expire it)
-- After refresh attempt
SELECT meta_data::json->>'refresh_token' as refresh_token_after 
FROM ticketing_tool_connections WHERE tool_name = 'manageengine';

-- refresh_token_after should match refresh_token_before (or be new if Zoho returned one)
```

### 2. Check Logs for Token Refresh
Look for these log messages:
- `"Refreshing ManageEngine access token using domain: {domain}"` - Refresh attempted
- `"Refreshed ManageEngine OAuth token (expires_at: ..., refresh_token_preserved: True)"` - Refresh succeeded
- `"Zoho did not return new refresh_token, preserving existing one"` - Existing token preserved
- `"Zoho returned new refresh_token, using it"` - New token received

### 3. Test Token Persistence on API Failure
- Simulate API failure (network issue, invalid endpoint, etc.)
- Verify that refreshed tokens are still persisted to database
- Check logs for: `"Fetch failed but tokens were refreshed. Persisting tokens..."`

## Compliance with ManageEngine/Zoho OAuth 2.0

### ✅ Generate Access Token and Refresh Token
- Correctly exchanges authorization code for access_token and refresh_token
- Stores both tokens in database

### ✅ Refresh Access Tokens
- Uses refresh_token to get new access_token
- Preserves refresh_token (as per Zoho docs, refresh tokens don't expire)
- Handles cases where Zoho may return a new refresh_token

### ✅ Error Handling
- Detects invalid/expired refresh_token
- Provides clear error messages
- Handles network errors gracefully

### ✅ Token Storage
- Securely stores tokens in database
- Persists tokens even if API calls fail
- Never loses refresh_token during refresh

## Next Steps

1. **Re-authorize the connection** (since current refresh_token is empty):
   - Go to Settings → Ticketing Connections
   - Click "Authorize" for ManageEngine connection
   - Complete OAuth flow to get new tokens

2. **Monitor logs** for the next few hours to verify:
   - Token refresh happens automatically when access_token expires
   - Refresh_token is preserved
   - No more "requires OAuth credentials" errors

3. **Verify long-term stability**:
   - Check after 24 hours that connection still works
   - Verify refresh_token is still in database
   - Confirm automatic refresh is working

## Files Modified

1. `backend/app/services/ticketing_connectors/zoho_oauth.py`
2. `backend/app/services/ticketing_connectors/manageengine.py`
3. `backend/app/services/ticketing_connectors/zoho.py`
4. `backend/app/services/ticketing_poller.py`



