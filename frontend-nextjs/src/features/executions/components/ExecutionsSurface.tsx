'use client';

import { useMemo, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  BoltIcon,
  ClockIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useExecutionSessions } from '../hooks/useExecutionSessions';
import { usePendingApprovals } from '../hooks/usePendingApprovals';

const tabConfig = [
  { id: 'active', label: 'Active Sessions', icon: BoltIcon },
  { id: 'approvals', label: 'Pending Approvals', icon: ShieldCheckIcon },
  { id: 'history', label: 'Recent History', icon: ClockIcon },
  { id: 'all', label: 'All Sessions', icon: CheckCircleIcon },
];

const statusColors: Record<string, string> = {
  pending: 'text-amber-300 bg-amber-500/10',
  running: 'text-blue-300 bg-blue-500/10',
  waiting_approval: 'text-purple-300 bg-purple-500/10',
  completed: 'text-emerald-300 bg-emerald-500/10',
  failed: 'text-red-300 bg-red-500/10',
  completed_with_errors: 'text-orange-300 bg-orange-500/10',
};

const humanStatus = (status: string) =>
  status.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());

export function ExecutionsSurface() {
  const [activeTab, setActiveTab] = useState('active');
  const { sessions, loading: sessionsLoading, error: sessionsError, refresh: refreshSessions } =
    useExecutionSessions();
  const {
    approvals,
    loading: approvalsLoading,
    error: approvalsError,
    refresh: refreshApprovals,
  } = usePendingApprovals();

  const activeSessions = useMemo(
    () =>
      sessions.filter((session) => {
        const status = (session.status || '').toLowerCase();
        return !['completed', 'failed', 'completed_with_errors'].includes(status);
      }),
    [sessions]
  );

  const historySessions = useMemo(() => {
    return [...sessions]
      .sort((a, b) => {
        const aTime = a.started_at ? new Date(a.started_at).getTime() : 0;
        const bTime = b.started_at ? new Date(b.started_at).getTime() : 0;
        return bTime - aTime;
      })
      .slice(0, 25);
  }, [sessions]);

  const renderStatusBadge = (status: string) => {
    const normalized = (status || 'unknown').toLowerCase();
    const className = statusColors[normalized] || 'text-slate-300 bg-slate-700/50';
    return (
      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${className}`}>
        {humanStatus(normalized)}
      </span>
    );
  };

  const renderActiveTab = () => (
    <div className="space-y-4">
      {activeSessions.length === 0 && (
        <p className="text-sm text-slate-400">No sessions are currently running.</p>
      )}
      {activeSessions.map((session) => (
        <div
          key={session.id}
          className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 hover:border-blue-500/40"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-500">Runbook</p>
              <p className="text-lg font-semibold text-white">
                {session.runbook_title || `Runbook #${session.runbook_id}`}
              </p>
            </div>
            {renderStatusBadge(session.status)}
          </div>
          {session.issue_description && (
            <p className="mt-2 text-sm text-slate-400">{session.issue_description}</p>
          )}
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
            <span>Session #{session.id}</span>
            {session.ticket_id && <span>Ticket #{session.ticket_id}</span>}
            {session.started_at && (
              <span>
                Started {formatDistanceToNow(new Date(session.started_at), { addSuffix: true })}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  const renderApprovalsTab = () => (
    <div className="space-y-4">
      {approvals.length === 0 && (
        <p className="text-sm text-slate-400">No approvals waiting. The agent is moving smoothly.</p>
      )}
      {approvals.map((approval) => (
        <div
          key={`${approval.session_id}-${approval.step_number}`}
          className="rounded-2xl border border-purple-500/30 bg-purple-500/5 p-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-widest text-purple-300">Approval Required</p>
              <p className="text-lg font-semibold text-white">
                {approval.runbook_title || `Runbook #${approval.runbook_id}`}
              </p>
            </div>
            <span className="text-xs text-purple-200">
              Step {approval.step_number} · {approval.step_type}
            </span>
          </div>
          <p className="mt-3 text-sm text-purple-100">{approval.command}</p>
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-purple-200">
            <span>Session #{approval.session_id}</span>
            {approval.issue_description && <span>{approval.issue_description}</span>}
            <span>
              Requested {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
            </span>
          </div>
        </div>
      ))}
    </div>
  );

  const renderHistoryTab = () => (
    <div className="space-y-3">
      {historySessions.map((session) => (
        <div
          key={session.id}
          className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3 text-sm text-slate-300"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-semibold text-white">
                {session.runbook_title || `Runbook #${session.runbook_id}`}
              </p>
              <p className="text-xs text-slate-500">
                Session #{session.id} •{' '}
                {session.started_at
                  ? formatDistanceToNow(new Date(session.started_at), { addSuffix: true })
                  : 'Time unknown'}
              </p>
            </div>
            {renderStatusBadge(session.status)}
          </div>
        </div>
      ))}
      {historySessions.length === 0 && (
        <p className="text-sm text-slate-500">No executions recorded yet.</p>
      )}
    </div>
  );

  const renderAllTab = () => (
    <div className="overflow-x-auto rounded-2xl border border-slate-800">
      <table className="min-w-full divide-y divide-slate-900 text-sm">
        <thead className="bg-slate-900/50 text-slate-400">
          <tr>
            <th className="px-4 py-3 text-left font-medium">Runbook</th>
            <th className="px-4 py-3 text-left font-medium">Ticket</th>
            <th className="px-4 py-3 text-left font-medium">Status</th>
            <th className="px-4 py-3 text-left font-medium">Started</th>
            <th className="px-4 py-3 text-left font-medium">Duration</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-900/60 text-slate-300">
          {sessions.map((session) => (
            <tr key={session.id}>
              <td className="px-4 py-3">
                <p className="font-medium text-white">
                  {session.runbook_title || `Runbook #${session.runbook_id}`}
                </p>
                <p className="text-xs text-slate-500">Session #{session.id}</p>
              </td>
              <td className="px-4 py-3 text-xs text-slate-400">
                {session.ticket_id ? `#${session.ticket_id}` : '—'}
              </td>
              <td className="px-4 py-3">{renderStatusBadge(session.status)}</td>
              <td className="px-4 py-3 text-xs text-slate-400">
                {session.started_at
                  ? new Date(session.started_at).toLocaleString()
                  : 'Not started'}
              </td>
              <td className="px-4 py-3 text-xs text-slate-400">
                {session.total_duration_minutes != null
                  ? `${session.total_duration_minutes} min`
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderContent = () => {
    if (sessionsError || approvalsError) {
      return (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-6 text-sm text-red-200">
          <ExclamationTriangleIcon className="mb-2 h-5 w-5" />
          <p>{sessionsError || approvalsError}</p>
        </div>
      );
    }

    if (sessionsLoading || approvalsLoading) {
      return <p className="text-sm text-slate-400">Syncing execution data...</p>;
    }

    switch (activeTab) {
      case 'active':
        return renderActiveTab();
      case 'approvals':
        return renderApprovalsTab();
      case 'history':
        return renderHistoryTab();
      case 'all':
        return renderAllTab();
      default:
        return renderActiveTab();
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Executions</p>
          <h2 className="text-2xl font-semibold text-white">Execution Control Surface</h2>
          <p className="text-sm text-slate-400">
            Monitor live sessions, approve interventions, and review history.
          </p>
        </div>
        <button
          onClick={() => {
            refreshSessions();
            refreshApprovals();
          }}
          className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-300 hover:border-blue-500 hover:text-white"
        >
          <ArrowPathIcon className="h-4 w-4" />
          Refresh data
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {tabConfig.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-2xl px-4 py-2 text-sm transition ${
                isActive
                  ? 'bg-blue-500/10 text-white border border-blue-500/40'
                  : 'border border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {renderContent()}
    </div>
  );
}


