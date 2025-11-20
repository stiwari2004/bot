#!/usr/bin/env python3
"""Test script to verify LLM connection from backend container"""
import httpx
import asyncio
import sys

async def test_connection():
    base_url = "http://host.docker.internal:11434"
    
    # Test Ollama connection
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"Testing Ollama connection to {base_url}...")
            
            # Test Ollama API (list models)
            resp = await client.get(f"{base_url}/api/tags")
            print(f"Ollama API check: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get('models', [])
                print(f"Models found: {len(models)}")
                if models:
                    model_name = models[0].get('name', '')
                    print(f"First model: {model_name}")
            
            # Test OpenAI-compatible models endpoint
            resp = await client.get(f"{base_url}/v1/models")
            print(f"Models endpoint: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Models found: {len(data.get('models', []))}")
                if data.get('models'):
                    model_name = data['models'][0].get('model') or data['models'][0].get('name')
                    print(f"First model: {model_name}")
            
            # Test chat completion (use llama3.2 or first available model)
            model_to_use = model_name if 'model_name' in locals() and model_name else "llama3.2"
            payload = {
                "model": model_to_use,
                "messages": [
                    {"role": "user", "content": "Say hello in one word"}
                ],
                "max_tokens": 10
            }
            print(f"Testing chat completion with model: {model_to_use}")
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








