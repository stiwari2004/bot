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
        return 'bg-green-100 text-green-800';
      case 'failed':
      case 'abandoned':
        return 'bg-red-100 text-red-800';
      case 'in_progress':
      case 'waiting_approval':
        return 'bg-blue-100 text-blue-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
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
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Execution Sessions</h2>
          <p className="text-sm text-gray-600 mt-1">Monitor and manage running commands and sessions</p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="waiting_approval">Waiting Approval</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="abandoned">Abandoned</option>
          </select>
          <button
            onClick={fetchSessions}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
          <span className="text-red-800">{error}</span>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Loading sessions...</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-600">No sessions found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sessions List */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Sessions ({sessions.length})</h3>
            <div className="space-y-3">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-all ${
                    selectedSession === session.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
                  }`}
                  onClick={() => setSelectedSession(session.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        {getStatusIcon(session.status)}
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(session.status)}`}>
                          {session.status}
                        </span>
                        {session.waiting_for_approval && (
                          <span className="px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                            Needs Approval
                          </span>
                        )}
                      </div>
                      <h4 className="font-semibold text-gray-900">{session.runbook_title}</h4>
                      <p className="text-sm text-gray-600 mt-1">
                        Session #{session.id} • Step {session.current_step}
                        {session.ticket_id && ` • Ticket #${session.ticket_id}`}
                      </p>
                      <div className="mt-2 text-xs text-gray-500">
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
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCancel(session.id);
                          }}
                          disabled={actionLoading === session.id}
                          className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                          title="Cancel session"
                        >
                          <XCircleIcon className="h-5 w-5" />
                        </button>
                      )}
                      {(session.status === 'completed' || session.status === 'failed' || session.status === 'abandoned') && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(session.id);
                          }}
                          disabled={actionLoading === session.id}
                          className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                          title="Delete session"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Session Details */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Session Details</h3>
              {selectedSession && (
                <button
                  onClick={() => {
                    setSelectedSession(null);
                    setSessionSteps([]);
                  }}
                  className="p-1 text-gray-400 hover:text-gray-600"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              )}
            </div>
            {selectedSession ? (
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-900 mb-2">Steps ({sessionSteps.length})</h4>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {sessionSteps.length === 0 ? (
                      <p className="text-sm text-gray-500">No steps found</p>
                    ) : (
                      sessionSteps.map((step) => (
                        <div
                          key={step.id}
                          className="p-3 border border-gray-200 rounded-lg bg-white"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-gray-700">
                                Step {step.step_number} ({step.step_type})
                              </span>
                              {step.completed && (
                                <span className={`px-2 py-0.5 rounded text-xs ${
                                  step.success
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-red-100 text-red-800'
                                }`}>
                                  {step.success ? 'Success' : 'Failed'}
                                </span>
                              )}
                              {!step.completed && (
                                <span className="px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-800">
                                  {step.approved === null && step.requires_approval
                                    ? 'Pending Approval'
                                    : 'Running'}
                                </span>
                              )}
                            </div>
                          </div>
                          {step.command && (
                            <div className="mb-2">
                              <p className="text-xs text-gray-500 mb-1">Command:</p>
                              <code className="text-xs bg-gray-50 p-2 rounded block font-mono">
                                {step.command}
                              </code>
                            </div>
                          )}
                          {step.notes && (
                            <p className="text-xs text-gray-600 mb-2">{step.notes}</p>
                          )}
                          {step.output && (
                            <div className="mb-2">
                              <p className="text-xs text-gray-500 mb-1">Output:</p>
                              <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto max-h-32">
                                {step.output}
                              </pre>
                            </div>
                          )}
                          {step.error && (
                            <div className="mb-2">
                              <p className="text-xs text-red-500 mb-1">Error:</p>
                              <pre className="text-xs bg-red-50 p-2 rounded overflow-x-auto max-h-32 text-red-800">
                                {step.error}
                              </pre>
                            </div>
                          )}
                          {step.completed_at && (
                            <p className="text-xs text-gray-500">
                              Completed: {formatDate(step.completed_at)}
                            </p>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="border border-gray-200 rounded-lg p-12 text-center bg-gray-50">
                <p className="text-gray-500">Select a session to view details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}




