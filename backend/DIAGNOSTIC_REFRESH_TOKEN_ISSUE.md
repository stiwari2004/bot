# ManageEngine Token Refresh Issue - Diagnostic Findings

## Root Cause Analysis

### Issue 1: **Refresh Token NOT Returned from Token Refresh** ⚠️ CRITICAL

**Location**: `backend/app/services/ticketing_connectors/zoho_oauth.py` lines 228-234

**Problem**: 
The `refresh_access_token()` method does NOT include `refresh_token` in its return dictionary. When Zoho/ManageEngine refreshes an access token, they may return a NEW refresh token, but our code is not capturing it.

**Current Code**:
```python
return {
    "access_token": token_data.get("access_token"),
    "expires_in": expires_in,
    "expires_at": expires_at.isoformat(),
    "token_type": token_data.get("token_type", "Bearer"),
    "api_domain": token_data.get("api_domain", "https://desk.zoho.com")
}
```

**Missing**: `refresh_token` field!

**Impact**:
- If Zoho returns a new refresh_token during refresh, we lose it
- The old refresh_token in database may become invalid
- Eventually, refresh will fail because we're using an expired/invalid refresh_token

---

### Issue 2: **Refresh Token Not Persisted After Refresh** ⚠️ CRITICAL

**Location**: `backend/app/services/ticketing_poller.py` lines 223-226

**Problem**:
Even if tokens are refreshed successfully in memory, if `fetch_tickets()` raises an exception, the refreshed tokens are NOT persisted to the database.

**Current Flow**:
1. `_get_valid_token()` refreshes token → updates `connection_meta` dict in memory
2. `fetch_tickets()` may fail (API error, network issue, etc.)
3. Exception handler (lines 240-249) does NOT persist `meta_data`
4. Refreshed tokens are lost

**Impact**:
- Token refresh succeeds but is lost if API call fails
- Next poll will try to refresh again (wasteful)
- If refresh_token expires, we're stuck

---

### Issue 3: **No Refresh Token Validation** ⚠️

**Location**: `backend/app/services/ticketing_connectors/manageengine.py` lines 272-300

**Problem**:
The code checks if `refresh_token` exists but doesn't validate if it's still valid. If refresh_token itself is expired, the refresh will fail silently.

**Current Code**:
```python
if refresh_token and client_id and client_secret:
    try:
        # Refresh attempt
    except Exception as e:
        logger.error(f"Failed to refresh ManageEngine token: {e}")
        return None  # Silent failure
```

**Impact**:
- No clear error message when refresh_token is expired
- User sees generic "requires OAuth credentials" error
- Hard to diagnose the actual problem

---

### Issue 4: **Refresh Token May Not Be Returned by Zoho**

**Research Needed**:
According to Zoho OAuth documentation:
- When refreshing an access token, Zoho may or may not return a new refresh_token
- If refresh_token is not returned, the old one should still be valid
- However, refresh_tokens can expire after ~90 days of inactivity

**Action Required**:
- Check Zoho API response during token refresh to see if `refresh_token` is included
- If it is included, we MUST save it
- If it's not included, we should keep the existing refresh_token

---

## Diagnostic Steps to Verify

### Step 1: Check Database State
Run this SQL query to see what's in the database:
```sql
SELECT 
    id,
    tool_name,
    api_base_url,
    last_sync_at,
    last_sync_status,
    last_error,
    meta_data::json->>'access_token' as has_access_token,
    meta_data::json->>'refresh_token' as has_refresh_token,
    meta_data::json->>'expires_at' as expires_at,
    meta_data::json->>'client_id' as has_client_id,
    meta_data::json->>'client_secret' as has_client_secret
FROM ticketing_tool_connections 
WHERE tool_name = 'manageengine';
```

### Step 2: Check Backend Logs
Look for these log messages:
- `"Refreshing ManageEngine access token using domain: {zoho_domain}"` - Refresh was attempted
- `"Failed to refresh ManageEngine token: {e}"` - Refresh failed (check error message)
- `"ManageEngine token expired but no refresh token available"` - Missing refresh_token
- `"Refreshed ManageEngine OAuth token (expires_at: {new_tokens.get('expires_at')})"` - Refresh succeeded

### Step 3: Check Token Expiration
- Check `expires_at` in database
- Calculate if token is actually expired
- Check if refresh_token exists in database

---

## Expected Behavior vs Actual Behavior

### Expected:
1. Token expires → Refresh token → Get new access_token AND new refresh_token (if provided)
2. Save both tokens to database
3. Use new tokens for next API call

### Actual:
1. Token expires → Refresh token → Get new access_token only
2. Save access_token to database (if API call succeeds)
3. Old refresh_token remains (may be invalid)
4. Eventually refresh fails because refresh_token is expired/invalid

---

## ✅ FIXES IMPLEMENTED

### 1. **Fixed `refresh_access_token()` to preserve refresh_token** ✅
   - Now includes `refresh_token` in return dictionary
   - If Zoho returns a new refresh_token, uses it
   - If Zoho doesn't return one, preserves the existing refresh_token
   - Added `existing_refresh_token` parameter to explicitly preserve it
   - Added better error handling and logging

### 2. **Fixed token persistence in poller** ✅
   - Tracks if tokens were refreshed before API call
   - Persists refreshed tokens even if `fetch_tickets()` fails
   - Prevents token loss due to API errors
   - Better error messages indicating what's missing

### 3. **Enhanced error messages** ✅
   - Distinguishes between missing credentials (refresh_token, client_id, client_secret)
   - Detects invalid/expired refresh_token errors
   - Provides actionable error messages

### 4. **Updated both Zoho and ManageEngine fetchers** ✅
   - Both now pass `existing_refresh_token` parameter
   - Both have improved error handling
   - Both log when refresh_token is preserved vs updated

## Implementation Details

### Changes Made:

1. **`zoho_oauth.py`**:
   - Added `existing_refresh_token` parameter to `refresh_access_token()`
   - Always includes `refresh_token` in return dict
   - Preserves existing refresh_token if Zoho doesn't return new one
   - Better error detection and logging

2. **`manageengine.py`**:
   - Updated to pass `existing_refresh_token` parameter
   - Enhanced error messages
   - Better logging of refresh_token preservation

3. **`zoho.py`**:
   - Updated to pass `existing_refresh_token` parameter
   - Enhanced error messages
   - Better logging of refresh_token preservation

4. **`ticketing_poller.py`**:
   - Tracks if tokens were refreshed before API call
   - Persists refreshed tokens in exception handler if fetch fails
   - Prevents token loss due to API errors

