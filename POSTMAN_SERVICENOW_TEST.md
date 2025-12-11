# ServiceNow Postman Test Setup

## Step 1: Create a New Request in Postman

1. **Method**: `GET`
2. **URL**: `https://dev229095.service-now.com/api/now/table/incident`

## Step 2: Set Authorization

1. Go to the **Authorization** tab
2. Select **Type**: `Basic Auth`
3. Enter:
   - **Username**: `bot-integration`
   - **Password**: `[your password]`

## Step 3: Set Headers

Go to the **Headers** tab and ensure these are set:
- `Content-Type`: `application/json`
- `Accept`: `application/json`

## Step 4: Set Query Parameters (Optional)

Go to the **Params** tab:
- `sysparm_limit`: `10`
- `sysparm_orderby`: `sys_updated_on:desc`
- `sysparm_display_value`: `true`

## Step 5: Send Request

Click **Send** and verify you get a 200 OK response with incident data.

## Step 6: Check What Postman Actually Sent

1. After sending, look at the **Request** section below
2. Click on the **Headers** tab in the request details
3. Find the `Authorization` header
4. **Copy the EXACT value** of the Authorization header

The Authorization header should look something like:
```
Authorization: Basic [base64-encoded-string]
```

## Step 7: Share the Authorization Header

Paste the EXACT Authorization header value here so we can replicate it exactly in the code.

---

## Alternative: Manual Header Method

If you want to set the Authorization header manually:

1. Go to **Headers** tab
2. Add a new header:
   - **Key**: `Authorization`
   - **Value**: `Basic [base64-encoded-username:password]`

To generate the base64 value:
- Format: `username:password`
- Example: `bot-integration:your-password-here`
- Base64 encode that string
- Prepend with `Basic ` (with a space)

Example:
```
Authorization: Basic Ym90LWludGVncmF0aW9uOnlvdXItcGFzc3dvcmQ=
```









