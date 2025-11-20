# Testing ManageEngine API in Postman

## ⚠️ IMPORTANT: ManageEngine requires form-encoded input_data, NOT raw JSON!

According to ManageEngine API documentation, `input_data` must be sent as a **URL-encoded form parameter**, not as raw JSON in the request body.

## Setup

1. **Open Postman** and create a new request
2. **Method**: `POST`
3. **URL**: `https://sdpondemand.manageengine.in/api/v3/requests`

## Headers

```
Authorization: Zoho-oauthtoken YOUR_ACCESS_TOKEN
Content-Type: application/x-www-form-urlencoded
```

Replace `YOUR_ACCESS_TOKEN` with the token from your database.

## Body (Form-Encoded)

Go to the **Body** tab, select **x-www-form-urlencoded**, and add:

**Key**: `input_data`  
**Value**: `{"list_info": {"row_count": 10, "start_index": 1}}`

## Test Cases

### Test 1: Full input_data with list_info
**Body** (x-www-form-urlencoded):
- Key: `input_data`
- Value: `{"list_info": {"row_count": 10, "start_index": 1, "sort_fields": [{"field": "modified_time", "order": "desc"}]}}`

### Test 2: Minimal input_data
**Body** (x-www-form-urlencoded):
- Key: `input_data`
- Value: `{"list_info": {"row_count": 10}}`

### Test 3: Empty input_data
**Body** (x-www-form-urlencoded):
- Key: `input_data`
- Value: `{}`

### Test 4: GET request (no body)
**Method**: `GET`
**URL**: `https://sdpondemand.manageengine.in/api/v3/requests?limit=10`
**Headers**: 
```
Authorization: Zoho-oauthtoken YOUR_ACCESS_TOKEN
Accept: application/json
```
(No body needed for GET)

## Getting Your Access Token

**Option 1: Use the helper script**
```powershell
.\get-manageengine-token.ps1
```

**Option 2: Direct database query**
```powershell
docker-compose exec postgres psql -U postgres -d troubleshooting_ai -c "SELECT meta_data::json->>'access_token' FROM ticketing_tool_connections WHERE tool_name = 'manageengine' LIMIT 1;"
```

**Option 3: From backend logs**
```powershell
docker-compose logs backend --tail=100 | Select-String "Zoho-oauthtoken" | Select-Object -First 1
```

## What to Look For

- **200 OK**: Success! Note the exact format that worked
- **400 Bad Request**: Check the error message - it will tell you what's wrong
- **401 Unauthorized**: Token might be expired
- **404 Not Found**: Wrong endpoint

## Key Points

1. **Content-Type must be `application/x-www-form-urlencoded`** (NOT `application/json`)
2. **input_data must be a JSON string** in the form parameter value
3. **Use the Body tab → x-www-form-urlencoded**, NOT raw JSON

## Once You Find the Working Format

Share:
1. The exact request format that returned 200
2. The response body structure
3. Any special headers needed

Then I'll update the code to match!
