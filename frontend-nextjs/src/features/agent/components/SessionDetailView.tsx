'use client';

import { useState } from 'react';
import { ArrowPathIcon } from '@heroicons/react/24/outline';
import type { ExecutionSessionDetail, ExecutionStep, ConnectionInfo, ControlAction } from '../types';
import { formatDate, formatDuration, formatShortDuration } from '../services/utils';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { PlanApprovalPanel } from './PlanApprovalPanel';
import { SessionReviewPanel } from './SessionReviewPanel';
import { FlagForReviewButton } from './FlagForReviewButton';
import { submitFeedback, retrySession } from '../services/agentSessionService';

interface Props {
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

export function SessionDetailView({
  session, connectionInfo, controlBusy, controlError,
  stepActionBusy, stepActionError, onControlAction, onStepApproval, onRetry,
}: Props) {
  const status = (session.status || '').toLowerCase();
  const isAwaitingPlan  = status === 'awaiting_plan_approval';
  const isFailedOrErrors = status === 'completed_with_errors' || status === 'failed';

  const [planKey, setPlanKey] = useState(0);
  const [reviewDone, setReviewDone] = useState(false);
  const [direction, setDirection] = useState('');
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [retryLoading, setRetryLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleFeedback = async () => {
    if (!direction.trim()) return;
    setFeedbackLoading(true);
    setActionError(null);
    try {
      await submitFeedback(session.id, direction.trim());
      setFeedbackSent(true);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to submit feedback');
    } finally {
      setFeedbackLoading(false);
    }
  };

  const handleRetry = async () => {
    setRetryLoading(true);
    setActionError(null);
    try {
      const data = await retrySession(session.id, direction);
      if (onRetry) onRetry(data.session_id);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to start retry');
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
            <div><dt className="text-neutral-500 font-semibold mb-1">Runbook</dt><dd className="text-neutral-900 font-medium">{session.runbook_title || '—'}</dd></div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Status</dt>
              <dd><Badge variant="status" status={session.status as any} size="sm">{session.status}</Badge></dd>
            </div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Current Step</dt><dd className="text-neutral-900 font-medium">{session.current_step ?? '—'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Sandbox Profile</dt><dd className="text-neutral-900 font-medium">{session.sandbox_profile ?? 'default'}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Started</dt><dd className="text-neutral-900 font-medium">{formatDate(session.started_at)}</dd></div>
            <div><dt className="text-neutral-500 font-semibold mb-1">Completed</dt><dd className="text-neutral-900 font-medium">{formatDate(session.completed_at ?? undefined)}</dd></div>
          </dl>
          {!isAwaitingPlan && (
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="warning" size="sm" onClick={() => onControlAction('pause')}
                disabled={controlBusy !== null || status === 'paused' || status === 'rollback_requested'}
                isLoading={controlBusy === 'pause'}>
                {controlBusy === 'pause' ? 'Pausing…' : 'Pause'}
              </Button>
              <Button variant="success" size="sm" onClick={() => onControlAction('resume')}
                disabled={controlBusy !== null || status !== 'paused'}
                isLoading={controlBusy === 'resume'}>
                {controlBusy === 'resume' ? 'Resuming…' : 'Resume'}
              </Button>
              <Button variant="danger" size="sm" onClick={() => onControlAction('rollback')}
                disabled={controlBusy !== null || status === 'rollback_requested'}
                isLoading={controlBusy === 'rollback'}>
                {controlBusy === 'rollback' ? 'Requesting…' : 'Trigger Rollback'}
              </Button>
            </div>
          )}
          {controlError && <p className="mt-3 text-xs text-error-600 font-medium">{controlError}</p>}
        </CardContent>
      </Card>

      {/* Plan approval */}
      {isAwaitingPlan && (
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
              <h3 className="text-lg font-semibold text-neutral-800">Awaiting Your Approval</h3>
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">Review the proposed plan below. Edit steps if needed, then approve to begin execution.</p>
          </CardHeader>
          <CardContent padding="md">
            <PlanApprovalPanel key={planKey} sessionId={session.id} onApproved={() => setPlanKey(k => k + 1)} />
          </CardContent>
        </Card>
      )}

      {/* Post-execution review */}
      {session.pending_review && !reviewDone && (
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-green-400" />
              <h3 className="text-lg font-semibold text-neutral-800">Execution Complete — Review Steps</h3>
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">The agent finished execution. Optionally save the successful steps as a reusable runbook.</p>
          </CardHeader>
          <CardContent padding="md">
            <SessionReviewPanel sessionId={session.id} agentSummary={session.agent_summary} onDone={() => setReviewDone(true)} />
          </CardContent>
        </Card>
      )}

      {/* Flag runbook for review */}
      {isFailedOrErrors && session.runbook_id && (
        <Card variant="outlined" className="border-amber-200 bg-amber-50/60">
          <CardContent padding="md">
            <p className="text-sm font-semibold text-amber-900 mb-1">Runbook did not work as expected</p>
            <p className="text-xs text-amber-700 mb-3">Flag this runbook for review so it appears in the Quarantine Dashboard for inspection and update. It will be blocked from auto-execution until reviewed and released.</p>
            <FlagForReviewButton runbookId={session.runbook_id} />
          </CardContent>
        </Card>
      )}

      {/* Retry with feedback */}
      {isFailedOrErrors && onRetry && (
        <Card variant="outlined" className="border-amber-200 bg-amber-50">
          <CardContent padding="md">
            <p className="text-sm font-semibold text-amber-900 mb-1">Execution did not resolve the issue</p>
            <p className="text-xs text-amber-700 mb-3">Leave feedback for the system to learn from, or tell the agent what to try instead and retry.</p>
            {feedbackSent ? (
              <div className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800 font-medium mb-3">
                Feedback recorded — thank you. The system will use this to improve future runs.
              </div>
            ) : (
              <textarea value={direction} onChange={e => { setDirection(e.target.value); setFeedbackSent(false); }} rows={3}
                placeholder="e.g. The issue was in /var/log — old journal files. Don't touch the app directory."
                className="w-full px-3 py-2 text-sm border border-amber-300 rounded-lg bg-white text-neutral-900 placeholder-neutral-400 focus:ring-2 focus:ring-amber-400 focus:border-amber-400 mb-3" />
            )}
            <div className="flex items-center justify-between gap-3 flex-wrap">
              {actionError ? <p className="text-xs text-red-600 font-medium">{actionError}</p> : <span />}
              <div className="flex gap-2">
                {!feedbackSent && (
                  <Button variant="outline" size="sm" onClick={handleFeedback}
                    isLoading={feedbackLoading} disabled={feedbackLoading || !direction.trim()}>
                    Submit feedback
                  </Button>
                )}
                <Button variant="warning" size="sm" onClick={handleRetry}
                  isLoading={retryLoading} disabled={retryLoading}
                  leftIcon={<ArrowPathIcon className="h-4 w-4" />}>
                  Try another approach
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connection Telemetry */}
      <Card variant="elevated">
        <CardHeader><h3 className="text-lg font-semibold text-neutral-800">Connection Telemetry</h3></CardHeader>
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
              <dd className="text-neutral-900 font-medium">{connectionInfo.connectionLatencyMs !== undefined ? formatShortDuration(connectionInfo.connectionLatencyMs) ?? '—' : '—'}</dd>
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

      {/* Execution Steps */}
      {!isAwaitingPlan && session.steps.length > 0 && (
        <Card variant="elevated">
          <CardHeader><h3 className="text-lg font-semibold text-neutral-800">Steps</h3></CardHeader>
          <CardContent padding="md">
            <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
              {session.steps.map(step => {
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
                          {step.completed
                            ? <Badge variant="success" size="sm">Done</Badge>
                            : <Badge variant="secondary" size="sm">{step.requires_approval && step.approved === null ? 'Awaiting approval' : 'Pending'}</Badge>
                          }
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
