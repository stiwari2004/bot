'use client';

import { useState, useEffect } from 'react';
import { 
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  EyeIcon
} from '@heroicons/react/24/outline';

interface ExecutionSession {
  id: number;
  runbook_id: number;
  runbook_title?: string;
  issue_description: string;
  status: string;
  started_at: string;
  completed_at?: string;
  total_duration_minutes?: number;
  steps_count?: number;
  feedback?: {
    was_successful: boolean | string;
    issue_resolved: boolean | string;
    rating?: number;
    feedback_text?: string;
  };
}

export function ExecutionHistory() {
  const [sessions, setSessions] = useState<ExecutionSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchExecutions();
  }, []);

  const fetchExecutions = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/executions/demo/executions?limit=50');
      
      if (!response.ok) {
        throw new Error('Failed to fetch execution history');
      }
      
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load execution history');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-6 w-6 text-green-600" />;
      case 'failed':
        return <XCircleIcon className="h-6 w-6 text-red-600" />;
      case 'in_progress':
        return <ClockIcon className="h-6 w-6 text-blue-600 animate-pulse" />;
      default:
        return <ClockIcon className="h-6 w-6 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'abandoned':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDuration = (minutes?: number) => {
    if (!minutes) return 'N/A';
    if (minutes < 60) return `${minutes}m`;
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hrs}h ${mins}m`;
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading execution history...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Execution History</h2>
        <p className="text-gray-600">View past runbook executions and their outcomes</p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {sessions.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No executions yet</h3>
          <p className="mt-2 text-gray-600">
            Start executing runbooks to see your history here
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="border border-gray-200 rounded-lg p-6 hover:border-blue-300 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  {getStatusIcon(session.status)}
                  
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {session.runbook_title || `Runbook #${session.runbook_id}`}
                      </h3>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadge(session.status)}`}>
                        {session.status}
                      </span>
                    </div>
                    
                    <p className="text-gray-600 mb-3">{session.issue_description}</p>
                    
                    <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                      <div className="flex items-center">
                        <ClockIcon className="h-4 w-4 mr-1" />
                        Started: {formatDate(session.started_at)}
                      </div>
                      {session.completed_at && (
                        <div className="flex items-center">
                          <CheckCircleIcon className="h-4 w-4 mr-1" />
                          Completed: {formatDate(session.completed_at)}
                        </div>
                      )}
                      {session.total_duration_minutes !== undefined && (
                        <div className="flex items-center">
                          Duration: {formatDuration(session.total_duration_minutes)}
                        </div>
                      )}
                      {session.steps_count !== undefined && (
                        <div className="flex items-center">
                          Steps: {session.steps_count}
                        </div>
                      )}
                    </div>

                    {/* Feedback Display */}
                    {session.feedback && (
                      <div className="mt-4 bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-gray-900">Feedback</span>
                          {session.feedback?.rating && (
                            <div className="flex items-center">
                              {[...Array(5)].map((_, i) => (
                                <span
                                  key={i}
                                  className={`text-lg ${
                                    i < (session.feedback?.rating || 0) 
                                      ? 'text-yellow-400' 
                                      : 'text-gray-300'
                                  }`}
                                >
                                  ★
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="flex space-x-4 text-sm">
                          <div className={`flex items-center ${
                            session.feedback.was_successful === true || session.feedback.was_successful === 'true' 
                              ? 'text-green-600' 
                              : 'text-red-600'
                          }`}>
                            {session.feedback.was_successful === true || session.feedback.was_successful === 'true' ? (
                              <CheckCircleIcon className="h-4 w-4 mr-1" />
                            ) : (
                              <XCircleIcon className="h-4 w-4 mr-1" />
                            )}
                            {session.feedback.was_successful === true || session.feedback.was_successful === 'true' 
                              ? 'Successful' 
                              : 'Unsuccessful'}
                          </div>
                          <div className={`flex items-center ${
                            session.feedback.issue_resolved === true || session.feedback.issue_resolved === 'true' 
                              ? 'text-green-600' 
                              : 'text-red-600'
                          }`}>
                            {session.feedback.issue_resolved === true || session.feedback.issue_resolved === 'true' ? (
                              <CheckCircleIcon className="h-4 w-4 mr-1" />
                            ) : (
                              <XCircleIcon className="h-4 w-4 mr-1" />
                            )}
                            {session.feedback.issue_resolved === true || session.feedback.issue_resolved === 'true' 
                              ? 'Resolved' 
                              : 'Not Resolved'}
                          </div>
                        </div>
                        {session.feedback.feedback_text && (
                          <p className="mt-2 text-sm text-gray-700">{session.feedback.feedback_text}</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Action Button */}
                <div className="ml-4">
                  <button
                    onClick={() => {
                      // Could navigate to detailed view in the future
                      alert(`View details for execution #${session.id}`);
                    }}
                    className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                  >
                    <EyeIcon className="h-5 w-5 text-gray-600" />
                    <span className="text-sm font-medium text-gray-700">View</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

