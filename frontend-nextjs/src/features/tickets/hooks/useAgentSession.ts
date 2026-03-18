/**
 * Controller hook for the agent session flow.
 * All state, API calls, and polling logic lives here.
 * Components only call actions and read state — no fetch logic in views.
 */
import { useEffect, useRef, useState } from 'react';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import type { Ticket, TicketDetail } from '@/features/tickets/types';

export type Phase = 'running' | 'approving' | 'review' | 'done';

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

interface AgentEvent {
  id?: number;
  event_type?: string;
  event?: string;
  payload?: Record<string, unknown>;
}

export interface AgentSessionState {
  phase: Phase;
  issueDescription: string;
  sessionId: number | null;
  sessionStatus: string;
  logLines: string[];
  // Plan approval
  planSteps: PlanStep[];
  planDiagnosis: PlanDiagnosis | null;
  rejectFeedback: string;
  approveLoading: boolean;
  rejectLoading: boolean;
  // Post-execution review
  steps: StepForReview[];
  weedSet: Set<number>;
  runbookTitle: string;
  agentSummary: string;
  savedRunbook: { id: number; title: string } | null;
  saveLoading: boolean;
  error: string | null;
}

export interface AgentSessionActions {
  setRunbookTitle: (v: string) => void;
  toggleWeed: (stepNumber: number) => void;
  saveRunbook: () => Promise<void>;
  stopPolling: () => void;
  // Plan approval
  updatePlanStep: (index: number, field: keyof PlanStep, value: string) => void;
  removePlanStep: (index: number) => void;
  addPlanStep: () => void;
  movePlanStep: (index: number, direction: 'up' | 'down') => void;
  setRejectFeedback: (v: string) => void;
  approvePlan: () => Promise<void>;
  rejectPlan: () => Promise<void>;
}

const POLL_INTERVAL_MS = 2000;
const MAX_OUTPUT_CHARS = 200;

function formatEvent(evt: AgentEvent): string {
  const p = evt.payload || {};
  const type = (p.event_type as string) || evt.event_type || evt.event || '';

  if (type === 'agent.started')           return `[START] ${p.message || 'Agent started'}`;
  if (type === 'agent.reasoning')         return `[STEP ${p.step_number}] ${p.reasoning}\n         $ ${p.command}  [${p.safety_label}]`;
  if (type === 'agent.diagnose_step')     return `[DIAGNOSE ${p.step_number}] $ ${p.command}`;
  if (type === 'agent.step_completed')    return `[STEP ${p.step_number}] ${p.success ? '✓' : '✗'} ${(p.output_preview as string || '').slice(0, MAX_OUTPUT_CHARS)}`;
  if (type === 'agent.caution')           return `[CAUTION] ${p.message || p.reason}`;
  if (type === 'agent.approval_required') return `[APPROVAL NEEDED] ${p.message || ''}\nPreview:\n${p.dry_run_output || ''}`;
  if (type === 'agent.command_blocked')   return `[BLOCKED] ${p.command} — ${p.reason}`;
  if (type === 'agent.plan_ready')        return `[PLAN READY] Diagnosis complete — review and approve the plan to proceed.`;
  if (type === 'agent.plan_revised')      return `[PLAN REVISED] Agent updated the plan based on your feedback — please review.`;
  if (type === 'agent.completed')         return `[DONE] ${p.summary || 'Agent finished.'}`;
  if (type === 'agent.error')             return `[ERROR] ${p.message}`;
  if (type === 'execution.step.started')  return `[STEP ${p.step_number}] $ ${p.command || ''}`;
  if (type === 'execution.step.output')   return `       ${(p.output as string || '').slice(0, MAX_OUTPUT_CHARS)}`;
  return '';
}

export function useAgentSession(ticket: TicketDetail | Ticket | null): [AgentSessionState, AgentSessionActions] {
  const [phase, setPhase] = useState<Phase>('running');
  const [issueDescription, setIssueDescription] = useState('');
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [sessionStatus, setSessionStatus] = useState('');
  const [logLines, setLogLines] = useState<string[]>([]);

  // Plan approval state
  const [planSteps, setPlanSteps] = useState<PlanStep[]>([]);
  const [planDiagnosis, setPlanDiagnosis] = useState<PlanDiagnosis | null>(null);
  const [rejectFeedback, setRejectFeedback] = useState('');
  const [approveLoading, setApproveLoading] = useState(false);
  const [rejectLoading, setRejectLoading] = useState(false);

  // Post-execution review state
  const [steps, setSteps] = useState<StepForReview[]>([]);
  const [weedSet, setWeedSet] = useState<Set<number>>(new Set());
  const [runbookTitle, setRunbookTitle] = useState('');
  const [agentSummary, setAgentSummary] = useState('');
  const [savedRunbook, setSavedRunbook] = useState<{ id: number; title: string } | null>(null);
  const [saveLoading, setSaveLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastEventIdRef = useRef<number>(0);
  const hasStartedRef = useRef(false);
  const inApprovalRef = useRef(false);

  // Auto-start when ticket arrives
  useEffect(() => {
    if (!ticket || hasStartedRef.current) return;
    const desc = `${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}`;
    setIssueDescription(desc);
    if (desc.trim()) {
      hasStartedRef.current = true;
      void doStartAgent(desc, ticket.id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket]);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  // ── Start agent ─────────────────────────────────────────────────────────────
  const doStartAgent = async (desc: string, ticketId?: number) => {
    setError(null);
    setLogLines([]);

    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessions(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          issue_description: desc,
          ticket_id: ticketId ?? undefined,
          tenant_id: 1,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || `Failed to start agent (${res.status})`);
      }
      const data = await res.json();
      const sid: number = data.session_id;
      setSessionId(sid);
      setLogLines([`Agent session #${sid} started.`, 'Connecting to target system…']);
      startPolling(sid);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start agent session');
    }
  };

  // ── Polling ─────────────────────────────────────────────────────────────────
  const startPolling = (sid: number) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => pollEvents(sid), POLL_INTERVAL_MS);
  };

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  const pollEvents = async (sid: number) => {
    try {
      const eventsUrl = `${apiConfig.endpoints.executions.agentSessionEvents(sid)}?since_id=${lastEventIdRef.current}&limit=50`;
      const evRes = await authFetch(eventsUrl);
      if (evRes.ok) {
        const evData = await evRes.json();
        const events: AgentEvent[] = Array.isArray(evData) ? evData : (evData.events || []);
        if (events.length > 0) {
          const newLines: string[] = [];
          for (const evt of events) {
            if (evt.id && evt.id > lastEventIdRef.current) lastEventIdRef.current = evt.id;
            const line = formatEvent(evt);
            if (line) newLines.push(line);
          }
          if (newLines.length) setLogLines(prev => [...prev, ...newLines]);
        }
      }

      const sessRes = await authFetch(apiConfig.endpoints.executions.agentSessionDetail(sid));
      if (sessRes.ok) {
        const sess = await sessRes.json();
        const status: string = sess.status || '';
        setSessionStatus(status);

        if (status === 'awaiting_plan_approval' && !inApprovalRef.current) {
          inApprovalRef.current = true;
          await loadPlanForApproval(sid);
        } else if (['completed', 'completed_with_errors', 'failed'].includes(status)) {
          stopPolling();
          await loadStepsForReview(sid);
        } else if (status === 'abandoned') {
          stopPolling();
          setError('Agent session was abandoned.');
        }
      }
    } catch {
      // polling errors are non-fatal
    }
  };

  // ── Load plan for approval ────────────────────────────────────────────────
  const loadPlanForApproval = async (sid: number) => {
    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessionPlan(sid));
      if (!res.ok) throw new Error('Failed to load plan');
      const data = await res.json();
      const steps: PlanStep[] = (data.proposed_plan || []).map((s: PlanStep, i: number) => ({
        step: s.step ?? (i + 1),
        intent: s.intent ?? '',
        command: s.command ?? '',
        risk: s.risk ?? 'medium',
      }));
      setPlanSteps(steps);
      setPlanDiagnosis(data.diagnosis || null);
      setPhase('approving');
    } catch {
      setLogLines(prev => [...prev, '[PLAN] Failed to load plan — try refreshing.']);
    }
  };

  // ── Plan approval actions ─────────────────────────────────────────────────
  const updatePlanStep = (index: number, field: keyof PlanStep, value: string) => {
    setPlanSteps(prev => prev.map((s, i) => i === index ? { ...s, [field]: value } : s));
  };

  const removePlanStep = (index: number) => {
    setPlanSteps(prev =>
      prev.filter((_, i) => i !== index).map((s, i) => ({ ...s, step: i + 1 }))
    );
  };

  const addPlanStep = () => {
    setPlanSteps(prev => [...prev, { step: prev.length + 1, intent: '', command: '', risk: 'medium' }]);
  };

  const movePlanStep = (index: number, direction: 'up' | 'down') => {
    setPlanSteps(prev => {
      const next = [...prev];
      const swapIdx = direction === 'up' ? index - 1 : index + 1;
      if (swapIdx < 0 || swapIdx >= next.length) return prev;
      [next[index], next[swapIdx]] = [next[swapIdx], next[index]];
      return next.map((s, i) => ({ ...s, step: i + 1 }));
    });
  };

  const approvePlan = async () => {
    if (!sessionId) return;
    setApproveLoading(true);
    setError(null);
    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessionPlanApprove(sessionId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposed_plan: planSteps }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || 'Failed to approve plan');
      }
      inApprovalRef.current = false;
      setPhase('running');
      setLogLines(prev => [...prev, '[APPROVED] Plan approved — agent is now executing…']);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve plan');
    } finally {
      setApproveLoading(false);
    }
  };

  const rejectPlan = async () => {
    if (!sessionId || !rejectFeedback.trim()) return;
    setRejectLoading(true);
    setError(null);
    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessionPlanReject(sessionId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: rejectFeedback }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || 'Failed to reject plan');
      }
      inApprovalRef.current = false;
      setRejectFeedback('');
      setPhase('running');
      setLogLines(prev => [...prev, '[REJECTED] Feedback sent — agent is re-planning…']);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject plan');
    } finally {
      setRejectLoading(false);
    }
  };

  // ── Load review steps ────────────────────────────────────────────────────────
  const loadStepsForReview = async (sid: number) => {
    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessionStepReview(sid));
      if (!res.ok) throw new Error('Failed to load step review');
      const data = await res.json();
      const stepList: StepForReview[] = data.steps || [];
      setSteps(stepList);
      setAgentSummary(data.agent_summary || '');
      setWeedSet(new Set(stepList.filter(s => s.suggested_weed).map(s => s.step_number)));
      setRunbookTitle(`Auto: ${issueDescription.slice(0, 60).replace(/\n/g, ' ')}`);
      setPhase('review');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load review');
    }
  };

  // ── Save runbook ─────────────────────────────────────────────────────────────
  const saveRunbook = async () => {
    if (!sessionId) return;
    setSaveLoading(true);
    setError(null);
    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessionReview(sessionId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          weed_step_numbers: Array.from(weedSet),
          save_as_runbook: true,
          runbook_title: runbookTitle.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || 'Failed to save runbook');
      }
      const result = await res.json();
      setSavedRunbook({ id: result.runbook_id, title: result.runbook_title });
      setPhase('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save runbook');
    } finally {
      setSaveLoading(false);
    }
  };

  const toggleWeed = (stepNumber: number) => {
    setWeedSet(prev => {
      const next = new Set(prev);
      next.has(stepNumber) ? next.delete(stepNumber) : next.add(stepNumber);
      return next;
    });
  };

  const state: AgentSessionState = {
    phase, issueDescription, sessionId, sessionStatus,
    logLines,
    planSteps, planDiagnosis, rejectFeedback, approveLoading, rejectLoading,
    steps, weedSet, runbookTitle, agentSummary,
    savedRunbook, saveLoading, error,
  };

  const actions: AgentSessionActions = {
    setRunbookTitle, toggleWeed, saveRunbook, stopPolling,
    updatePlanStep, removePlanStep, addPlanStep, movePlanStep,
    setRejectFeedback, approvePlan, rejectPlan,
  };

  return [state, actions];
}
