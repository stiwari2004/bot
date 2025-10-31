# Delivery Phases and Operating Modes

This document keeps the team focused on the current phase and outlines the next steps.

## Phase 1: Assistant (Draft Runbook Creation)
- Trigger: Monitoring event or user-reported incident.
- Behavior:
  - RAG retrieval from vector store (pgvector) using issue description.
  - LLM (provider-agnostic; POC: local llama.cpp) generates an agent-executable YAML runbook following the standard schema.
  - YAML is validated and stored as a draft runbook with confidence score and citations/metadata.
- Output: Draft runbook for human review and manual execution guidance.

## Phase 2: Human-in-the-Loop (Review & Approval)
- Review draft, edit as needed, and approve.
- On approval, runbook is versioned and marked active.
- Track changes and approvals in audit trail.

## Phase 3: Autonomous Bot (Execute & Iterate)
- Execute approved runbooks automatically with guardrails.
- Capture outputs, timings, and status; perform rollbacks if needed.
- On failure or low confidence, escalate to human.
- Feed successful executions back into knowledge base to improve future drafts.

## Provider Abstraction
- POC: llama.cpp local server (OpenAI-compatible API).
- Future: Switch to other providers (OpenAI, Claude, etc.) via configuration only.

## Current Focus
- Complete and validate Phase 1 end-to-end: high-quality AI-generated YAML runbooks using RAG context, stored as drafts with metadata.

