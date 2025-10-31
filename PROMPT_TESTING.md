# Prompt Testing Guide

## Current Prompt Templates

### System Message
```
You are a YAML generator for agent-executable troubleshooting runbooks. Return ONLY valid YAML. No markdown, no code fences.
```

### User Message Template
```
Generate a troubleshooting runbook YAML.

Issue: {issue_description}
Service: {service}, Environment: {env}, Risk: {risk}

Context (knowledge snippets):
{context}

YAML structure (copy exactly; lists must start with '- '):
runbook_id: rb-{service}-issue
version: 1.0.0
title: Fix [Issue]
service: {service}
env: {env}
risk: {risk}
description: Brief description without quotes
inputs:
- name: server_name
  type: string
  required: true
  description: Target server
prechecks:
- description: Basic health check
  command: uptime
  expected_output: load averages present
steps:
- name: Check CPU
  type: command
  command: top -b -n 1 | head -n 20
  expected_output: process list
- name: Check Memory
  type: command
  command: free -h
  expected_output: memory stats
postchecks:
- description: Verify resolution
  command: uptime
  expected_output: system responsive

IMPORTANT: Output ONLY raw YAML; no backticks, no markdown.
```

## Example Test Case

### Variables:
- **issue_description**: `server is running slow and users are complaining of timeouts`
- **service**: `server`
- **env**: `prod`
- **risk**: `low`
- **context**: `Server performance issues typically involve high CPU usage, memory exhaustion, or I/O bottlenecks. Check system metrics, identify runaway processes, and consider service restarts.`

### Full Prompt for ChatGPT:

**System Message:**
```
You are a YAML generator for agent-executable troubleshooting runbooks. Return ONLY valid YAML. No markdown, no code fences.
```

**User Message:**
```
Generate a troubleshooting runbook YAML.

Issue: server is running slow and users are complaining of timeouts
Service: server, Environment: prod, Risk: low

Context (knowledge snippets):
Server performance issues typically involve high CPU usage, memory exhaustion, or I/O bottlenecks. Check system metrics, identify runaway processes, and consider service restarts.

YAML structure (copy exactly; lists must start with '- '):
runbook_id: rb-server-issue
version: 1.0.0
title: Fix [Issue]
service: server
env: prod
risk: low
description: Brief description without quotes
inputs:
- name: server_name
  type: string
  required: true
  description: Target server
prechecks:
- description: Basic health check
  command: uptime
  expected_output: load averages present
steps:
- name: Check CPU
  type: command
  command: top -b -n 1 | head -n 20
  expected_output: process list
- name: Check Memory
  type: command
  command: free -h
  expected_output: memory stats
postchecks:
- description: Verify resolution
  command: uptime
  expected_output: system responsive

IMPORTANT: Output ONLY raw YAML; no backticks, no markdown.
```

## What to Look For in Responses

1. **Complete troubleshooting steps**: Should have 5-10+ steps covering diagnosis, resolution, verification
2. **Proper YAML format**: All lists (inputs, steps, postchecks) must start with `- `
3. **No markdown**: Should start directly with `runbook_id:` not `` ```yaml ``
4. **Relevant commands**: Steps should be specific to the issue (e.g., CPU/memory for slow server)
5. **Inputs match usage**: Input parameters should be referenced in steps with `{{variable}}`
6. **Prechecks and postchecks**: Should include validation before and after

## Feedback Format

When you test, note:
- ✅ What works well
- ❌ What's missing (e.g., "Only 3 steps, need more diagnostic steps")
- 🔧 What to change (e.g., "Add more network-related checks for timeout issues")

Then we'll iterate on the prompt!

