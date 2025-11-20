#!/usr/bin/env python3
"""Test LLM connection directly"""
import asyncio
import sys
sys.path.insert(0, 'backend')

from app.services.llm_service import get_llm_service

async def test_llm():
    print("Testing LLM connection...")
    llm = get_llm_service()
    
    print(f"Base URL: {llm.base_url}")
    print(f"Model ID: {await llm._ensure_model_id()}")
    
    print("\nTesting simple chat...")
    result = await llm._chat_once_with_system(
        "You are a helpful assistant.",
        "Say hello in one sentence."
    )
    print(f"Result: {repr(result)}")
    print(f"Length: {len(result) if result else 0}")
    print(f"Has content: {bool(result and result.strip())}")
    
    if not result or not result.strip():
        print("\nERROR: Empty response!")
        return 1
    
    print("\nTesting YAML generation...")
    yaml_result = await llm.generate_yaml_runbook(
        tenant_id=1,
        issue_description="High CPU usage on server",
        service_type="server",
        env="prod",
        risk="low",
        context=""
    )
    print(f"YAML Result length: {len(yaml_result) if yaml_result else 0}")
    print(f"YAML Has content: {bool(yaml_result and yaml_result.strip())}")
    if yaml_result:
        print(f"YAML Preview: {yaml_result[:200]}")
    
    if not yaml_result or not yaml_result.strip():
        print("\nERROR: Empty YAML response!")
        return 1
    
    print("\nSUCCESS: LLM is working!")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(test_llm())
    sys.exit(exit_code)

