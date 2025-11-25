# ManageEngine OAuth 2.0 Setup in Postman

## Overview
ManageEngine ServiceDesk Plus Cloud uses Zoho OAuth 2.0 for authentication. This guide will help you set up and test the OAuth flow in Postman before implementing it in code.

## Step 1: Create a New Request in Postman

1. Open Postman
2. Create a new request (or use the existing ManageEngine request from the workspace)
3. Name it: "Generate Access Token and Refresh Token"

## Step 2: Configure OAuth 2.0 Authorization

1. Go to the **Authorization** tab
2. Select **OAuth 2.0** as the Type
3. Click **Get New Access Token**

## Step 3: Fill in OAuth 2.0 Details

### Grant Type
- Select: **Authorization Code**

### Callback URL
- **IMPORTANT**: If Postman auto-fills `https://oauth.pstmn.io/v1/vscode-callback`, you have two options:

  **Option A: Override the Callback URL (Recommended)**
  1. Click directly in the "Callback URL" field
  2. Delete the auto-filled URL
  3. Enter: `http://localhost:8000/oauth/callback`
  4. (This should match the redirect URI registered in your Zoho OAuth app)
  
  **Option B: Use Postman's Callback URL (For Testing Only)**
  1. Keep: `https://oauth.pstmn.io/v1/vscode-callback`
  2. **BUT**: You must also add this URL to your Zoho OAuth app's authorized redirect URIs
  3. Go to your Zoho OAuth app settings and add this callback URL
  4. This is only for testing - your production code should use `http://localhost:8000/oauth/callback`

**Note**: If the Callback URL field is grayed out or not editable:
- Try clicking directly on the text field (not the label)
- Or use the "Advanced" section to add it as a query parameter
- Or manually construct the authorization URL (see Alternative Method below)

### Auth URL
- Enter: `https://accounts.zoho.in/oauth/v2/auth`
- (For Indian accounts - use `.in` domain)
- (For other regions, use `.com` domain: `https://accounts.zoho.com/oauth/v2/auth`)

### Access Token URL
- Enter: `https://accounts.zoho.in/oauth/v2/token`
- (For Indian accounts - use `.in` domain)
- (For other regions, use `.com` domain: `https://accounts.zoho.com/oauth/v2/token`)

### Client ID
- Enter your ManageEngine OAuth Client ID

### Client Secret
- Enter your ManageEngine OAuth Client Secret

### Scope
- Enter: `SDPOnDemand.requests.ALL`
- (This is the ManageEngine-specific scope)

### State
- Optional: Enter a random string for CSRF protection
- Example: `test-state-12345`

### Client Authentication
- Select: **Send as Basic Auth header** (or **Send client credentials in body**)

## Step 4: Additional Parameters

In the **Advanced** section, you may need to add:

### Additional Query Parameters
- `access_type`: `offline` (IMPORTANT: This is required to get a refresh token)

### Additional Body Parameters
- None needed (all parameters are in the query string)

## Alternative Method: Manual Authorization URL (If Callback URL is Stuck)

If you cannot change the callback URL in Postman's OAuth 2.0 helper:

### Step 1: Construct and Open Authorization URL

**IMPORTANT**: For manual Postman testing, we'll use a simple redirect URI that you can control, or extract the code from the URL before the backend processes it.

#### Option A: Use a Simple Redirect (Requires Adding Redirect URI to Zoho)

**First, add the redirect URI to your Zoho OAuth app:**
1. Go to https://api-console.zoho.in/
2. Select your OAuth app
3. Go to "Authorized Redirect URIs"
4. Add: `http://localhost:3000`
5. Save

**Then:**

1. **Manually construct the authorization URL** (this is a GET request, NOT POST):
   ```
   https://accounts.zoho.in/oauth/v2/auth?client_id=1000.WXEEIPQ1O5QX0BBAFOFOLSZMUCPFOK&scope=SDPOnDemand.requests.ALL&redirect_uri=http://localhost:3000&response_type=code&access_type=offline&state=test-123
   ```
   Note: Using `http://localhost:3000` as redirect_uri to avoid backend state validation issues

2. **IMPORTANT: Open this URL in your web browser** (Chrome, Firefox, etc.)
   - Do NOT send it as a POST request in Postman
   - The URL should be opened directly in a browser
   - You'll see the Zoho sign-in page (this is correct!)

3. **Sign in to your Zoho account** on the page that opens

4. **Authorize the application** - click "Allow" or "Authorize"

5. **After authorization**, Zoho will redirect you to:
   ```
   http://localhost:3000?code=AUTHORIZATION_CODE&state=test-state-12345
   ```
   - The frontend will show an error (expected), but the `code` parameter will be in the URL
   - **Quickly copy the full URL from your browser's address bar** before the page loads

6. **Extract the authorization code** from the URL:
   - Look for `code=1000.xxxxx` in the URL
   - Copy everything after `code=` and before the next `&` (or end of URL)
   - Example: If URL is `http://localhost:3000?code=1000.abc123xyz&state=test-state-12345`
   - Copy: `1000.abc123xyz`

#### Option B: Use Backend Callback (Requires Proper State)

If you want to use the backend callback (`http://localhost:8000/oauth/callback`), you need to:

1. **Get your connection ID** from the database:
   ```sql
   SELECT id FROM ticketing_tool_connections WHERE tool_name = 'manageengine';
   ```
   Let's say the ID is `7`

2. **Generate a state** in the format: `connection_id:random_string`
   - Example: `7:test-random-12345`

3. **Store this state in the database** (temporarily):
   ```sql
   UPDATE ticketing_tool_connections 
   SET meta_data = jsonb_set(
     meta_data::jsonb, 
     '{oauth_state}', 
     '"7:test-random-12345"'
   )::text
   WHERE id = 7;
   ```

4. **Use this state in your authorization URL**:
   ```
   https://accounts.zoho.in/oauth/v2/auth?client_id=1000.WXEEIPQ1O5QX0BBAFOFOLSZMUCPFOK&scope=SDPOnDemand.requests.ALL&redirect_uri=http://localhost:8000/oauth/callback&response_type=code&access_type=offline&state=7:test-random-12345
   ```

#### Option C: Use Registered Redirect URI with Proper State (No Zoho Changes Needed)

If you don't want to modify Zoho settings, use the existing registered redirect URI:

1. **Get your connection ID:**
   ```bash
   docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT id FROM ticketing_tool_connections WHERE tool_name = 'manageengine';"
   ```
   Example output: `id = 7`

2. **Generate a state** in format: `connection_id:random_string`
   - Example: `7:postman-test-12345`

3. **Store this state in the database:**
   ```bash
   docker-compose exec -T postgres psql -U postgres -d troubleshooting_ai -c "UPDATE ticketing_tool_connections SET meta_data = jsonb_set(meta_data::jsonb, '{oauth_state}', '\"7:postman-test-12345\"')::text WHERE id = 7;"
   ```
   (Replace `7` with your actual connection ID)

4. **Use this state in your authorization URL:**
   ```
   https://accounts.zoho.in/oauth/v2/auth?client_id=1000.WXEEIPQ1O5QX0BBAFOFOLSZMUCPFOK&scope=SDPOnDemand.requests.ALL&redirect_uri=http://localhost:8000/oauth/callback&response_type=code&access_type=offline&state=7:postman-test-12345
   ```

5. **After authorization**, the backend will handle it and redirect to frontend
   - Check backend logs for the authorization code
   - Or check the database for the new tokens

**Recommendation**: Use **Option A** if you can add the redirect URI to Zoho (quickest). Use **Option C** if you can't modify Zoho settings.

### Step 2: Exchange Code for Tokens (POST Request in Postman)

1. **In Postman, create a new request:**
   - Name: "Exchange Code for Tokens"
   - Method: **POST** (this one IS a POST request)
   - URL: `https://accounts.zoho.in/oauth/v2/token`

2. **Go to Headers tab:**
   - Add: `Content-Type: application/x-www-form-urlencoded`

3. **Go to Body tab:**
   - Select: **x-www-form-urlencoded**
   - Add these key-value pairs:
     - `grant_type`: `authorization_code`
     - `client_id`: `1000.WXEEIPQ1O5QX0BBAFOFOLSZMUCPFOK` (your Client ID)
     - `client_secret`: `YOUR_CLIENT_SECRET` (your actual Client Secret)
     - `redirect_uri`: `http://localhost:8000/oauth/callback`
     - `code`: `PASTE_THE_CODE_FROM_STEP_1_HERE`

4. **Send the request**

5. **Check the response** - you should see:
   ```json
   {
     "access_token": "1000.xxxxx...",
     "refresh_token": "1000.xxxxx...",
     "expires_in": 3600,
     "token_type": "Bearer",
     "api_domain": "https://sdpondemand.manageengine.in"
   }
   ```

**IMPORTANT**: Verify that `refresh_token` is present in the response. If it's missing, the issue is with the authorization request (missing `access_type=offline` parameter).

## Step 5: Request Token

1. Click **Request Token**
2. You'll be redirected to Zoho's authorization page
3. Log in and authorize the application
4. You'll be redirected back to Postman with the authorization code
5. Postman will automatically exchange the code for tokens

## Step 6: Verify Token Response

After successful token exchange, you should see:

```json
{
  "access_token": "1000.xxxxx...",
  "refresh_token": "1000.xxxxx...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "api_domain": "https://sdpondemand.manageengine.in"
}
```

**IMPORTANT**: Verify that `refresh_token` is present in the response. If it's missing:
- Check that `access_type=offline` was included in the authorization request
- Try revoking the app authorization in Zoho and re-authorizing
- Check your OAuth app configuration in Zoho

## Step 7: Test Token Refresh

1. Create a new request: "Refresh Access Token"
2. Set method to **POST**
3. URL: `https://accounts.zoho.in/oauth/v2/token`
4. Go to **Body** tab → **x-www-form-urlencoded**
5. Add parameters:
   - `grant_type`: `refresh_token`
   - `client_id`: Your Client ID
   - `client_secret`: Your Client Secret
   - `refresh_token`: The refresh token from Step 6

6. Send the request
7. You should receive a new `access_token` and possibly a new `refresh_token`

## Step 8: Test API Call

1. Create a new request: "Get Tickets"
2. Set method to **GET**
3. URL: `https://sdpondemand.manageengine.in/api/v3/requests`
4. Go to **Authorization** tab
5. Select **Bearer Token**
6. Enter the `access_token` from Step 6
7. Send the request
8. You should receive ticket data

## Troubleshooting

### Issue: No refresh_token in response
- **Solution**: Ensure `access_type=offline` is included in the authorization URL
- Revoke and re-authorize the app in Zoho
- Check OAuth app settings in Zoho console

### Issue: Invalid grant error
- **Solution**: Check that the authorization code hasn't expired (codes expire quickly)
- Ensure redirect_uri matches exactly what's registered

### Issue: Invalid client error
- **Solution**: Verify Client ID and Client Secret are correct
- Check that you're using the correct domain (.in vs .com)

## Key Points from Zoho OAuth Documentation

According to Zoho's OAuth 2.0 documentation:
1. **Refresh tokens do not expire** and can be reused
2. **Zoho may or may not return a new refresh_token** in the refresh response
3. **If a new refresh_token is returned, use it; otherwise, preserve the existing one**
4. **Access tokens expire** (typically 3600 seconds = 1 hour)
5. **Authorization codes expire quickly** (within minutes)

## Next Steps

Once you've successfully:
1. ✅ Obtained both `access_token` and `refresh_token` in Postman
2. ✅ Verified token refresh works
3. ✅ Tested an API call with the access token

Then we can proceed to verify and fix the code implementation to match the working Postman flow.

