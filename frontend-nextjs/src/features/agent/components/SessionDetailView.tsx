'use client';

import type { ExecutionSessionDetail, ExecutionStep, ConnectionInfo, ControlAction } from '../types';
import { statusColor, formatDate, formatDuration, formatShortDuration } from '../services/utils';

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
      <div className="border border-gray-200 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-gray-800 mb-2">
          Session Overview
        </h3>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-gray-500">Runbook</dt>
            <dd className="text-gray-900">{session.runbook_title}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Status</dt>
            <dd>
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(
                  session.status
                )}`}
              >
                {session.status}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Current Step</dt>
            <dd className="text-gray-900">
              {session.current_step ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Sandbox Profile</dt>
            <dd className="text-gray-900">
              {session.sandbox_profile ?? 'default'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Started</dt>
            <dd className="text-gray-900">
              {formatDate(session.started_at)}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Completed</dt>
            <dd className="text-gray-900">
              {formatDate(session.completed_at ?? undefined)}
            </dd>
          </div>
        </dl>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={() => onControlAction('pause')}
            disabled={
              controlBusy !== null ||
              normalizedStatus === 'paused' ||
              normalizedStatus === 'rollback_requested'
            }
            className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium ${
              controlBusy === 'pause'
                ? 'bg-amber-300 text-amber-900'
                : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {controlBusy === 'pause' ? 'Pausing…' : 'Pause'}
          </button>
          <button
            onClick={() => onControlAction('resume')}
            disabled={
              controlBusy !== null || normalizedStatus !== 'paused'
            }
            className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium ${
              controlBusy === 'resume'
                ? 'bg-green-400 text-white'
                : 'bg-green-100 text-green-700 hover:bg-green-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {controlBusy === 'resume' ? 'Resuming…' : 'Resume'}
          </button>
          <button
            onClick={() => onControlAction('rollback')}
            disabled={
              controlBusy !== null ||
              normalizedStatus === 'rollback_requested'
            }
            className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium ${
              controlBusy === 'rollback'
                ? 'bg-red-400 text-white'
                : 'bg-red-100 text-red-700 hover:bg-red-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {controlBusy === 'rollback' ? 'Requesting…' : 'Trigger Rollback'}
          </button>
        </div>
        {controlError && (
          <p className="mt-2 text-xs text-red-600">{controlError}</p>
        )}
      </div>

      <div className="border border-gray-200 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-gray-800 mb-2">
          Connection Telemetry
        </h3>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-gray-500">Target Host</dt>
            <dd className="text-gray-900">
              {connectionInfo.host ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Connector</dt>
            <dd className="text-gray-900">
              {connectionInfo.connector ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Environment</dt>
            <dd className="text-gray-900">
              {connectionInfo.environment ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Service</dt>
            <dd className="text-gray-900">
              {connectionInfo.service ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Cluster</dt>
            <dd className="text-gray-900">
              {connectionInfo.clusterId ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Device</dt>
            <dd className="text-gray-900">
              {connectionInfo.deviceId ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Sandbox</dt>
            <dd className="text-gray-900">
              {connectionInfo.sandboxProfile ?? 'default'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Credential Source</dt>
            <dd className="text-gray-900">
              {connectionInfo.credentialSource ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Assigned Worker</dt>
            <dd className="text-gray-900">
              {connectionInfo.workerId ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Connection Latency</dt>
            <dd className="text-gray-900">
              {connectionInfo.connectionLatencyMs !== undefined
                ? formatShortDuration(connectionInfo.connectionLatencyMs) ?? '—'
                : '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Last Command</dt>
            <dd className="text-gray-900">
              {connectionInfo.lastCommandDurationMs !== undefined || connectionInfo.lastCommand
                ? (
                    <>
                      {connectionInfo.lastCommand && (
                        <div className="text-xs text-gray-600 mb-1 font-mono truncate" title={connectionInfo.lastCommand}>
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
            <dt className="text-gray-500">Approval Mode</dt>
            <dd className="text-gray-900">
              {connectionInfo.approvalMode
                ? connectionInfo.approvalMode.replace('_', ' ')
                : '—'}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">SLA Remaining</dt>
            <dd className="text-gray-900">
              {formatDuration(connectionInfo.slaRemainingMs)}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">SLA Deadline</dt>
            <dd className="text-gray-900">
              {connectionInfo.slaDeadline
                ? formatDate(connectionInfo.slaDeadline.toISOString())
                : '—'}
            </dd>
          </div>
        </dl>
      </div>

      <div className="border border-gray-200 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-gray-800 mb-2">
          Steps
        </h3>
        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
          {session.steps.map((step) => {
            const approvalStatus = step.requires_approval
              ? step.approved === true
                ? 'approved'
                : step.approved === false
                ? 'rejected'
                : 'pending'
              : 'n/a';
            const approvalBadge =
              approvalStatus === 'approved'
                ? 'bg-green-100 text-green-700'
                : approvalStatus === 'rejected'
                ? 'bg-red-100 text-red-700'
                : 'bg-amber-100 text-amber-700';
            return (
              <div
                key={`${step.step_number}-${step.step_type}`}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold text-gray-800">
                      #{step.step_number}{' '}
                      <span className="text-gray-500">
                        {step.step_type || 'step'}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 line-clamp-2">
                      {step.command}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 text-right">
                    {step.completed ? (
                      <span className="text-green-600 font-semibold">
                        Done
                      </span>
                    ) : (
                      <span>
                        {step.requires_approval && step.approved === null
                          ? 'Awaiting approval'
                          : 'Pending'}
                      </span>
                    )}
                  </div>
                </div>
                {step.requires_approval && (
                  step.approved === null ? (
                    <div className="flex flex-wrap justify-end gap-2">
                      <button
                        onClick={() => onStepApproval(step, true)}
                        disabled={stepActionBusy === step.step_number}
                        className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium text-white ${
                          stepActionBusy === step.step_number
                            ? 'bg-green-400'
                            : 'bg-green-600 hover:bg-green-700'
                        }`}
                      >
                        {stepActionBusy === step.step_number
                          ? 'Saving...'
                          : 'Approve'}
                      </button>
                      <button
                        onClick={() => onStepApproval(step, false)}
                        disabled={stepActionBusy === step.step_number}
                        className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-xs font-medium text-white ${
                          stepActionBusy === step.step_number
                            ? 'bg-red-400'
                            : 'bg-red-600 hover:bg-red-700'
                        }`}
                      >
                        {stepActionBusy === step.step_number
                          ? 'Saving...'
                          : 'Request changes'}
                      </button>
                    </div>
                  ) : (
                    <div className="flex justify-end">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${approvalBadge}`}
                      >
                        {approvalStatus === 'approved'
                          ? 'Approved'
                          : approvalStatus === 'rejected'
                          ? 'Changes requested'
                          : 'Pending'}
                      </span>
                    </div>
                  )
                )}
              </div>
            );
          })}
        </div>
        {stepActionError && (
          <div className="mt-3 text-xs text-red-600">
            {stepActionError}
          </div>
        )}
      </div>
    </div>
  );
}



