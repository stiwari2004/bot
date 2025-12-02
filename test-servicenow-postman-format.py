"""
Test ServiceNow API with exact Postman format
This will help us see what Postman is actually sending

CRITICAL: HTTP Basic Auth REQUIRES base64 encoding!
Format: Basic <base64-encoded-username:password>
"""
import requests
import base64

# Your credentials
USERNAME = "bot-integration"  # Note: user said "bot_integration" but should be "bot-integration"?
PASSWORD = input("Enter password: ")

# ServiceNow instance
INSTANCE_URL = "https://dev229095.service-now.com"
API_URL = f"{INSTANCE_URL}/api/now/table/incident"

# Method 1: Using requests with auth parameter (like Postman Basic Auth)
print("\n=== Method 1: Using requests.auth.HTTPBasicAuth ===")
response1 = requests.get(
    API_URL,
    auth=(USERNAME, PASSWORD),
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json"
    },
    params={
        "sysparm_limit": 10
    }
)
print(f"Status: {response1.status_code}")
print(f"Response: {response1.text[:200]}")
if response1.status_code == 200:
    print("✅ SUCCESS with requests.auth!")
else:
    print("❌ FAILED")

# Method 2: Manual Authorization header (base64 encoded)
print("\n=== Method 2: Manual Authorization header (base64) ===")
credentials = f"{USERNAME}:{PASSWORD}"
encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
auth_header = f"Basic {encoded}"

print(f"Credentials string: {credentials[:20]}...")
print(f"Base64 encoded: {encoded[:50]}...")
print(f"Authorization header: {auth_header[:50]}...")

response2 = requests.get(
    API_URL,
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": auth_header
    },
    params={
        "sysparm_limit": 10
    }
)
print(f"Status: {response2.status_code}")
print(f"Response: {response2.text[:200]}")
if response2.status_code == 200:
    print("✅ SUCCESS with manual header!")
else:
    print("❌ FAILED")

# Method 3: Plain text (what you showed - this won't work)
print("\n=== Method 3: Plain text (this should FAIL) ===")
plain_header = f"Basic {USERNAME}:{PASSWORD}"
response3 = requests.get(
    API_URL,
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": plain_header
    },
    params={
        "sysparm_limit": 10
    }
)
print(f"Status: {response3.status_code}")
print(f"Response: {response3.text[:200]}")
if response3.status_code == 200:
    print("✅ SUCCESS (unexpected!)")
else:
    print("❌ FAILED (expected)")

print("\n=== Summary ===")
print("If Method 1 or 2 works, the code should work too.")
print("If all methods fail, it's a ServiceNow account/permissions issue.")

