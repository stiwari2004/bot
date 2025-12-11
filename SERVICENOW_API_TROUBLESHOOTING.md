# ServiceNow REST API Authentication Troubleshooting

Based on [Official ServiceNow REST API Documentation](https://www.servicenow.com/docs/bundle/zurich-api-reference/page/integrate/inbound-rest/concept/c_RESTAPI.html)

## ✅ What We're Sending (CORRECT)

Our code is sending:
- **Format**: `Authorization: Basic <base64-encoded-username:password>`
- **Encoding**: Base64 (RFC 7617 compliant)
- **Headers**: `Content-Type: application/json`, `Accept: application/json`

This matches ServiceNow's requirements exactly.

## ❌ Why It's Failing (ServiceNow Side)

Since it worked 2 hours ago, something changed in ServiceNow:

### 1. **PDI Instance Refresh** (Most Likely)
- ServiceNow Personal Developer Instances (PDIs) refresh periodically
- All users, roles, and data get reset
- **Solution**: Recreate the user and assign roles

### 2. **Account Locked**
- Too many failed authentication attempts
- **Check**: User record > "Locked out" field
- **Solution**: Unlock account or reset password

### 3. **Missing Required Roles**
According to ServiceNow docs, user needs:
- `snc_platform_rest_api_access` - **REQUIRED** for REST API access
- `itil` - For incident access
- `sn_incident_read` - To read incidents
- `web_service_admin` - For web service operations (optional but recommended)

### 4. **System Property**
- Check: `glide.basicauth.required.api` system property
- Should be set appropriately for your instance

### 5. **Password Changed**
- Someone changed the password
- **Test**: Try logging into ServiceNow UI with same credentials

## 🔍 Step-by-Step Troubleshooting

### Step 1: Verify User Still Exists
1. Log into ServiceNow UI as admin
2. Go to: `System Security > Users > Users`
3. Search for: `bot-integration`
4. **Check**:
   - User exists?
   - Active = Yes?
   - Locked out = No?

### Step 2: Verify Roles
1. Open `bot-integration` user record
2. Go to "Roles" tab
3. **Verify these roles exist**:
   - ✅ `snc_platform_rest_api_access` (REQUIRED)
   - ✅ `itil`
   - ✅ `sn_incident_read`
   - ✅ `web_service_admin` (recommended)

### Step 3: Test Password
1. Log out of ServiceNow
2. Try logging in with `bot-integration` credentials
3. If UI login fails → password is wrong
4. If UI login works → password is correct, issue is elsewhere

### Step 4: Check System Properties
1. Go to: `System Properties > Properties`
2. Search for: `glide.basicauth.required.api`
3. Check its value and ensure it's set correctly

### Step 5: Check ServiceNow Logs
1. Go to: `System Logs > All`
2. Filter for: `bot-integration` or `401` or `authentication`
3. Look for error messages about failed authentication

## 🛠️ Quick Fix: Recreate User

If PDI was refreshed, recreate the user:

1. **Create New User**:
   - User ID: `bot-integration`
   - Active: Yes
   - Password: Set strong password
   - Password Needs Reset: No

2. **Assign Roles**:
   - `snc_platform_rest_api_access` (REQUIRED)
   - `itil`
   - `sn_incident_read`
   - `web_service_admin`

3. **Test in Postman**:
   - Use Basic Auth (Postman will auto-encode)
   - URL: `https://dev229095.service-now.com/api/now/table/incident`
   - Should return 200 OK

## 📝 Verification Checklist

- [ ] User exists and is Active
- [ ] User is not Locked out
- [ ] Role `snc_platform_rest_api_access` is assigned
- [ ] Role `itil` is assigned
- [ ] Role `sn_incident_read` is assigned
- [ ] Password works in ServiceNow UI login
- [ ] Postman Basic Auth works (200 OK)
- [ ] System property `glide.basicauth.required.api` is set correctly

## 🔗 References

- [ServiceNow REST API Documentation](https://www.servicenow.com/docs/bundle/zurich-api-reference/page/integrate/inbound-rest/concept/c_RESTAPI.html)
- [ServiceNow Integration Guide](https://www.servicenow.com/community/developer-articles/servicenow-to-servicenow-integration-step-by-step-guide/ta-p/2305317)









