'use client';

import type { ExecutionSessionDetail, ExecutionStep, ConnectionInfo, ControlAction } from '../types';
import { statusColor, formatDate, formatDuration, formatShortDuration } from '../services/utils';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

interface SessionDetailViewProps {
  session: ExecutionSessionDetail;
  connectionInfo: ConnectionInfo;
  controlBusy: ControlAction | null;
  controlError: string | null;
  stepActionBusy: number | null;
  stepActionError: string | null;
  onControlAction: (action: ControlAction) => void;
  onStepApproval: (step: ExecutionStep, approve: boolean) => void;
}

export function SessionDetailView({
  session,
  connectionInfo,
  controlBusy,
  controlError,
  stepActionBusy,
  stepActionError,
  onControlAction,
  onStepApproval,
}: SessionDetailViewProps) {
  const normalizedStatus = (session.status || '').toLowerCase();

  return (
    <div className="space-y-6">
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-800">
            Session Overview
          </h3>
        </CardHeader>
        <CardContent padding="md">
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mb-4">
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Runbook</dt>
              <dd className="text-neutral-900 font-medium">{session.runbook_title}</dd>
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
              <dd className="text-neutral-900 font-medium">
                {session.current_step ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Sandbox Profile</dt>
              <dd className="text-neutral-900 font-medium">
                {session.sandbox_profile ?? 'default'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Started</dt>
              <dd className="text-neutral-900 font-medium">
                {formatDate(session.started_at)}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Completed</dt>
              <dd className="text-neutral-900 font-medium">
                {formatDate(session.completed_at ?? undefined)}
              </dd>
            </div>
          </dl>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              variant="warning"
              size="sm"
              onClick={() => onControlAction('pause')}
              disabled={
                controlBusy !== null ||
                normalizedStatus === 'paused' ||
                normalizedStatus === 'rollback_requested'
              }
              isLoading={controlBusy === 'pause'}
            >
              {controlBusy === 'pause' ? 'Pausing…' : 'Pause'}
            </Button>
            <Button
              variant="success"
              size="sm"
              onClick={() => onControlAction('resume')}
              disabled={
                controlBusy !== null || normalizedStatus !== 'paused'
              }
              isLoading={controlBusy === 'resume'}
            >
              {controlBusy === 'resume' ? 'Resuming…' : 'Resume'}
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => onControlAction('rollback')}
              disabled={
                controlBusy !== null ||
                normalizedStatus === 'rollback_requested'
              }
              isLoading={controlBusy === 'rollback'}
            >
              {controlBusy === 'rollback' ? 'Requesting…' : 'Trigger Rollback'}
            </Button>
          </div>
          {controlError && (
            <p className="mt-3 text-xs text-error-600 font-medium">{controlError}</p>
          )}
        </CardContent>
      </Card>

      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-800">
            Connection Telemetry
          </h3>
        </CardHeader>
        <CardContent padding="md">
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Target Host</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.host ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Connector</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.connector ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Environment</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.environment ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Service</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.service ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Cluster</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.clusterId ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Device</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.deviceId ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Sandbox</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.sandboxProfile ?? 'default'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Credential Source</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.credentialSource ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Assigned Worker</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.workerId ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Connection Latency</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.connectionLatencyMs !== undefined
                  ? formatShortDuration(connectionInfo.connectionLatencyMs) ?? '—'
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Last Command</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.lastCommandDurationMs !== undefined || connectionInfo.lastCommand
                  ? (
                      <>
                        {connectionInfo.lastCommand && (
                          <div className="text-xs text-neutral-600 mb-1 font-mono truncate" title={connectionInfo.lastCommand}>
                            {connectionInfo.lastCommand}
                          </div>
                        )}
                        {connectionInfo.lastCommandDurationMs !== undefined && (
                          <div className="text-xs">
                            {formatShortDuration(connectionInfo.lastCommandDurationMs) ?? '—'} · {
                              connectionInfo.lastCommandStatus === 'error'
                                ? 'failed'
                                : 'success'
                            }{
                              connectionInfo.lastCommandRetries
                                ? ` · retries ${connectionInfo.lastCommandRetries}`
                                : ''
                            }
                          </div>
                        )}
                      </>
                    )
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">Approval Mode</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.approvalMode
                  ? connectionInfo.approvalMode.replace('_', ' ')
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">SLA Remaining</dt>
              <dd className="text-neutral-900 font-medium">
                {formatDuration(connectionInfo.slaRemainingMs)}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500 font-semibold mb-1">SLA Deadline</dt>
              <dd className="text-neutral-900 font-medium">
                {connectionInfo.slaDeadline
                  ? formatDate(connectionInfo.slaDeadline.toISOString())
                  : '—'}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-800">
            Steps
          </h3>
        </CardHeader>
        <CardContent padding="md">
          <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
            {session.steps.map((step) => {
              const approvalStatus = step.requires_approval
                ? step.approved === true
                  ? 'approved'
                  : step.approved === false
                  ? 'rejected'
                  : 'pending'
                : 'n/a';
              return (
                <Card
                  key={`${step.step_number}-${step.step_type}`}
                  variant="default"
                >
                  <CardContent padding="sm">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex-1">
                        <div className="font-semibold text-neutral-900 mb-1">
                          #{step.step_number}{' '}
                          <span className="text-neutral-500 font-normal">
                            {step.step_type || 'step'}
                          </span>
                        </div>
                        <div className="text-xs text-neutral-600 line-clamp-2 font-mono">
                          {step.command}
                        </div>
                      </div>
                      <div className="text-xs text-right">
                        {step.completed ? (
                          <Badge variant="success" size="sm">Done</Badge>
                        ) : (
                          <Badge variant="secondary" size="sm">
                            {step.requires_approval && step.approved === null
                              ? 'Awaiting approval'
                              : 'Pending'}
                          </Badge>
                        )}
                      </div>
                    </div>
                    {step.requires_approval && (
                      step.approved === null ? (
                        <div className="flex flex-wrap justify-end gap-2 mt-2">
                          <Button
                            variant="success"
                            size="sm"
                            onClick={() => onStepApproval(step, true)}
                            disabled={stepActionBusy === step.step_number}
                            isLoading={stepActionBusy === step.step_number}
                          >
                            {stepActionBusy === step.step_number
                              ? 'Saving...'
                              : 'Approve'}
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => onStepApproval(step, false)}
                            disabled={stepActionBusy === step.step_number}
                            isLoading={stepActionBusy === step.step_number}
                          >
                            {stepActionBusy === step.step_number
                              ? 'Saving...'
                              : 'Request changes'}
                          </Button>
                        </div>
                      ) : (
                        <div className="flex justify-end mt-2">
                          <Badge
                            variant={approvalStatus === 'approved' ? 'success' : approvalStatus === 'rejected' ? 'error' : 'warning'}
                            size="sm"
                          >
                            {approvalStatus === 'approved'
                              ? 'Approved'
                              : approvalStatus === 'rejected'
                              ? 'Changes requested'
                              : 'Pending'}
                          </Badge>
                        </div>
                      )
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
          {stepActionError && (
            <div className="mt-3 text-xs text-error-600 font-medium">
              {stepActionError}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}



