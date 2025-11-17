#!/usr/bin/env python3
"""Test script to verify LLM connection from backend container"""
import httpx
import asyncio
import sys

async def test_connection():
    base_url = "http://host.docker.internal:8080"
    
    # Test health endpoint
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"Testing connection to {base_url}...")
            
            # Test health
            resp = await client.get(f"{base_url}/health")
            print(f"Health check: {resp.status_code} - {resp.text}")
            
            # Test models
            resp = await client.get(f"{base_url}/v1/models")
            print(f"Models endpoint: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Models found: {len(data.get('models', []))}")
                if data.get('models'):
                    model_name = data['models'][0].get('model') or data['models'][0].get('name')
                    print(f"First model: {model_name}")
            
            # Test chat completion
            payload = {
                "model": model_name if 'model_name' in locals() else "test",
                "messages": [
                    {"role": "user", "content": "Say hello in one word"}
                ],
                "max_tokens": 10
            }
            resp = await client.post(f"{base_url}/v1/chat/completions", json=payload, timeout=30.0)
            print(f"Chat completion: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Response: {data.get('choices', [{}])[0].get('message', {}).get('content', 'No content')}")
            else:
                print(f"Error: {resp.text[:200]}")
                
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(test_connection()))








