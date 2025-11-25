"""
Test script to see what YAML the LLM is generating that causes the newline error
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import get_llm_service
from app.services.runbook.generation.yaml_processor import YamlProcessor
import yaml

async def test_yaml_generation():
    """Test what YAML is being generated"""
    issue_description = "We are experiencing high CPU utilization on our Windows server InfraBotTestVM1"
    service = "auto"
    env = "Windows"
    risk = "low"
    
    print("=" * 80)
    print("TESTING YAML GENERATION")
    print("=" * 80)
    print(f"Issue: {issue_description}")
    print(f"Service: {service}, Env: {env}, Risk: {risk}")
    print()
    
    # Get LLM service
    llm_service = get_llm_service()
    
    # Get context (simplified)
    from app.services.runbook.generation.content_builder import ContentBuilder
    content_builder = ContentBuilder()
    context_str = content_builder.build_context(service_type=service, tenant_id=1, db=None)
    
    print("Calling LLM to generate YAML...")
    print()
    
    # Generate YAML
    ai_yaml = await llm_service.generate_yaml_runbook(
        tenant_id=1,
        issue_description=issue_description,
        service_type=service,
        env=env,
        risk=risk,
        context=context_str,
    )
    
    print("=" * 80)
    print("RAW YAML FROM LLM (first 500 chars):")
    print("=" * 80)
    print(repr(ai_yaml[:500]))
    print()
    
    print("=" * 80)
    print("RAW YAML FROM LLM (first 500 chars, readable):")
    print("=" * 80)
    print(ai_yaml[:500])
    print()
    
    # Check for newlines in first 200 chars
    print("=" * 80)
    print("CHECKING FOR NEWLINES IN FIRST 200 CHARS:")
    print("=" * 80)
    first_200 = ai_yaml[:200]
    for i, char in enumerate(first_200):
        if char == '\n':
            print(f"Found newline at position {i}: {repr(first_200[max(0, i-20):i+20])}")
    print()
    
    # Check first line specifically
    first_line = ai_yaml.split('\n')[0] if '\n' in ai_yaml else ai_yaml
    print("=" * 80)
    print(f"FIRST LINE (length: {len(first_line)}):")
    print("=" * 80)
    print(repr(first_line))
    print()
    
    if len(first_line) >= 101:
        print(f"Character at column 101: {repr(first_line[100])}")
        print(f"Context around column 101: {repr(first_line[90:110])}")
    print()
    
    # Try processing with yaml_processor
    print("=" * 80)
    print("PROCESSING WITH YAML PROCESSOR:")
    print("=" * 80)
    processor = YamlProcessor()
    try:
        processed = processor.sanitize_command_strings(ai_yaml)
        print("Processing successful")
        print(f"Processed YAML first 500 chars: {repr(processed[:500])}")
    except Exception as e:
        print(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Try parsing
    print("=" * 80)
    print("ATTEMPTING YAML PARSE:")
    print("=" * 80)
    try:
        spec = yaml.safe_load(ai_yaml)
        print("Parse successful!")
    except Exception as e:
        print(f"Parse failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_yaml_generation())



