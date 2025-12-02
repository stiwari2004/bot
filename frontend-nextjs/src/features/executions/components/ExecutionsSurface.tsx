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
  pending: 'text-amber-700 bg-amber-50 border-amber-200',
  running: 'text-blue-700 bg-blue-50 border-blue-200',
  waiting_approval: 'text-purple-700 bg-purple-50 border-purple-200',
  completed: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  failed: 'text-red-700 bg-red-50 border-red-200',
  completed_with_errors: 'text-orange-700 bg-orange-50 border-orange-200',
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
    const className = statusColors[normalized] || 'text-gray-700 bg-gray-100 border-gray-200';
    return (
      <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${className}`}>
        {humanStatus(normalized)}
      </span>
    );
  };

  const renderActiveTab = () => (
    <div className="space-y-4">
      {activeSessions.length === 0 && (
        <p className="text-sm text-gray-500 text-left">No sessions are currently running.</p>
      )}
      {activeSessions.map((session) => (
        <div
          key={session.id}
          className="rounded-2xl border border-gray-100 bg-white p-4 hover:border-indigo-200 hover:shadow-md shadow-sm transition-all"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-left">
              <p className="text-xs uppercase tracking-widest text-gray-500">Runbook</p>
              <p className="text-lg font-semibold text-gray-900">
                {session.runbook_title || `Runbook #${session.runbook_id}`}
              </p>
            </div>
            {renderStatusBadge(session.status)}
          </div>
          {session.issue_description && (
            <p className="mt-2 text-sm text-gray-600 text-left">{session.issue_description}</p>
          )}
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
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
        <p className="text-sm text-gray-500 text-left">No approvals waiting. The agent is moving smoothly.</p>
      )}
      {approvals.map((approval) => (
        <div
          key={`${approval.session_id}-${approval.step_number}`}
          className="rounded-2xl border border-violet-200 bg-gradient-to-br from-violet-50 to-indigo-50 p-4 shadow-sm hover:shadow-md transition-shadow"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-left">
              <p className="text-xs uppercase tracking-widest text-purple-600">Approval Required</p>
              <p className="text-lg font-semibold text-gray-900">
                {approval.runbook_title || `Runbook #${approval.runbook_id}`}
              </p>
            </div>
            <span className="text-xs text-purple-700 font-medium">
              Step {approval.step_number} · {approval.step_type}
            </span>
          </div>
          <p className="mt-3 text-sm text-gray-700 text-left font-mono bg-white p-2 rounded border border-gray-200">{approval.command}</p>
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-600">
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
          className="rounded-xl border border-gray-100 bg-white px-4 py-3 text-sm shadow-sm hover:shadow-md transition-shadow"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-left">
              <p className="font-semibold text-gray-900">
                {session.runbook_title || `Runbook #${session.runbook_id}`}
              </p>
              <p className="text-xs text-gray-500">
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
        <p className="text-sm text-gray-500 text-left">No executions recorded yet.</p>
      )}
    </div>
  );

  const renderAllTab = () => (
    <div className="overflow-x-auto rounded-2xl border border-gray-100 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50 text-gray-700">
          <tr>
            <th className="px-4 py-3 text-left font-semibold">Runbook</th>
            <th className="px-4 py-3 text-left font-semibold">Ticket</th>
            <th className="px-4 py-3 text-left font-semibold">Status</th>
            <th className="px-4 py-3 text-left font-semibold">Started</th>
            <th className="px-4 py-3 text-left font-semibold">Duration</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {sessions.map((session) => (
            <tr key={session.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <p className="font-medium text-gray-900">
                  {session.runbook_title || `Runbook #${session.runbook_id}`}
                </p>
                <p className="text-xs text-gray-500">Session #{session.id}</p>
              </td>
              <td className="px-4 py-3 text-xs text-gray-600">
                {session.ticket_id ? `#${session.ticket_id}` : '—'}
              </td>
              <td className="px-4 py-3">{renderStatusBadge(session.status)}</td>
              <td className="px-4 py-3 text-xs text-gray-600">
                {session.started_at
                  ? new Date(session.started_at).toLocaleString()
                  : 'Not started'}
              </td>
              <td className="px-4 py-3 text-xs text-gray-600">
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
        <div className="rounded-2xl border border-red-300 bg-red-50 p-6 text-sm text-red-700">
          <ExclamationTriangleIcon className="mb-2 h-5 w-5" />
          <p className="text-left">{sessionsError || approvalsError}</p>
        </div>
      );
    }

    if (sessionsLoading || approvalsLoading) {
      return <p className="text-sm text-gray-500 text-left">Syncing execution data...</p>;
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
        <div className="text-left">
          <p className="text-xs uppercase tracking-[0.4em] text-gray-500">Executions</p>
          <h2 className="text-2xl font-semibold text-gray-900">Execution Control Surface</h2>
          <p className="text-sm text-gray-600">
            Monitor live sessions, approve interventions, and review history.
          </p>
        </div>
        <button
          onClick={() => {
            refreshSessions();
            refreshApprovals();
          }}
          className="flex items-center gap-2 rounded-2xl border border-gray-200 bg-white px-4 py-2 text-sm text-gray-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 transition-colors shadow-sm"
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
              className={`flex items-center gap-2 rounded-2xl px-4 py-2 text-sm transition border shadow-sm ${
                isActive
                  ? 'bg-gradient-to-r from-indigo-50 to-violet-50 text-indigo-700 border-indigo-300'
                  : 'border border-gray-200 text-gray-600 hover:border-indigo-200 hover:bg-indigo-50/50'
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


