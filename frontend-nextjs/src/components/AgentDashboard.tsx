/**
 * Agent Execution Dashboard - Pending Approvals
 * Displays all execution sessions waiting for human approval
 */
'use client';

import { useState, useEffect } from 'react';
import {
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';

interface PendingApproval {
  session_id: number;
  runbook_id: number;
  runbook_title: string;
  step_number: number;
  step_type: string;
  command: string;
  issue_description: string;
  created_at: string;
}

export function AgentDashboard() {
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<number | null>(null);

  useEffect(() => {
    fetchPendingApprovals();
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchPendingApprovals, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchPendingApprovals = async () => {
    try {
      const response = await fetch(apiConfig.endpoints.agent.pendingApprovals());
      if (!response.ok) {
        throw new Error('Failed to fetch pending approvals');
      }
      const data = await response.json();
      setPendingApprovals(data.pending_approvals || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch approvals');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (sessionId: number, stepNumber: number, approve: boolean) => {
    try {
      const response = await fetch(
        apiConfig.endpoints.agent.approveStep(sessionId, stepNumber),
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ approve, notes: approve ? 'Approved' : 'Rejected' }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to ${approve ? 'approve' : 'reject'} step`);
      }

      // Refresh pending approvals
      await fetchPendingApprovals();
      
      // If viewing this session, refresh it
      if (selectedSession === sessionId) {
        fetchExecutionStatus(sessionId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process approval');
    }
  };

  const fetchExecutionStatus = async (sessionId: number) => {
    try {
      const response = await fetch(apiConfig.endpoints.agent.execution(sessionId));
      if (response.ok) {
        const data = await response.json();
        // Update local state if needed
      }
    } catch (err) {
      console.error('Failed to fetch execution status:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-gray-600">Loading pending approvals...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center gap-2">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
          <p className="text-red-800 font-medium">Error loading approvals</p>
        </div>
        <p className="text-red-700 mt-2 text-sm">{error}</p>
      </div>
    );
  }

  if (pendingApprovals.length === 0) {
    return (
      <div className="p-8 bg-blue-50 border border-blue-200 rounded-lg text-center">
        <CheckCircleIcon className="h-12 w-12 text-blue-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Pending Approvals</h3>
        <p className="text-gray-600 text-sm">
          All execution sessions are running smoothly. No approvals needed at this time.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Agent Execution Dashboard</h2>
          <p className="text-gray-600 mt-1">Review and approve execution steps</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">
            {pendingApprovals.length} Pending
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {pendingApprovals.map((approval) => (
          <div
            key={approval.session_id}
            className="bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
                    <h3 className="text-lg font-semibold text-gray-900">
                      {approval.runbook_title}
                    </h3>
                  </div>
                  
                  <p className="text-gray-600 text-sm mb-4">{approval.issue_description}</p>
                  
                  <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-semibold text-gray-500 uppercase">
                        Step {approval.step_number}
                      </span>
                      <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded capitalize">
                        {approval.step_type}
                      </span>
                    </div>
                    <code className="text-sm text-gray-800 block bg-white p-2 rounded border border-gray-200">
                      {approval.command}
                    </code>
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <ClockIcon className="h-4 w-4" />
                    <span>
                      {new Date(approval.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-3 mt-6 pt-6 border-t border-gray-200">
                <button
                  onClick={() => handleApprove(approval.session_id, approval.step_number, true)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                >
                  <CheckCircleIcon className="h-5 w-5" />
                  Approve & Continue
                </button>
                <button
                  onClick={() => handleApprove(approval.session_id, approval.step_number, false)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
                >
                  <XCircleIcon className="h-5 w-5" />
                  Reject & Stop
                </button>
                <button
                  onClick={() => setSelectedSession(approval.session_id)}
                  className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  View Details
                  <ArrowRightIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {selectedSession && (
        <ExecutionDetailView
          sessionId={selectedSession}
          onClose={() => setSelectedSession(null)}
        />
      )}
    </div>
  );
}

interface ExecutionDetailViewProps {
  sessionId: number;
  onClose: () => void;
}

function ExecutionDetailView({ sessionId, onClose }: ExecutionDetailViewProps) {
  const [execution, setExecution] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExecutionStatus();
    const interval = setInterval(fetchExecutionStatus, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const fetchExecutionStatus = async () => {
    try {
      const response = await fetch(apiConfig.endpoints.agent.execution(sessionId));
      if (response.ok) {
        const data = await response.json();
        setExecution(data);
      }
    } catch (err) {
      console.error('Failed to fetch execution status:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center">
        <div className="bg-white rounded-lg p-6">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        </div>
      </div>
    );
  }

  if (!execution) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />
        
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-gray-900">Execution Details</h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-500"
              >
                <XCircleIcon className="h-6 w-6" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Status</h4>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  execution.status === 'completed' ? 'bg-green-100 text-green-800' :
                  execution.status === 'failed' ? 'bg-red-100 text-red-800' :
                  execution.status === 'waiting_approval' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {execution.status}
                </span>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Steps</h4>
                <div className="space-y-2">
                  {execution.steps?.map((step: any) => (
                    <div
                      key={step.step_number}
                      className="border border-gray-200 rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">Step {step.step_number}</span>
                        <div className="flex items-center gap-2">
                          {step.completed && (
                            step.success ? (
                              <CheckCircleIcon className="h-5 w-5 text-green-500" />
                            ) : (
                              <XCircleIcon className="h-5 w-5 text-red-500" />
                            )
                          )}
                          {step.requires_approval && (
                            <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                              Requires Approval
                            </span>
                          )}
                        </div>
                      </div>
                      <code className="text-sm text-gray-700 block bg-gray-50 p-2 rounded mt-2">
                        {step.command}
                      </code>
                      {step.output && (
                        <div className="mt-2 text-sm text-gray-600">
                          <strong>Output:</strong>
                          <pre className="bg-gray-50 p-2 rounded mt-1 text-xs overflow-x-auto">
                            {step.output}
                          </pre>
                        </div>
                      )}
                      {step.error && (
                        <div className="mt-2 text-sm text-red-600">
                          <strong>Error:</strong>
                          <pre className="bg-red-50 p-2 rounded mt-1 text-xs overflow-x-auto">
                            {step.error}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


