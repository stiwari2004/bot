# Testing OAuth Flow with cURL

## Step 1: Get Authorization URL from Backend

```bash
curl -X GET "http://localhost:8000/api/v1/settings/ticketing-connections/7/oauth/authorize"
```

This will return JSON with `authorization_url` and `state`. Copy both values.

## Step 2: Open Authorization URL in Browser

Open the `authorization_url` in your browser, sign in, and authorize.

After authorization, you'll be redirected to:
```
http://localhost:8000/oauth/callback?code=AUTHORIZATION_CODE&state=STATE_VALUE
```

**Copy the `code` parameter value** from the URL.

## Step 3: Exchange Code for Tokens (cURL Test)

Use this curl command to see Zoho's raw response:

```bash
curl -X POST "https://accounts.zoho.in/oauth/v2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=1000.WXEEIPQ1O5QX0BBAFOFOLSZMUCPFOK" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=http://localhost:8000/oauth/callback" \
  -d "code=AUTHORIZATION_CODE_FROM_STEP_2"
```

Replace:
- `YOUR_CLIENT_SECRET` with your actual client secret
- `AUTHORIZATION_CODE_FROM_STEP_2` with the code you copied

## Step 4: Check the Response

The response should be JSON. Look for:
- `access_token`: Should be present
- `refresh_token`: **This is what we're checking for!**
- `expires_in`: Token expiration time
- `token_type`: Usually "Bearer"

## What to Look For

1. **If `refresh_token` is in the response**: The issue is in our code not saving it properly
2. **If `refresh_token` is NOT in the response**: Zoho is not returning it, which could mean:
   - The app was already authorized before (Zoho only returns refresh_token on first authorization)
   - The `access_type=offline` parameter isn't working
   - OAuth app configuration issue



