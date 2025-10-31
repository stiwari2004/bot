#!/usr/bin/env python3
import requests
import json

url = "http://host.docker.internal:8080/v1/chat/completions"
payload = {
    "model": "/Users/sandiptiwari/models/qwen2.5-1.5b/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
    "messages": [
        {"role": "system", "content": "You are a concise troubleshooting assistant."},
        {"role": "user", "content": "Generate YAML with runbook_id and title only."}
    ],
    "temperature": 0.2,
    "max_tokens": 200
}

print(f"Testing llama.cpp at {url}")
r = requests.post(url, json=payload, timeout=60)
print(f"Status: {r.status_code}")
print(f"Response keys: {list(r.json().keys())}")

data = r.json()
choices = data.get("choices") or []
if choices:
    msg = choices[0].get("message", {})
    content = msg.get("content", "")
    print(f"Content (first 500 chars): {content[:500]}")
else:
    print("No choices in response")
    print(f"Full response: {json.dumps(data, indent=2)}")

