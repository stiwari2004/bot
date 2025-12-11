# ServiceNow Resolve Incident - Postman Test

## Prerequisites
- ServiceNow instance URL: `https://dev229095.service-now.com`
- Username: `aiagent_integration`
- Password: [your password]
- Incident Number: `INC0010003`
- Incident sys_id: `9dd2299dc3a53610b17971edd401314e` (resolved from number)

## Step 1: Get sys_id from Incident Number (if needed)

**Request:**
- Method: `GET`
- URL: `https://dev229095.service-now.com/api/now/table/incident`
- Query Params:
  - `sysparm_query`: `number=INC0010003`
  - `sysparm_fields`: `sys_id,number,state`
  - `sysparm_limit`: `1`
- Authorization: Basic Auth
  - Username: `aiagent_integration`
  - Password: [your password]
- Headers:
  - `Content-Type`: `application/json`
  - `Accept`: `application/json`

## Step 2: Set automated_state_flow=False (Bypass Business Rules)

**Request:**
- Method: `PATCH`
- URL: `https://dev229095.service-now.com/api/now/table/incident/9dd2299dc3a53610b17971edd401314e`
- Authorization: Basic Auth
  - Username: `aiagent_integration`
  - Password: [your password]
- Headers:
  - `Content-Type`: `application/json`
  - `Accept`: `application/json`
- Body (JSON):
```json
{
  "automated_state_flow": false
}
```

## Step 3: Resolve the Incident

**Request:**
- Method: `PATCH`
- URL: `https://dev229095.service-now.com/api/now/table/incident/9dd2299dc3a53610b17971edd401314e`
- Authorization: Basic Auth
  - Username: `aiagent_integration`
  - Password: [your password]
- Headers:
  - `Content-Type`: `application/json`
  - `Accept`: `application/json`
- Body (JSON):
```json
{
  "incident_state": "4",
  "state": "4",
  "automated_state_flow": false,
  "active": false,
  "resolved_at": "2025-11-30 17:50:44",
  "close_code": "Solution provided",
  "close_notes": "False positive detected: cpu is below warning threshold",
  "work_notes": "False positive detected: cpu is below warning threshold"
}
```

## Alternative: Try with only incident_state (not state)

If Step 3 doesn't work, try this variant:

**Request:**
- Method: `PATCH`
- URL: `https://dev229095.service-now.com/api/now/table/incident/9dd2299dc3a53610b17971edd401314e`
- Authorization: Basic Auth
- Headers:
  - `Content-Type`: `application/json`
  - `Accept`: `application/json`
- Body (JSON):
```json
{
  "incident_state": "4",
  "automated_state_flow": false,
  "active": false,
  "resolved_at": "2025-11-30 17:50:44",
  "close_code": "Solution provided",
  "close_notes": "False positive detected: cpu is below warning threshold",
  "work_notes": "False positive detected: cpu is below warning threshold"
}
```

## Alternative: Try with only state (not incident_state)

**Request:**
- Method: `PATCH`
- URL: `https://dev229095.service-now.com/api/now/table/incident/9dd2299dc3a53610b17971edd401314e`
- Authorization: Basic Auth
- Headers:
  - `Content-Type`: `application/json`
  - `Accept`: `application/json`
- Body (JSON):
```json
{
  "state": "4",
  "automated_state_flow": false,
  "active": false,
  "resolved_at": "2025-11-30 17:50:44",
  "close_code": "Solution provided",
  "close_notes": "False positive detected: cpu is below warning threshold",
  "work_notes": "False positive detected: cpu is below warning threshold"
}
```

## Expected Response

If successful, you should see:
- Status: `200 OK`
- Response body should show:
  - `incident_state`: `"4"` (or `4` as number)
  - `state`: `"4"` (or `4` as number)
  - `active`: `false`
  - `close_code`: `"Solution provided"`
  - `close_notes`: [your notes]

## Troubleshooting

If the state doesn't change:
1. Check the response body for error messages
2. Verify the `close_code` value exists in your ServiceNow instance
3. Check ACL permissions for the user account
4. Check if there are business rules preventing the transition
5. Try using `PUT` instead of `PATCH`
6. Check if `resolved_at` format is correct (may need different format)

## Notes

- Replace `9dd2299dc3a53610b17971edd401314e` with the actual sys_id from Step 1
- Update `resolved_at` timestamp to current time
- Verify `close_code` value matches your ServiceNow instance's enumeration values









