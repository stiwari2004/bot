/**
 * Controller hook for the agent session flow.
 * All state, API calls, and polling logic lives here.
 * Components only call actions and read state — no fetch logic in views.
 */
import { useEffect, useRef, useState } from 'react';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import type { Ticket, TicketDetail } from '@/features/tickets/types';

export type Phase = 'setup' | 'approving' | 'review' | 'done';

export interface StepForReview {
  step_number: number;
  command: string;
  reasoning: string;
  output: string;
  error: string;
  success: boolean;
  safety_level: number;
  safety_label: string;
  suggested_weed: boolean;
}

export interface PlanStep {
  step: number;
  intent: string;
  command: string;
  risk: string;
}

export interface PlanDiagnosis {
  root_cause: string;
  evidence: string[];
  confidence: string;
}

export interface AgentSessionState {
  phase: Phase;
  issueDescription: string;
  sessionId: number | null;
  starting: boolean;
  error: string | null;
}

export interface AgentSessionActions {
  setIssueDescription: (v: string) => void;
  startAgent: (e: React.FormEvent) => Promise<void>;
}

export function useAgentSession(
  ticket: TicketDetail | Ticket | null,
  onAgentStarted?: (sessionId: number) => void
): [AgentSessionState, AgentSessionActions] {
  const [phase, setPhase] = useState<Phase>('setup');
  const [issueDescription, setIssueDescription] = useState('');
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticket) return;
    setIssueDescription(`${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}`);
  }, [ticket]);

  const startAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueDescription.trim()) return;
    setError(null);
    setStarting(true);
    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessions(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          issue_description: issueDescription,
          ticket_id: (ticket as any)?.id ?? undefined,
          tenant_id: 1,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as any)?.detail || `Failed to start agent (${res.status})`);
      }
      const data = await res.json();
      setSessionId(data.session_id);
      if (onAgentStarted) {
        onAgentStarted(data.session_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start agent session');
    } finally {
      setStarting(false);
    }
  };

  const state: AgentSessionState = {
    phase, issueDescription, sessionId, starting, error,
  };

  const actions: AgentSessionActions = {
    setIssueDescription, startAgent,
  };

  return [state, actions];
}
