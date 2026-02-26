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
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { useExecutionSessions } from '../hooks/useExecutionSessions';
import { usePendingApprovals } from '../hooks/usePendingApprovals';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableRow, TableHead, TableCell, TableBody } from '@/components/ui/Table';
import apiConfig from '@/lib/api-config';
import { authFetch } from '@/lib/auth-fetch';

const tabConfig = [
  { id: 'active', label: 'Active Sessions', icon: BoltIcon },
  { id: 'approvals', label: 'Pending Approvals', icon: ShieldCheckIcon },
  { id: 'history', label: 'Recent History', icon: ClockIcon },
  { id: 'all', label: 'All Sessions', icon: CheckCircleIcon },
];

const humanStatus = (status: string) =>
  status.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());

export function ExecutionsSurface() {
  const [activeTab, setActiveTab] = useState('active');
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const { sessions, loading: sessionsLoading, error: sessionsError, refresh: refreshSessions } =
    useExecutionSessions();
  const {
    approvals,
    loading: approvalsLoading,
    error: approvalsError,
    refresh: refreshApprovals,
  } = usePendingApprovals();

  const handleCancelSession = async (sessionId: number) => {
    if (!confirm('Cancel this execution? The session will be marked abandoned and will no longer run.')) return;
    setCancellingId(sessionId);
    try {
      const res = await authFetch(apiConfig.endpoints.agent.cancelSession(sessionId), { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || 'Failed to cancel');
      }
      await refreshSessions();
      await refreshApprovals();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to cancel session');
    } finally {
      setCancellingId(null);
    }
  };

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

  const renderActiveTab = () => (
    <div className="grid gap-4">
      {activeSessions.length === 0 ? (
        <Card>
          <CardContent padding="lg">
            <div className="text-center py-12">
              <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
                <BoltIcon className="h-8 w-8 text-neutral-400" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 mb-1">No active sessions</h3>
              <p className="text-sm text-neutral-600">All execution sessions are currently idle.</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        activeSessions.map((session) => (
          <Card key={session.id} hover variant="elevated">
            <CardContent padding="md">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                <div className="text-left">
                  <p className="text-xs uppercase tracking-widest text-neutral-500 font-semibold mb-1">Runbook</p>
                  <p className="text-lg font-semibold text-neutral-900">
                    {session.runbook_title || `Runbook #${session.runbook_id}`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="status" status={session.status as any} size="sm">
                    {humanStatus(session.status)}
                  </Badge>
                  <button
                    type="button"
                    onClick={() => handleCancelSession(session.id)}
                    disabled={cancellingId === session.id}
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 disabled:opacity-50"
                    title="Cancel execution (clear stuck runs)"
                  >
                    <XCircleIcon className="h-4 w-4" />
                    {cancellingId === session.id ? 'Cancelling…' : 'Cancel'}
                  </button>
                </div>
              </div>
              {session.issue_description && (
                <p className="mb-3 text-sm text-neutral-600 text-left">{session.issue_description}</p>
              )}
              <div className="flex flex-wrap gap-4 text-xs text-neutral-500">
                <span className="font-medium">Session #{session.id}</span>
                {session.ticket_id && <span className="font-medium">Ticket #{session.ticket_id}</span>}
                {session.started_at && (
                  <span>
                    Started {formatDistanceToNow(new Date(session.started_at), { addSuffix: true })}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );

  const renderApprovalsTab = () => (
    <div className="grid gap-4">
      {approvals.length === 0 ? (
        <Card>
          <CardContent padding="lg">
            <div className="text-center py-12">
              <div className="mx-auto w-16 h-16 rounded-full bg-success-100 flex items-center justify-center mb-4">
                <ShieldCheckIcon className="h-8 w-8 text-success-600" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 mb-1">No approvals waiting</h3>
              <p className="text-sm text-neutral-600">The agent is moving smoothly.</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        approvals.map((approval) => (
          <Card
            key={`${approval.session_id}-${approval.step_number}`}
            variant="gradient"
            className="border-secondary-200 bg-gradient-to-br from-secondary-50 to-primary-50"
          >
            <CardContent padding="md">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                <div className="text-left">
                  <p className="text-xs uppercase tracking-widest text-secondary-600 font-semibold mb-1">Approval Required</p>
                  <p className="text-lg font-semibold text-neutral-900">
                    {approval.runbook_title || `Runbook #${approval.runbook_id}`}
                  </p>
                </div>
                <Badge variant="secondary" size="sm">
                  Step {approval.step_number} · {approval.step_type}
                </Badge>
              </div>
              <div className="mb-3 rounded-lg bg-white p-3 border border-neutral-200">
                <p className="text-sm text-neutral-700 text-left font-mono">{approval.command}</p>
              </div>
              <div className="flex flex-wrap gap-4 text-xs text-neutral-600">
                <span className="font-medium">Session #{approval.session_id}</span>
                {approval.issue_description && <span>{approval.issue_description}</span>}
                <span>
                  Requested {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                </span>
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );

  const renderHistoryTab = () => (
    <div className="grid gap-3">
      {historySessions.length === 0 ? (
        <Card>
          <CardContent padding="lg">
            <div className="text-center py-12">
              <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
                <ClockIcon className="h-8 w-8 text-neutral-400" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 mb-1">No execution history</h3>
              <p className="text-sm text-neutral-600">No executions have been recorded yet.</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        historySessions.map((session) => (
          <Card key={session.id} hover variant="default">
            <CardContent padding="sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-left flex-1 min-w-0">
                  <p className="font-semibold text-neutral-900 mb-1">
                    {session.runbook_title || `Runbook #${session.runbook_id}`}
                  </p>
                  <p className="text-xs text-neutral-500">
                    Session #{session.id} •{' '}
                    {session.started_at
                      ? formatDistanceToNow(new Date(session.started_at), { addSuffix: true })
                      : 'Time unknown'}
                  </p>
                </div>
                <Badge variant="status" status={session.status as any} size="sm">
                  {humanStatus(session.status)}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );

  const renderAllTab = () => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Runbook</TableHead>
          <TableHead>Ticket</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Started</TableHead>
          <TableHead>Duration</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sessions.length === 0 ? (
          <TableRow>
            <TableCell colSpan={5} className="text-center py-12">
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
                  <CheckCircleIcon className="h-8 w-8 text-neutral-400" />
                </div>
                <p className="text-sm text-neutral-600">No sessions found</p>
              </div>
            </TableCell>
          </TableRow>
        ) : (
          sessions.map((session) => (
            <TableRow key={session.id} hover>
              <TableCell>
                <p className="font-semibold text-neutral-900">
                  {session.runbook_title || `Runbook #${session.runbook_id}`}
                </p>
                <p className="text-xs text-neutral-500">Session #{session.id}</p>
              </TableCell>
              <TableCell>
                <span className="text-xs text-neutral-600">
                  {session.ticket_id ? `#${session.ticket_id}` : '—'}
                </span>
              </TableCell>
              <TableCell>
                <Badge variant="status" status={session.status as any} size="sm">
                  {humanStatus(session.status)}
                </Badge>
              </TableCell>
              <TableCell>
                <span className="text-xs text-neutral-600">
                  {session.started_at
                    ? new Date(session.started_at).toLocaleString()
                    : 'Not started'}
                </span>
              </TableCell>
              <TableCell>
                <span className="text-xs text-neutral-600">
                  {session.total_duration_minutes != null
                    ? `${session.total_duration_minutes} min`
                    : '—'}
                </span>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );

  const renderContent = () => {
    if (sessionsError || approvalsError) {
      return (
        <Card variant="outlined" className="border-error-200 bg-error-50">
          <CardContent padding="md">
            <div className="flex items-center gap-3">
              <ExclamationTriangleIcon className="h-5 w-5 text-error-600 flex-shrink-0" />
              <p className="text-error-700 text-sm">{sessionsError || approvalsError}</p>
            </div>
          </CardContent>
        </Card>
      );
    }

    if (sessionsLoading || approvalsLoading) {
      return (
        <Card>
          <CardContent padding="lg">
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <span className="ml-3 text-neutral-600 font-medium">Syncing execution data...</span>
            </div>
          </CardContent>
        </Card>
      );
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
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-neutral-500 font-bold mb-1">Executions</p>
          <h2 className="text-3xl font-bold text-neutral-900 mb-1">Execution Control Surface</h2>
          <p className="text-sm text-neutral-600">
            Monitor live sessions, approve interventions, and review history.
          </p>
        </div>
        <button
          onClick={() => {
            refreshSessions();
            refreshApprovals();
          }}
          className="flex items-center gap-2 rounded-xl border-2 border-primary-200 bg-white px-4 py-2 text-sm font-semibold text-primary-700 hover:border-primary-300 hover:bg-primary-50 transition-all duration-200 shadow-sm hover:shadow-md"
        >
          <ArrowPathIcon className="h-4 w-4" />
          Refresh data
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        {tabConfig.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all duration-200 border-2 shadow-sm ${
                isActive
                  ? 'bg-gradient-to-r from-primary-50 to-secondary-50 text-primary-700 border-primary-300 shadow-md'
                  : 'border-neutral-200 text-neutral-600 hover:border-primary-200 hover:bg-primary-50/30 hover:shadow-md'
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


