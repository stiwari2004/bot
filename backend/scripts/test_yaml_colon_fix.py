#!/usr/bin/env python3
"""
Test YAML colon fix for expected_output values ending with colon
"""
import sys
import os
import yaml

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.runbook.generation.yaml_processor import YamlProcessor
from app.core.logging import get_logger

logger = get_logger(__name__)


def test_colon_fix():
    """Test that expected_output values ending with colon are quoted"""
    
    # Simulate problematic YAML from LLM
    problematic_yaml = """runbook_id: rb-test
version: 1.0.0
title: Test Runbook
service: network
env: prod
risk: low
description: Test

inputs:
  - name: host_ip
    type: string
    required: true
    description: Host IP

prechecks:
  - description: Check DNS
    command: nslookup google.com
    expected_output: Address:
  - description: Check ping
    command: ping -c 4 8.8.8.8
    expected_output: 0% packet loss
  - description: Check interface
    command: ip addr show eth0
    expected_output: inet

steps:
  - name: Step 1
    step_number: 1
    type: command
    command: echo test
    expected_output: test:
    purpose: diagnose
    severity: safe

postchecks:
  - description: Final check
    command: echo done
    expected_output: done:
"""
    
    print("\n" + "="*80)
    print("TESTING YAML COLON FIX")
    print("="*80)
    
    print("\nBEFORE FIX:")
    print("Problematic lines:")
    for i, line in enumerate(problematic_yaml.split('\n'), 1):
        if 'expected_output:' in line and ':' in line.split('expected_output:')[1].strip() and not line.strip().endswith('"'):
            print(f"  Line {i}: {line}")
    
    # Try to parse - should fail
    try:
        yaml.safe_load(problematic_yaml)
        print("\n⚠️  YAML parsed without errors (unexpected!)")
    except yaml.YAMLError as e:
        print(f"\n❌ YAML parse error (expected): {e}")
    
    # Apply fix
    print("\n[STEP 1] Applying sanitize_expected_output_field fix...")
    processor = YamlProcessor()
    fixed_yaml = processor.sanitize_expected_output_field(problematic_yaml)
    
    print("\nAFTER FIX:")
    print("Fixed lines:")
    for i, (before, after) in enumerate(zip(problematic_yaml.split('\n'), fixed_yaml.split('\n')), 1):
        if before != after:
            print(f"  Line {i}:")
            print(f"    Before: {before}")
            print(f"    After:  {after}")
    
    # Try to parse fixed YAML - should succeed
    print("\n[STEP 2] Testing if fixed YAML parses correctly...")
    try:
        spec = yaml.safe_load(fixed_yaml)
        print("✅ YAML parsed successfully!")
        
        # Check if values are quoted
        prechecks = spec.get("prechecks", [])
        steps = spec.get("steps", [])
        
        print("\nChecking prechecks:")
        for i, precheck in enumerate(prechecks, 1):
            if isinstance(precheck, dict):
                expected = precheck.get("expected_output", "")
                print(f"  Precheck {i}: expected_output = {repr(expected)}")
        
        print("\nChecking steps:")
        for i, step in enumerate(steps, 1):
            if isinstance(step, dict):
                expected = step.get("expected_output", "")
                print(f"  Step {i}: expected_output = {repr(expected)}")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ YAML still has parse errors: {e}")
        return False


if __name__ == "__main__":
    try:
        success = test_colon_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




