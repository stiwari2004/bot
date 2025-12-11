'use client';

import { useState, useEffect } from 'react';
import { 
  TrashIcon, 
  XCircleIcon, 
  PlayIcon, 
  CheckCircleIcon,
  XMarkIcon,
  ClockIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface Session {
  id: number;
  runbook_id: number;
  runbook_title: string;
  ticket_id: number | null;
  status: string;
  current_step: number;
  waiting_for_approval: boolean;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  total_duration_minutes: number | null;
}

interface Step {
  id: number;
  step_number: number;
  step_type: string;
  command: string;
  notes: string | null;
  requires_approval: boolean;
  approved: boolean | null;
  completed: boolean;
  success: boolean | null;
  output: string | null;
  error: string | null;
  completed_at: string | null;
  created_at: string;
}

export function SessionManager() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<number | null>(null);
  const [sessionSteps, setSessionSteps] = useState<Step[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const url = apiConfig.endpoints.agent.sessions(filterStatus === 'all' ? undefined : filterStatus);
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.statusText}`);
      }
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch sessions');
      console.error('Error fetching sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSessionSteps = async (sessionId: number) => {
    try {
      const response = await fetch(apiConfig.endpoints.agent.sessionSteps(sessionId));
      if (!response.ok) {
        throw new Error(`Failed to fetch steps: ${response.statusText}`);
      }
      const data = await response.json();
      setSessionSteps(data.steps || []);
    } catch (err) {
      console.error('Error fetching session steps:', err);
      setSessionSteps([]);
    }
  };

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [filterStatus]);

  useEffect(() => {
    if (selectedSession) {
      fetchSessionSteps(selectedSession);
      const interval = setInterval(() => fetchSessionSteps(selectedSession), 3000);
      return () => clearInterval(interval);
    }
  }, [selectedSession]);

  const handleCancel = async (sessionId: number) => {
    if (!confirm('Are you sure you want to cancel this session?')) {
      return;
    }
    try {
      setActionLoading(sessionId);
      const response = await fetch(apiConfig.endpoints.agent.cancelSession(sessionId), {
        method: 'POST',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to cancel session');
      }
      await fetchSessions();
      if (selectedSession === sessionId) {
        setSelectedSession(null);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to cancel session');
      console.error('Error cancelling session:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (sessionId: number) => {
    if (!confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
      return;
    }
    try {
      setActionLoading(sessionId);
      const response = await fetch(apiConfig.endpoints.agent.deleteSession(sessionId), {
        method: 'DELETE',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete session');
      }
      await fetchSessions();
      if (selectedSession === sessionId) {
        setSelectedSession(null);
        setSessionSteps([]);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete session');
      console.error('Error deleting session:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-success-100 text-success-800';
      case 'failed':
      case 'abandoned':
        return 'bg-error-100 text-error-800';
      case 'in_progress':
      case 'waiting_approval':
        return 'bg-primary-100 text-primary-800';
      case 'pending':
        return 'bg-warning-100 text-warning-800';
      default:
        return 'bg-neutral-100 text-neutral-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-600" />;
      case 'failed':
      case 'abandoned':
        return <XCircleIcon className="h-5 w-5 text-red-600" />;
      case 'in_progress':
        return <PlayIcon className="h-5 w-5 text-blue-600" />;
      case 'waiting_approval':
        return <ClockIcon className="h-5 w-5 text-yellow-600" />;
      default:
        return <ClockIcon className="h-5 w-5 text-gray-600" />;
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (minutes: number | null) => {
    if (!minutes) return '—';
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  return (
    <div className="space-y-6">
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center mb-2">
                <div className="p-1.5 rounded-lg bg-secondary-100 mr-3">
                  <PlayIcon className="h-6 w-6 text-secondary-600" />
                </div>
                <h2 className="text-2xl font-semibold text-neutral-900">Execution Sessions</h2>
              </div>
              <p className="text-sm text-neutral-600">Monitor and manage running commands and sessions</p>
            </div>
            <div className="flex items-center gap-4">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2 border-2 border-neutral-300 rounded-lg text-sm font-medium text-neutral-900 bg-white hover:border-primary-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
              >
                <option value="all">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="waiting_approval">Waiting Approval</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="abandoned">Abandoned</option>
              </select>
              <Button variant="primary" size="sm" onClick={fetchSessions}>
                Refresh
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {error && (
        <Card variant="elevated">
          <CardContent padding="md">
            <div className="flex items-center gap-2">
              <ExclamationTriangleIcon className="h-5 w-5 text-error-600" />
              <span className="text-error-800">{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <Card variant="elevated">
          <CardContent padding="lg">
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <span className="ml-3 text-neutral-600 font-medium">Loading sessions...</span>
            </div>
          </CardContent>
        </Card>
      ) : sessions.length === 0 ? (
        <Card variant="elevated">
          <CardContent padding="lg">
            <div className="text-center py-12">
              <p className="text-neutral-600">No sessions found</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sessions List */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-neutral-900">Sessions ({sessions.length})</h3>
            <div className="space-y-3">
              {sessions.map((session) => (
                <Card
                  key={session.id}
                  variant={selectedSession === session.id ? "default" : "default"}
                  className={`cursor-pointer transition-all ${
                    selectedSession === session.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'hover:border-primary-300'
                  }`}
                  onClick={() => setSelectedSession(session.id)}
                >
                  <CardContent padding="md">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          {getStatusIcon(session.status)}
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(session.status)}`}>
                            {session.status}
                          </span>
                          {session.waiting_for_approval && (
                            <span className="px-2 py-1 rounded text-xs font-medium bg-warning-100 text-warning-800">
                              Needs Approval
                            </span>
                          )}
                        </div>
                        <h4 className="font-semibold text-neutral-900">{session.runbook_title}</h4>
                        <p className="text-sm text-neutral-600 mt-1">
                          Session #{session.id} • Step {session.current_step}
                          {session.ticket_id && ` • Ticket #${session.ticket_id}`}
                        </p>
                        <div className="mt-2 text-xs text-neutral-500">
                          <div>Created: {formatDate(session.created_at)}</div>
                          {session.started_at && <div>Started: {formatDate(session.started_at)}</div>}
                          {session.completed_at && <div>Completed: {formatDate(session.completed_at)}</div>}
                          {session.total_duration_minutes && (
                            <div>Duration: {formatDuration(session.total_duration_minutes)}</div>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2 ml-4">
                        {(session.status === 'in_progress' || session.status === 'pending' || session.status === 'waiting_approval') && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCancel(session.id);
                            }}
                            disabled={actionLoading === session.id}
                            title="Cancel session"
                          >
                            <XCircleIcon className="h-5 w-5" />
                          </Button>
                        )}
                        {(session.status === 'completed' || session.status === 'failed' || session.status === 'abandoned') && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(session.id);
                            }}
                            disabled={actionLoading === session.id}
                            title="Delete session"
                          >
                            <TrashIcon className="h-5 w-5" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Session Details */}
          <div className="space-y-4">
            <Card variant="elevated">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-neutral-900">Session Details</h3>
                  {selectedSession && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setSelectedSession(null);
                        setSessionSteps([]);
                      }}
                    >
                      <XMarkIcon className="h-5 w-5" />
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent padding="md">
                {selectedSession ? (
                  <div>
                    <div className="mb-4">
                      <h4 className="font-semibold text-neutral-900 mb-2">Steps ({sessionSteps.length})</h4>
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {sessionSteps.length === 0 ? (
                          <p className="text-sm text-neutral-500">No steps found</p>
                        ) : (
                          sessionSteps.map((step) => (
                            <Card key={step.id} variant="default" className="mb-2">
                              <CardContent padding="sm">
                                <div className="flex items-center justify-between mb-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm font-semibold text-neutral-700">
                                      Step {step.step_number} ({step.step_type})
                                    </span>
                                    {step.completed && (
                                      <span className={`px-2 py-0.5 rounded text-xs ${
                                        step.success
                                          ? 'bg-success-100 text-success-800'
                                          : 'bg-error-100 text-error-800'
                                      }`}>
                                        {step.success ? 'Success' : 'Failed'}
                                      </span>
                                    )}
                                    {!step.completed && (
                                      <span className="px-2 py-0.5 rounded text-xs bg-warning-100 text-warning-800">
                                        {step.approved === null && step.requires_approval
                                          ? 'Pending Approval'
                                          : 'Running'}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                {step.command && (
                                  <div className="mb-2">
                                    <p className="text-xs text-neutral-500 mb-1">Command:</p>
                                    <code className="text-xs bg-neutral-50 p-2 rounded block font-mono">
                                      {step.command}
                                    </code>
                                  </div>
                                )}
                                {step.notes && (
                                  <p className="text-xs text-neutral-600 mb-2">{step.notes}</p>
                                )}
                                {step.output && (
                                  <div className="mb-2">
                                    <p className="text-xs text-neutral-500 mb-1">Output:</p>
                                    <pre className="text-xs bg-neutral-50 p-2 rounded overflow-x-auto max-h-32">
                                      {step.output}
                                    </pre>
                                  </div>
                                )}
                                {step.error && (
                                  <div className="mb-2">
                                    <p className="text-xs text-error-500 mb-1">Error:</p>
                                    <pre className="text-xs bg-error-50 p-2 rounded overflow-x-auto max-h-32 text-error-800">
                                      {step.error}
                                    </pre>
                                  </div>
                                )}
                                {step.completed_at && (
                                  <p className="text-xs text-neutral-500">
                                    Completed: {formatDate(step.completed_at)}
                                  </p>
                                )}
                              </CardContent>
                            </Card>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <p className="text-neutral-500">Select a session to view details</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}










