'use client';

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon, CheckCircleIcon, TrashIcon } from '@heroicons/react/24/outline';

import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';
import type { Ticket, TicketDetail } from '@/features/tickets/types';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface GenerateRunbookModalProps {
  ticket: TicketDetail | Ticket | null;
  onClose: () => void;
}

type Phase = 'setup' | 'running' | 'review' | 'done';

interface AgentEvent {
  id?: number;
  event_type?: string;
  event?: string;
  payload?: Record<string, unknown>;
  created_at?: string;
}

interface StepForReview {
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

const SAFETY_COLORS: Record<number, string> = {
  1: 'text-green-700 bg-green-50 border-green-200',
  2: 'text-amber-700 bg-amber-50 border-amber-200',
  3: 'text-orange-700 bg-orange-50 border-orange-200',
  4: 'text-red-700 bg-red-50 border-red-200',
};

export function GenerateRunbookModal({ ticket, onClose }: GenerateRunbookModalProps) {
  const [issueDescription, setIssueDescription] = useState(
    ticket ? `${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}` : ''
  );
  const [phase, setPhase] = useState<Phase>('setup');
  const [error, setError] = useState<string | null>(null);

  // Running phase
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [sessionStatus, setSessionStatus] = useState<string>('');
  const logEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastEventIdRef = useRef<number>(0);

  // Review phase
  const [steps, setSteps] = useState<StepForReview[]>([]);
  const [weedSet, setWeedSet] = useState<Set<number>>(new Set());
  const [runbookTitle, setRunbookTitle] = useState('');
  const [agentSummary, setAgentSummary] = useState('');
  const [saveLoading, setSaveLoading] = useState(false);

  // Done phase
  const [savedRunbook, setSavedRunbook] = useState<{ id: number; title: string } | null>(null);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = 'unset'; };
  }, []);

  useEffect(() => {
    if (!ticket) return;
    setIssueDescription(
      `${ticket.title}${ticket.description ? '\n\n' + ticket.description : ''}`
    );
  }, [ticket]);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logLines]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  // ── Phase: start agent ──────────────────────────────────────────────────────
  const handleStartAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueDescription.trim()) return;

    setError(null);
    setLogLines([]);
    setPhase('running');

    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessions(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          issue_description: issueDescription,
          ticket_id: ticket?.id ?? undefined,
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
      setLogLines([`Agent session #${sid} started.`, 'Connecting to target system...']);

      // Start polling events
      startPolling(sid);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start agent session');
      setPhase('setup');
    }
  };

  // ── Event polling ───────────────────────────────────────────────────────────
  const startPolling = (sid: number) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => pollEvents(sid), 2000);
  };

  const pollEvents = async (sid: number) => {
    try {
      const url = `${apiConfig.endpoints.executions.agentSessionEvents(sid)}?since_id=${lastEventIdRef.current}&limit=50`;
      const res = await authFetch(url);
      if (!res.ok) return;

      const data = await res.json();
      const events: AgentEvent[] = Array.isArray(data) ? data : (data.events || []);

      if (events.length > 0) {
        const newLines: string[] = [];
        for (const evt of events) {
          if (evt.id && evt.id > lastEventIdRef.current) {
            lastEventIdRef.current = evt.id;
          }
          const line = formatEvent(evt);
          if (line) newLines.push(line);
        }
        if (newLines.length) {
          setLogLines(prev => [...prev, ...newLines]);
        }
      }

      // Check session status
      const sessionRes = await authFetch(apiConfig.endpoints.executions.agentSessionDetail(sid));
      if (sessionRes.ok) {
        const session = await sessionRes.json();
        const status: string = session.status || '';
        setSessionStatus(status);

        if (status === 'completed' || status === 'completed_with_errors' || status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current);
          await loadStepsForReview(sid);
        } else if (status === 'abandoned') {
          if (pollRef.current) clearInterval(pollRef.current);
          setError('Agent session was abandoned.');
          setPhase('setup');
        }
      }
    } catch {
      // polling errors are non-fatal
    }
  };

  const formatEvent = (evt: AgentEvent): string => {
    const p = evt.payload || {};
    const type = (p.event_type as string) || evt.event_type || evt.event || '';

    if (type === 'agent.started') return `[START] ${p.message || 'Agent started'}`;
    if (type === 'agent.reasoning') {
      return `[STEP ${p.step_number}] Reasoning: ${p.reasoning}\n         $ ${p.command}  [${p.safety_label}]`;
    }
    if (type === 'agent.step_completed') {
      const ok = p.success ? '✓' : '✗';
      return `[STEP ${p.step_number}] ${ok} ${p.output_preview || ''}`;
    }
    if (type === 'agent.caution') {
      return `[CAUTION] ${p.message || p.reason}`;
    }
    if (type === 'agent.approval_required') {
      return `[APPROVAL NEEDED] ${p.message || ''}\nPreview:\n${p.dry_run_output || ''}`;
    }
    if (type === 'agent.command_blocked') {
      return `[BLOCKED] ${p.command} — ${p.reason}`;
    }
    if (type === 'agent.completed') {
      return `[DONE] ${p.summary || 'Agent finished.'}`;
    }
    if (type === 'agent.error') return `[ERROR] ${p.message}`;

    // Generic fallback for execution events
    if (type === 'execution.step.started') return `[STEP ${p.step_number}] Started: ${p.command || ''}`;
    if (type === 'execution.step.output') return `       ${p.output || ''}`.substring(0, 200);
    return '';
  };

  // ── Load steps for review ───────────────────────────────────────────────────
  const loadStepsForReview = async (sid: number) => {
    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessionStepReview(sid));
      if (!res.ok) throw new Error('Failed to load step review');
      const data = await res.json();

      const stepList: StepForReview[] = data.steps || [];
      setSteps(stepList);
      setAgentSummary(data.agent_summary || '');

      // Pre-mark suggested weeds
      const initialWeeds = new Set<number>(
        stepList.filter(s => s.suggested_weed).map(s => s.step_number)
      );
      setWeedSet(initialWeeds);

      // Default title from issue description
      const shortDesc = issueDescription.slice(0, 60).replace(/\n/g, ' ');
      setRunbookTitle(`Auto: ${shortDesc}`);

      setPhase('review');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load review');
    }
  };

  // ── Save as runbook ─────────────────────────────────────────────────────────
  const handleSaveRunbook = async () => {
    if (!sessionId) return;
    setSaveLoading(true);
    setError(null);
    try {
      const res = await authFetch(
        apiConfig.endpoints.executions.agentSessionReview(sessionId),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            weed_step_numbers: Array.from(weedSet),
            save_as_runbook: true,
            runbook_title: runbookTitle.trim() || undefined,
          }),
        }
      );
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
      if (next.has(stepNumber)) next.delete(stepNumber);
      else next.add(stepNumber);
      return next;
    });
  };

  if (!ticket) return null;

  // ── Render ──────────────────────────────────────────────────────────────────
  return createPortal(
    <div
      className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={phase === 'setup' ? onClose : undefined}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      >
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold text-neutral-900">
                {phase === 'setup' && 'Solve Incident with Agent'}
                {phase === 'running' && 'Agent Running…'}
                {phase === 'review' && 'Review & Save Runbook'}
                {phase === 'done' && 'Runbook Saved'}
              </h3>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <XMarkIcon className="h-6 w-6" />
              </Button>
            </div>
            {phase !== 'setup' && (
              <p className="mt-1 text-sm text-neutral-500">
                {issueDescription.slice(0, 100)}{issueDescription.length > 100 ? '…' : ''}
              </p>
            )}
          </CardHeader>

          <CardContent padding="md">

            {/* ── Phase: Setup ── */}
            {phase === 'setup' && (
              <form onSubmit={handleStartAgent} className="space-y-4">
                <Card variant="outlined" className="border-blue-200 bg-blue-50">
                  <CardContent padding="sm">
                    <p className="text-sm text-blue-800 font-medium">
                      The agent will connect to the target server, run discovery commands,
                      and fix the issue step-by-step. Destructive commands require your approval
                      before executing. Once resolved, you can save the steps as a reusable runbook.
                    </p>
                  </CardContent>
                </Card>

                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">
                    Issue Description *
                  </label>
                  <textarea
                    value={issueDescription}
                    onChange={e => setIssueDescription(e.target.value)}
                    rows={6}
                    className="w-full px-3 py-2.5 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-neutral-900 transition-all"
                    placeholder="Describe the issue…"
                    required
                  />
                </div>

                {error && (
                  <Card variant="outlined" className="border-red-200 bg-red-50">
                    <CardContent padding="sm">
                      <p className="text-sm text-red-800">{error}</p>
                    </CardContent>
                  </Card>
                )}

                <div className="flex justify-end gap-3 pt-2">
                  <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
                  <Button type="submit" variant="primary" disabled={!issueDescription.trim()}>
                    Start Agent
                  </Button>
                </div>
              </form>
            )}

            {/* ── Phase: Running ── */}
            {phase === 'running' && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-sm text-neutral-600">
                  <span className="inline-block h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                  Agent working… {sessionStatus && `(${sessionStatus})`}
                </div>

                {/* Live log */}
                <div className="bg-neutral-950 rounded-lg p-4 h-80 overflow-y-auto font-mono text-xs text-green-400 space-y-1">
                  {logLines.length === 0 ? (
                    <span className="text-neutral-500">Waiting for agent output…</span>
                  ) : (
                    logLines.map((line, i) => (
                      <div key={i} className="whitespace-pre-wrap leading-relaxed">{line}</div>
                    ))
                  )}
                  <div ref={logEndRef} />
                </div>

                <Card variant="outlined" className="border-amber-200 bg-amber-50">
                  <CardContent padding="sm">
                    <p className="text-xs text-amber-800">
                      If the agent requests approval for a destructive command, an approval
                      prompt will appear here. The agent is paused until you respond.
                    </p>
                  </CardContent>
                </Card>

                {error && (
                  <Card variant="outlined" className="border-red-200 bg-red-50">
                    <CardContent padding="sm">
                      <p className="text-sm text-red-800">{error}</p>
                    </CardContent>
                  </Card>
                )}

                <div className="flex justify-end">
                  <Button
                    variant="outline"
                    onClick={() => {
                      if (pollRef.current) clearInterval(pollRef.current);
                      onClose();
                    }}
                  >
                    Close (agent continues in background)
                  </Button>
                </div>
              </div>
            )}

            {/* ── Phase: Review ── */}
            {phase === 'review' && (
              <div className="space-y-4">
                {agentSummary && (
                  <Card variant="outlined" className="border-green-200 bg-green-50">
                    <CardContent padding="sm">
                      <p className="text-sm font-semibold text-green-900">Agent summary</p>
                      <p className="text-sm text-green-800 mt-1">{agentSummary}</p>
                    </CardContent>
                  </Card>
                )}

                <div>
                  <p className="text-sm font-semibold text-neutral-700 mb-1">
                    Review steps — uncheck any that were unnecessary (weeds).
                    Only checked steps will be saved in the runbook.
                  </p>
                  <p className="text-xs text-neutral-500 mb-3">
                    Steps pre-marked as weeds failed or were blocked. You can override any selection.
                  </p>

                  <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                    {steps.map(step => {
                      const isWeed = weedSet.has(step.step_number);
                      return (
                        <div
                          key={step.step_number}
                          className={`rounded-lg border p-3 transition-all cursor-pointer ${
                            isWeed
                              ? 'border-neutral-200 bg-neutral-50 opacity-50'
                              : 'border-neutral-300 bg-white'
                          }`}
                          onClick={() => toggleWeed(step.step_number)}
                        >
                          <div className="flex items-start gap-3">
                            {/* Checkbox */}
                            <div className={`mt-0.5 h-5 w-5 rounded border-2 flex-shrink-0 flex items-center justify-center ${
                              isWeed ? 'border-neutral-300 bg-white' : 'border-blue-500 bg-blue-500'
                            }`}>
                              {!isWeed && (
                                <CheckCircleIcon className="h-4 w-4 text-white" />
                              )}
                            </div>

                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs font-semibold text-neutral-500">
                                  Step {step.step_number}
                                </span>
                                <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${SAFETY_COLORS[step.safety_level] || ''}`}>
                                  {step.safety_label}
                                </span>
                                {isWeed && (
                                  <span className="text-xs text-neutral-400 flex items-center gap-1">
                                    <TrashIcon className="h-3 w-3" /> weed
                                  </span>
                                )}
                              </div>

                              {step.reasoning && (
                                <p className="text-xs text-neutral-500 mt-0.5 italic">
                                  {step.reasoning}
                                </p>
                              )}

                              <code className="block text-xs font-mono text-neutral-800 mt-1 bg-neutral-100 rounded px-2 py-1 truncate">
                                $ {step.command}
                              </code>

                              {step.output && !isWeed && (
                                <pre className="text-xs text-neutral-600 mt-1 whitespace-pre-wrap line-clamp-2">
                                  {step.output.slice(0, 200)}
                                </pre>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Runbook title */}
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-1">
                    Runbook title
                  </label>
                  <input
                    type="text"
                    value={runbookTitle}
                    onChange={e => setRunbookTitle(e.target.value)}
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                    placeholder="Name for the saved runbook…"
                  />
                </div>

                {error && (
                  <Card variant="outlined" className="border-red-200 bg-red-50">
                    <CardContent padding="sm">
                      <p className="text-sm text-red-800">{error}</p>
                    </CardContent>
                  </Card>
                )}

                <div className="flex justify-between items-center pt-2 border-t border-neutral-200">
                  <p className="text-xs text-neutral-500">
                    {steps.length - weedSet.size} of {steps.length} steps will be saved
                  </p>
                  <div className="flex gap-3">
                    <Button variant="outline" onClick={onClose}>Discard</Button>
                    <Button
                      variant="primary"
                      onClick={handleSaveRunbook}
                      isLoading={saveLoading}
                      disabled={saveLoading || steps.length === weedSet.size}
                    >
                      Save as Runbook
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* ── Phase: Done ── */}
            {phase === 'done' && savedRunbook && (
              <div className="space-y-4 py-4 text-center">
                <CheckCircleIcon className="h-16 w-16 text-green-500 mx-auto" />
                <p className="text-xl font-bold text-neutral-900">Runbook saved!</p>
                <p className="text-neutral-600">{savedRunbook.title}</p>
                <p className="text-sm text-neutral-500">
                  Runbook ID: {savedRunbook.id} — this runbook will be reused automatically
                  for future incidents of the same type, with no LLM calls.
                </p>
                <Button variant="primary" onClick={onClose}>Close</Button>
              </div>
            )}

          </CardContent>
        </Card>
      </div>
    </div>,
    document.body
  );
}
