# Ready-to-Use Prompt for ChatGPT/Claude Testing

**Issue with your previous ChatGPT response:** Missing dashes (`-`) before list items in YAML.

---

## Test This Improved Prompt:

**SYSTEM:**
```
You are a YAML generator for agent-executable troubleshooting runbooks. Return ONLY valid YAML. No markdown, no code fences. Remember: In YAML, list items MUST start with a dash and space ('- '). Without dashes, YAML parsers will fail.
```

**USER:**
```
Generate a COMPREHENSIVE troubleshooting runbook YAML with 8-12 diagnostic and resolution steps.

Issue: server is running slow and users are complaining of timeouts
Service: server, Environment: prod, Risk: low

Context (knowledge snippets):
Server performance issues typically involve high CPU usage, memory exhaustion, or I/O bottlenecks. 
Check system metrics (top, htop, iostat), identify runaway processes, review system logs (/var/log/messages), 
check disk space (df -h), and consider service restarts if necessary. Monitor network connectivity and database connections.
Timeout issues may indicate resource exhaustion, network latency, or database query problems.

YAML structure (copy this FORMAT EXACTLY - note the DASH at start of each list item):
runbook_id: rb-server-issue
version: 1.0.0
title: Fix [Issue Name Here]
service: server
env: prod
risk: low
description: Brief description without quotes
inputs:
- name: server_name
  type: string
  required: true
  description: Target server hostname or IP
- name: service_name
  type: string
  required: false
  description: Affected service name (optional)
prechecks:
- description: Check server is reachable via ping
  command: ping -c 2 {server_name}
  expected_output: "0% packet loss"
steps:
- name: Check CPU usage
  type: command
  command: top -b -n 1 | head -n 20
  expected_output: CPU usage and top processes
- name: Check memory usage
  type: command
  command: free -h
  expected_output: memory statistics
[ADD 6-10 MORE RELEVANT STEPS HERE: disk I/O, network, logs, processes, etc.]
postchecks:
- description: Verify server responsiveness
  command: uptime
  expected_output: system responsive
- description: Verify no critical errors
  command: tail -n 20 /var/log/messages
  expected_output: no critical errors

CRITICAL FORMATTING RULES:
1. Output ONLY raw YAML; no backticks, no markdown code fences.
2. EVERY list item MUST start with a dash and space: "- " (this is MANDATORY for YAML lists)
3. WRONG: "name: value" without dash. RIGHT: "- name: value" with dash
4. Indent list items 2 spaces under their parent key (inputs, prechecks, steps, postchecks).
5. Include 8-12 total steps based on the issue context.
6. Make steps relevant and specific to the problem.
7. Use {variable} syntax for input references in commands.

EXAMPLE OF CORRECT FORMAT:
inputs:
- name: server_name
  type: string
  required: true
  description: Target server

EXAMPLE OF WRONG FORMAT (DO NOT USE):
inputs:
name: server_name
type: string
```

---

## Use test_prompt.py to generate variations:

```bash
python3 test_prompt.py
```

This shows the exact prompt your backend will send to the LLM.

