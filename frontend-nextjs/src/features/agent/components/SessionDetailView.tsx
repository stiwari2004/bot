'use client';

import { useEffect, useState } from 'react';
import {
  ArrowUpIcon,
  ArrowDownIcon,
  TrashIcon,
  PlusIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import type { ExecutionSessionDetail, ExecutionStep, ConnectionInfo, ControlAction } from '../types';
import { statusColor, formatDate, formatDuration, formatShortDuration } from '../services/utils';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { apiConfig } from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

// ── Plan approval types ────────────────────────────────────────────────────────

interface PlanStep {
  step: number;
  intent: string;
  command: string;
  risk: string;
}

interface Approach {
  id: string;
  title: string;
  rationale: string;
  risk: string;
  steps: PlanStep[];
}

interface PlanDiagnosis {
  root_cause: string;
  evidence: string[];
  confidence: string;
}

const RISK_COLORS: Record<string, string> = {
  low:    'text-green-700 bg-green-50 border-green-200',
  medium: 'text-amber-700 bg-amber-50 border-amber-200',
  high:   'text-red-700 bg-red-50 border-red-200',
};

const RISK_BADGE: Record<string, string> = {
  low:    'bg-green-100 text-green-800 border border-green-200',
  medium: 'bg-amber-100 text-amber-800 border border-amber-200',
  high:   'bg-red-100 text-red-800 border border-red-200',
};

// ── Props ──────────────────────────────────────────────────────────────────────

interface SessionDetailViewProps {
  session: ExecutionSessionDetail;
  connectionInfo: ConnectionInfo;
  controlBusy: ControlAction | null;
  controlError: string | null;
  stepActionBusy: number | null;
  stepActionError: string | null;
  onControlAction: (action: ControlAction) => void;
  onStepApproval: (step: ExecutionStep, approve: boolean) => void;
  onRetry?: (newSessionId: number) => void;
}

// ── Plan approval panel ────────────────────────────────────────────────────────

function PlanApprovalPanel({
  sessionId,
  onApproved,
}: {
  sessionId: number;
  onApproved: () => void;
}) {
  const [approaches, setApproaches] = useState<Approach[]>([]);
  const [diagnosis, setDiagnosis] = useState<PlanDiagnosis | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [steps, setSteps] = useState<PlanStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [approveLoading, setApproveLoading] = useState(false);
  const [rejectLoading, setRejectLoading] = useState(false);
  const [showReject, setShowReject] = useState(false);
  const [rejectFeedback, setRejectFeedback] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await authFetch(apiConfig.endpoints.executions.agentSessionPlan(sessionId));
        if (!res.ok) throw new Error('Failed to load plan');
        const data = await res.json();
        if (cancelled) return;
        setDiagnosis(data.diagnosis || null);
        const appr: Approach[] = (data.approaches || []).map((a: Approach, i: number) => ({
          id: a.id ?? String.fromCharCode(65 + i),
          title: a.title ?? `Approach ${i + 1}`,
          rationale: a.rationale ?? '',
          risk: a.risk ?? 'medium',
          steps: (a.steps || []).map((s: PlanStep, j: number) => ({
            step: s.step ?? j + 1,
            intent: s.intent ?? '',
            command: s.command ?? '',
            risk: s.risk ?? 'medium',
          })),
        }));
        setApproaches(appr);
        // If only one approach, auto-select it
        if (appr.length === 1) {
          setSelectedId(appr[0].id);
          setSteps(appr[0].steps);
        }
      } catch (e) {
        if (!cancelled) setError('Could not load plan — try refreshing.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [sessionId]);

  const selectApproach = (id: string) => {
    const approach = approaches.find(a => a.id === id);
    if (!approach) return;
    setSelectedId(id);
    setSteps(approach.steps.map((s, i) => ({ ...s, step: i + 1 })));
    setError(null);
  };

  const updateStep = (idx: number, field: keyof PlanStep, value: string) =>
    setSteps(prev => prev.map((s, i) => i === idx ? { ...s, [field]: value } : s));

  const removeStep = (idx: number) =>
    setSteps(prev => prev.filter((_, i) => i !== idx).map((s, i) => ({ ...s, step: i + 1 })));

  const moveStep = (idx: number, dir: 'up' | 'down') =>
    setSteps(prev => {
      const next = [...prev];
      const swap = dir === 'up' ? idx - 1 : idx + 1;
      if (swap < 0 || swap >= next.length) return prev;
      [next[idx], next[swap]] = [next[swap], next[idx]];
      return next.map((s, i) => ({ ...s, step: i + 1 }));
    });

  const addStep = () =>
    setSteps(prev => [...prev, { step: prev.length + 1, intent: '', command: '', risk: 'medium' }]);

  const approve = async () => {
    if (!selectedId) { setError('Please select an approach first.'); return; }
    setApproveLoading(true);
    setError(null);
    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessionPlanApprove(sessionId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_approach_id: selectedId, proposed_plan: steps }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Approval failed');
      onApproved();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Approval failed');
    } finally {
      setApproveLoading(false);
    }
  };

  const reject = async () => {
    if (!rejectFeedback.trim()) return;
    setRejectLoading(true);
    setError(null);
    try {
      const res = await authFetch(apiConfig.endpoints.executions.agentSessionPlanReject(sessionId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: rejectFeedback }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Rejection failed');
      setShowReject(false);
      setRejectFeedback('');
      onApproved(); // triggers workspace to refresh session status
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rejection failed');
    } finally {
      setRejectLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-6 text-sm text-neutral-500">
        <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
        Loading plan…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Diagnosis */}
      {diagnosis && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <p className="text-sm font-semibold text-blue-900 mb-1">
            Diagnosis — {diagnosis.confidence} confidence
          </p>
          <p className="text-sm text-blue-800">{diagnosis.root_cause}</p>
          {diagnosis.evidence?.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {diagnosis.evidence.map((e, i) => (
                <li key={i} className="text-xs text-blue-700 flex gap-1">
                  <span className="text-blue-400 flex-shrink-0">•</span>{e}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Approach selector */}
      {approaches.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-neutral-700 mb-2">
            Choose an approach
          </p>
          <div className="space-y-2">
            {approaches.map(approach => (
              <button
                key={approach.id}
                type="button"
                onClick={() => selectApproach(approach.id)}
                className={`w-full text-left rounded-lg border p-3 transition-all ${
                  selectedId === approach.id
                    ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                    : 'border-neutral-200 bg-white hover:border-blue-300 hover:bg-blue-50/40'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center justify-center h-5 w-5 rounded-full text-xs font-bold flex-shrink-0 ${
                      selectedId === approach.id ? 'bg-blue-600 text-white' : 'bg-neutral-200 text-neutral-600'
                    }`}>{approach.id}</span>
                    <span className="text-sm font-semibold text-neutral-900">{approach.title}</span>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium uppercase ${RISK_BADGE[approach.risk] || RISK_BADGE.medium}`}>
                    {approach.risk}
                  </span>
                </div>
                {approach.rationale && (
                  <p className="text-xs text-neutral-600 ml-7">{approach.rationale}</p>
                )}
                <p className="text-xs text-neutral-400 ml-7 mt-0.5">{approach.steps.length} step{approach.steps.length !== 1 ? 's' : ''}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step editor — shown once an approach is selected */}
      {selectedId && steps.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-neutral-700 mb-1">
            Steps — edit, reorder or remove before approving.
          </p>
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {steps.map((step, idx) => (
              <div key={idx} className="rounded-lg border border-neutral-300 bg-white p-3">
                <div className="flex items-start gap-2">
                  <div className="flex flex-col gap-0.5 pt-0.5 flex-shrink-0">
                    <button type="button" onClick={() => moveStep(idx, 'up')} disabled={idx === 0}
                      className="p-0.5 text-neutral-400 hover:text-neutral-700 disabled:opacity-30">
                      <ArrowUpIcon className="h-3.5 w-3.5" />
                    </button>
                    <button type="button" onClick={() => moveStep(idx, 'down')} disabled={idx === steps.length - 1}
                      className="p-0.5 text-neutral-400 hover:text-neutral-700 disabled:opacity-30">
                      <ArrowDownIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div className="flex-1 min-w-0 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-neutral-500">Step {step.step}</span>
                      <select value={step.risk} onChange={e => updateStep(idx, 'risk', e.target.value)}
                        className={`text-xs px-1.5 py-0.5 rounded border font-medium cursor-pointer ${RISK_COLORS[step.risk] || RISK_COLORS.medium}`}>
                        <option value="low">LOW</option>
                        <option value="medium">MEDIUM</option>
                        <option value="high">HIGH</option>
                      </select>
                    </div>
                    <input type="text" value={step.intent} onChange={e => updateStep(idx, 'intent', e.target.value)}
                      placeholder="What this step achieves…"
                      className="w-full text-xs px-2 py-1.5 border border-neutral-200 rounded text-neutral-700 italic placeholder-neutral-400 focus:ring-1 focus:ring-blue-400 focus:border-blue-400" />
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-mono text-neutral-500 flex-shrink-0">$</span>
                      <input type="text" value={step.command} onChange={e => updateStep(idx, 'command', e.target.value)}
                        placeholder="shell command"
                        className="flex-1 text-xs font-mono px-2 py-1.5 bg-neutral-100 border border-neutral-200 rounded text-neutral-900 placeholder-neutral-400 focus:ring-1 focus:ring-blue-400 focus:border-blue-400" />
                    </div>
                  </div>
                  <button type="button" onClick={() => removeStep(idx)}
                    className="p-1 text-neutral-400 hover:text-red-500 flex-shrink-0">
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
          <button type="button" onClick={addStep}
            className="mt-2 flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 font-medium">
            <PlusIcon className="h-4 w-4" /> Add step
          </button>
        </div>
      )}

      {/* Reject textarea */}
      {showReject && (
        <div className="space-y-2 pt-2 border-t border-neutral-200">
          <div className="flex items-center gap-1.5 text-sm text-amber-700 font-medium">
            <ExclamationTriangleIcon className="h-4 w-4" /> Rejection feedback
          </div>
          <textarea value={rejectFeedback} onChange={e => setRejectFeedback(e.target.value)} rows={3}
            placeholder="Explain what's wrong and what the agent should try instead…"
            className="w-full px-3 py-2 text-sm border border-neutral-300 rounded-lg focus:ring-2 focus:ring-amber-400 text-neutral-900" />
        </div>
      )}

      {error && <p className="text-xs text-red-600 font-medium">{error}</p>}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-neutral-200">
        <p className="text-xs text-neutral-500">
          {selectedId
            ? `${steps.length} step${steps.length !== 1 ? 's' : ''} · approach ${selectedId} selected`
            : 'Select an approach above'}
        </p>
        <div className="flex gap-2">
          {!showReject ? (
            <Button variant="outline" size="sm" onClick={() => setShowReject(true)}>
              None of these work
            </Button>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => setShowReject(false)}>Cancel</Button>
              <Button variant="outline" size="sm" onClick={reject}
                isLoading={rejectLoading} disabled={rejectLoading || !rejectFeedback.trim()}
                className="border-amber-400 text-amber-700 hover:bg-amber-50">
                Send Feedback
              </Button>
            </>
          )}
          <Button variant="primary" size="sm" onClick={approve}
            isLoading={approveLoading} disabled={approveLoading || !selectedId || steps.length === 0}>
            Approve & Execute
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export function SessionDetailView({
  session,
  connectionInfo,
  controlBusy,
  controlError,
  stepActionBusy,
  stepActionError,
  onControlAction,
  onStepApproval,
  onRetry,
}: SessionDetailViewProps) {
  const normalizedStatus = (session.status || '').toLowerCase();
  const isAwaitingPlanApproval = normalizedStatus === 'awaiting_plan_approval';
  const isFailedOrErrors = normalizedStatus === 'completed_with_errors' || normalizedStatus === 'failed';

  const [retryLoading, setRetryLoading] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [retryDirection, setRetryDirection] = useState('');
  // Key to remount PlanApprovalPanel after rejection (agent replans)
  const [planKey, setPlanKey] = useState(0);

  const handleRetry = async () => {
    setRetryLoading(true);
    setRetryError(null);
    try {
      const body: Record<string, string> = {};
      if (retryDirection.trim()) body.user_direction = retryDirection.trim();
      const res = await authFetch(apiConfig.endpoints.executions.agentSessionRetry(session.id), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Failed to retry');
      const data = await res.json();
      if (onRetry) onRetry(data.session_id);
    } catch (e) {
      setRetryError(e instanceof Error ? e.message : 'Failed to start retry');
    } finally {
      setRetryLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Session Overview */}
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-800">Session Overview</h3>
        </CardHeader>
        <CardContent padding="md">
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mb-4">
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Runbook</dt>
              <dd className="text-neutral-900 font-medium">{session.runbook_title || '—'}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Status</dt>
              <dd>
                <Badge variant="status" status={session.status as any} size="sm">
                  {session.status}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Current Step</dt>
              <dd className="text-neutral-900 font-medium">{session.current_step ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Sandbox Profile</dt>
              <dd className="text-neutral-900 font-medium">{session.sandbox_profile ?? 'default'}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Started</dt>
              <dd className="text-neutral-900 font-medium">{formatDate(session.started_at)}</dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Completed</dt>
              <dd className="text-neutral-900 font-medium">{formatDate(session.completed_at ?? undefined)}</dd>
            </div>
          </dl>

          {/* Controls — hide when awaiting plan approval */}
          {!isAwaitingPlanApproval && (
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="warning" size="sm" onClick={() => onControlAction('pause')}
                disabled={controlBusy !== null || normalizedStatus === 'paused' || normalizedStatus === 'rollback_requested'}
                isLoading={controlBusy === 'pause'}>
                {controlBusy === 'pause' ? 'Pausing…' : 'Pause'}
              </Button>
              <Button variant="success" size="sm" onClick={() => onControlAction('resume')}
                disabled={controlBusy !== null || normalizedStatus !== 'paused'}
                isLoading={controlBusy === 'resume'}>
                {controlBusy === 'resume' ? 'Resuming…' : 'Resume'}
              </Button>
              <Button variant="danger" size="sm" onClick={() => onControlAction('rollback')}
                disabled={controlBusy !== null || normalizedStatus === 'rollback_requested'}
                isLoading={controlBusy === 'rollback'}>
                {controlBusy === 'rollback' ? 'Requesting…' : 'Trigger Rollback'}
              </Button>
            </div>
          )}
          {controlError && <p className="mt-3 text-xs text-error-600 font-medium">{controlError}</p>}
        </CardContent>
      </Card>

      {/* ── Plan Approval Panel ── */}
      {isAwaitingPlanApproval && (
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
              <h3 className="text-lg font-semibold text-neutral-800">Awaiting Your Approval</h3>
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">
              Review the proposed plan below. Edit steps if needed, then approve to begin execution.
            </p>
          </CardHeader>
          <CardContent padding="md">
            <PlanApprovalPanel
              key={planKey}
              sessionId={session.id}
              onApproved={() => setPlanKey(k => k + 1)}
            />
          </CardContent>
        </Card>
      )}

      {/* ── Try another approach (on failure) ── */}
      {isFailedOrErrors && onRetry && (
        <Card variant="outlined" className="border-amber-200 bg-amber-50">
          <CardContent padding="md">
            <p className="text-sm font-semibold text-amber-900 mb-1">Execution did not resolve the issue</p>
            <p className="text-xs text-amber-700 mb-3">
              Tell the agent what NOT to do and which direction to try instead. This context will be
              injected into the new session so it doesn't repeat the same approach.
            </p>
            <textarea
              value={retryDirection}
              onChange={e => setRetryDirection(e.target.value)}
              rows={3}
              placeholder="e.g. Don't delete the app. Instead try restarting the service or clearing the cache…"
              className="w-full px-3 py-2 text-sm border border-amber-300 rounded-lg bg-white text-neutral-900 placeholder-neutral-400 focus:ring-2 focus:ring-amber-400 focus:border-amber-400 mb-3"
            />
            <div className="flex items-center justify-between gap-4">
              {retryError
                ? <p className="text-xs text-red-600 font-medium">{retryError}</p>
                : <span />
              }
              <Button variant="warning" size="sm" onClick={handleRetry}
                isLoading={retryLoading} disabled={retryLoading}
                leftIcon={<ArrowPathIcon className="h-4 w-4" />}>
                Try another approach
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connection Telemetry */}
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-800">Connection Telemetry</h3>
        </CardHeader>
        <CardContent padding="md">
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div><dt className="text-neutral-500 font-semibold mb-1">Target Host</dt><dd className="text-neutral-900 font-medium">{connectionInfo.host ?? '—'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Connector</dt><dd className="text-neutral-900 font-medium">{connectionInfo.connector ?? '—'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Environment</dt><dd className="text-neutral-900 font-medium">{connectionInfo.environment ?? '—'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Service</dt><dd className="text-neutral-900 font-medium">{connectionInfo.service ?? '—'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Cluster</dt><dd className="text-neutral-900 font-medium">{connectionInfo.clusterId ?? '—'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Device</dt><dd className="text-neutral-900 font-medium">{connectionInfo.deviceId ?? '—'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Sandbox</dt><dd className="text-neutral-900 font-medium">{connectionInfo.sandboxProfile ?? 'default'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Credential Source</dt><dd className="text-neutral-900 font-medium">{connectionInfo.credentialSource ?? '—'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Assigned Worker</dt><dd className="text-neutral-900 font-medium">{connectionInfo.workerId ?? '—'}</dd></div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Connection Latency</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.connectionLatencyMs !== undefined ? formatShortDuration(connectionInfo.connectionLatencyMs) ?? '—' : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Last Command</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.lastCommand || connectionInfo.lastCommandDurationMs !== undefined ? (
                  <>
                    {connectionInfo.lastCommand && <div className="text-xs text-neutral-600 mb-1 font-mono truncate">{connectionInfo.lastCommand}</div>}
                    {connectionInfo.lastCommandDurationMs !== undefined && (
                      <div className="text-xs">{formatShortDuration(connectionInfo.lastCommandDurationMs) ?? '—'} · {connectionInfo.lastCommandStatus === 'error' ? 'failed' : 'success'}{connectionInfo.lastCommandRetries ? ` · retries ${connectionInfo.lastCommandRetries}` : ''}</div>
                    )}
                  </>
                ) : '—'}
              </dd>
            </div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Approval Mode</dt><dd className="text-neutral-900 font-medium">{connectionInfo.approvalMode ? connectionInfo.approvalMode.replace('_', ' ') : '—'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">SLA Remaining</dt><dd className="text-neutral-900 font-medium">{formatDuration(connectionInfo.slaRemainingMs)}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">SLA Deadline</dt><dd className="text-neutral-900 font-medium">{connectionInfo.slaDeadline ? formatDate(connectionInfo.slaDeadline.toISOString()) : '—'}</dd></div>
          </dl>
        </CardContent>
      </Card>

      {/* Execution Steps — only shown when actually executing */}
      {!isAwaitingPlanApproval && session.steps.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <h3 className="text-lg font-semibold text-neutral-800">Steps</h3>
          </CardHeader>
          <CardContent padding="md">
            <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
              {session.steps.map((step) => {
                const approvalStatus = step.requires_approval
                  ? step.approved === true ? 'approved' : step.approved === false ? 'rejected' : 'pending'
                  : 'n/a';
                return (
                  <Card key={`${step.step_number}-${step.step_type}`} variant="default">
                    <CardContent padding="sm">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex-1">
                          <div className="font-semibold text-neutral-900 mb-1">
                            #{step.step_number} <span className="text-neutral-500 font-normal">{step.step_type || 'step'}</span>
                          </div>
                          <div className="text-xs text-neutral-600 line-clamp-2 font-mono">{step.command}</div>
                        </div>
                        <div className="text-xs text-right">
                          {step.completed ? (
                            <Badge variant="success" size="sm">Done</Badge>
                          ) : (
                            <Badge variant="secondary" size="sm">
                              {step.requires_approval && step.approved === null ? 'Awaiting approval' : 'Pending'}
                            </Badge>
                          )}
                        </div>
                      </div>
                      {step.requires_approval && (
                        step.approved === null ? (
                          <div className="flex flex-wrap justify-end gap-2 mt-2">
                            <Button variant="success" size="sm" onClick={() => onStepApproval(step, true)}
                              disabled={stepActionBusy === step.step_number} isLoading={stepActionBusy === step.step_number}>
                              {stepActionBusy === step.step_number ? 'Saving...' : 'Approve'}
                            </Button>
                            <Button variant="danger" size="sm" onClick={() => onStepApproval(step, false)}
                              disabled={stepActionBusy === step.step_number} isLoading={stepActionBusy === step.step_number}>
                              {stepActionBusy === step.step_number ? 'Saving...' : 'Request changes'}
                            </Button>
                          </div>
                        ) : (
                          <div className="flex justify-end mt-2">
                            <Badge variant={approvalStatus === 'approved' ? 'success' : approvalStatus === 'rejected' ? 'error' : 'warning'} size="sm">
                              {approvalStatus === 'approved' ? 'Approved' : approvalStatus === 'rejected' ? 'Changes requested' : 'Pending'}
                            </Badge>
                          </div>
                        )
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
            {stepActionError && <div className="mt-3 text-xs text-error-600 font-medium">{stepActionError}</div>}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
