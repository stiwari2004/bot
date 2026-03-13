-- Add meta_data JSON column to execution_sessions for agent session metadata
-- (agent_session flag, pending_review, agent_summary, resolved_inputs, etc.)

ALTER TABLE execution_sessions
    ADD COLUMN IF NOT EXISTS meta_data JSON;
