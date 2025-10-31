#!/usr/bin/env python3
"""Quick script to render prompt templates for testing in ChatGPT/Claude."""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.services.prompt_store import render_prompt

# Example test case
example_vars = {
    "issue_description": "server is running slow and users are complaining of timeouts",
    "service": "server",
    "env": "prod",
    "risk": "low",
    "context": """Server performance issues typically involve high CPU usage, memory exhaustion, or I/O bottlenecks. 
Check system metrics (top, htop, iostat), identify runaway processes, review system logs (/var/log/messages), 
check disk space (df -h), and consider service restarts if necessary. Monitor network connectivity and database connections.
Timeout issues may indicate resource exhaustion, network latency, or database query problems.""",
}

print("=" * 80)
print("SYSTEM MESSAGE:")
print("=" * 80)
rendered = render_prompt("runbook_yaml_v1", example_vars)
print(rendered["system"])
print("\n")

print("=" * 80)
print("USER MESSAGE:")
print("=" * 80)
print(rendered["user"])
print("\n")

print("=" * 80)
print("COPY ABOVE TO CHATGPT/CLAUDE AND TEST!")
print("=" * 80)

