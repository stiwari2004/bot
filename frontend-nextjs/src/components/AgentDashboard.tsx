/**
 * Agent Execution Dashboard - Pending Approvals
 * Displays all execution sessions waiting for human approval
 */
'use client';

import { useState, useEffect, useRef } from 'react';
import {
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
  PlayIcon,
  StopIcon,
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

interface StepExecutionState {
  step_number: number;
  step_type: string;
  command: string;
  description: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  output: string;
  error: string;
  duration_ms?: number;
  started_at?: string;
  completed_at?: string;
}

function ExecutionDetailView({ sessionId, onClose }: ExecutionDetailViewProps) {
  const [execution, setExecution] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'detailed' | 'summary'>('detailed');
  const [stepStates, setStepStates] = useState<Map<number, StepExecutionState>>(new Map());
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const outputRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Fetch initial execution status
  useEffect(() => {
    fetchExecutionStatus();
  }, [sessionId]);

  // WebSocket connection for real-time events
  useEffect(() => {
    if (!sessionId) return;

    const toWebSocketUrl = (baseUrl: string) => {
      if (baseUrl.startsWith('https://')) {
        return `wss://${baseUrl.slice('https://'.length)}`;
      }
      if (baseUrl.startsWith('http://')) {
        return `ws://${baseUrl.slice('http://'.length)}`;
      }
      return baseUrl;
    };

    const wsUrl = `${toWebSocketUrl(apiConfig.baseUrl)}/api/v1/executions/ws/sessions/${sessionId}`;
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    socket.onopen = () => {
      setWsConnected(true);
      console.log('WebSocket connected for session', sessionId);
    };

    socket.onclose = () => {
      setWsConnected(false);
      console.log('WebSocket disconnected for session', sessionId);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data);
        if (Array.isArray(data.events)) {
          data.events.forEach((event: any) => {
            handleExecutionEvent(event);
          });
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  const handleExecutionEvent = (event: any) => {
    const stepNumber = event.step_number || event.payload?.step_number;
    if (!stepNumber) return;

    setStepStates((prev) => {
      const newMap = new Map(prev);
      const current: StepExecutionState = newMap.get(stepNumber) || {
        step_number: stepNumber,
        step_type: event.payload?.step_type || 'main',
        command: event.payload?.command || '',
        description: event.payload?.description || '',
        status: 'pending' as const,
        output: '',
        error: '',
        duration_ms: undefined,
        started_at: undefined,
        completed_at: undefined,
      };

      switch (event.event || event.event_type) {
        case 'execution.step.started':
          newMap.set(stepNumber, {
            ...current,
            command: event.payload?.command || current.command,
            description: event.payload?.description || current.description,
            status: 'executing',
            started_at: event.timestamp || new Date().toISOString(),
          });
          break;
        case 'execution.step.output':
          newMap.set(stepNumber, {
            ...current,
            output: current.output + (event.payload?.output || ''),
          });
          // Auto-scroll output
          setTimeout(() => {
            const outputEl = outputRefs.current.get(stepNumber);
            if (outputEl) {
              outputEl.scrollTop = outputEl.scrollHeight;
            }
          }, 10);
          break;
        case 'execution.step.completed':
          newMap.set(stepNumber, {
            ...current,
            status: 'completed',
            output: event.payload?.output || current.output,
            duration_ms: event.payload?.duration_ms,
            completed_at: event.timestamp || new Date().toISOString(),
          });
          break;
        case 'execution.step.failed':
          newMap.set(stepNumber, {
            ...current,
            status: 'failed',
            output: event.payload?.output || current.output,
            error: event.payload?.error || '',
            duration_ms: event.payload?.duration_ms,
            completed_at: event.timestamp || new Date().toISOString(),
          });
          break;
      }

      return newMap;
    });
  };

  const fetchExecutionStatus = async () => {
    try {
      const response = await fetch(apiConfig.endpoints.agent.execution(sessionId));
      if (response.ok) {
        const data = await response.json();
        setExecution(data);
        
        // Initialize step states from execution data
        if (data.steps) {
          const initialStates = new Map<number, StepExecutionState>();
          data.steps.forEach((step: any) => {
            initialStates.set(step.step_number, {
              step_number: step.step_number,
              step_type: step.step_type || 'main',
              command: step.command || '',
              description: step.notes || '',
              status: step.completed 
                ? (step.success ? 'completed' : 'failed')
                : (step.step_number === data.current_step ? 'executing' : 'pending'),
              output: step.output || '',
              error: step.error || '',
              duration_ms: undefined,
              started_at: undefined,
              completed_at: undefined,
            });
          });
          setStepStates(initialStates);
        }
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

  const formatDuration = (ms?: number) => {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />
        
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-6xl sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <h3 className="text-xl font-semibold text-gray-900">Execution Session #{sessionId}</h3>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  execution?.status === 'completed' ? 'bg-green-100 text-green-800' :
                  execution?.status === 'failed' ? 'bg-red-100 text-red-800' :
                  execution?.status === 'waiting_approval' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {execution?.status || 'loading'}
                </span>
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="text-xs text-gray-500">
                    {wsConnected ? 'Live' : 'Disconnected'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 border border-gray-300 rounded-lg">
                  <button
                    onClick={() => setViewMode('detailed')}
                    className={`px-3 py-1 text-sm font-medium rounded-l-lg ${
                      viewMode === 'detailed'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Detailed
                  </button>
                  <button
                    onClick={() => setViewMode('summary')}
                    className={`px-3 py-1 text-sm font-medium rounded-r-lg ${
                      viewMode === 'summary'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Summary
                  </button>
                </div>
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-500"
                >
                  <XCircleIcon className="h-6 w-6" />
                </button>
              </div>
            </div>
            
            {viewMode === 'detailed' ? (
              <div className="space-y-4 max-h-[70vh] overflow-y-auto">
                {execution?.steps?.map((step: any) => {
                  const stepState: StepExecutionState = stepStates.get(step.step_number) || {
                    step_number: step.step_number,
                    step_type: step.step_type || 'main',
                    command: step.command || '',
                    description: step.notes || '',
                    status: step.completed 
                      ? (step.success ? 'completed' : 'failed')
                      : (step.step_number === execution.current_step ? 'executing' : 'pending'),
                    output: step.output || '',
                    error: step.error || '',
                    duration_ms: undefined,
                    started_at: undefined,
                    completed_at: undefined,
                  };

                  return (
                    <div
                      key={step.step_number}
                      className={`border rounded-lg p-4 ${
                        stepState.status === 'executing' ? 'border-blue-400 bg-blue-50' :
                        stepState.status === 'completed' ? 'border-green-300 bg-green-50' :
                        stepState.status === 'failed' ? 'border-red-300 bg-red-50' :
                        'border-gray-200 bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-gray-900">
                              Step {step.step_number}
                            </span>
                            <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded capitalize">
                              {stepState.step_type}
                            </span>
                            {stepState.status === 'executing' && (
                              <div className="flex items-center gap-1 text-blue-600">
                                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600" />
                                <span className="text-xs font-medium">Executing...</span>
                              </div>
                            )}
                            {stepState.status === 'completed' && (
                              <div className="flex items-center gap-1 text-green-600">
                                <CheckCircleIcon className="h-4 w-4" />
                                <span className="text-xs font-medium">Completed</span>
                              </div>
                            )}
                            {stepState.status === 'failed' && (
                              <div className="flex items-center gap-1 text-red-600">
                                <XCircleIcon className="h-4 w-4" />
                                <span className="text-xs font-medium">Failed</span>
                              </div>
                            )}
                            {stepState.duration_ms && (
                              <span className="text-xs text-gray-500">
                                ({formatDuration(stepState.duration_ms)})
                              </span>
                            )}
                          </div>
                          {stepState.description && (
                            <p className="text-sm text-gray-600 mb-2">{stepState.description}</p>
                          )}
                        </div>
                      </div>
                      
                      <div className="bg-gray-900 text-green-400 p-3 rounded font-mono text-xs mb-2">
                        <div className="text-gray-400 mb-1">$ {stepState.command}</div>
                      </div>
                      
                      {stepState.output && (
                        <div className="mt-2">
                          <div className="text-xs font-semibold text-gray-700 mb-1">Output:</div>
                          <div
                            ref={(el) => {
                              if (el) outputRefs.current.set(step.step_number, el);
                            }}
                            className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs max-h-48 overflow-y-auto"
                          >
                            <pre className="whitespace-pre-wrap">{stepState.output}</pre>
                          </div>
                        </div>
                      )}
                      
                      {stepState.error && (
                        <div className="mt-2">
                          <div className="text-xs font-semibold text-red-700 mb-1">Error:</div>
                          <div className="bg-red-50 border border-red-200 text-red-800 p-3 rounded font-mono text-xs max-h-48 overflow-y-auto">
                            <pre className="whitespace-pre-wrap">{stepState.error}</pre>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3">Summary</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Total Steps:</span>
                      <span className="ml-2 font-medium">{execution?.steps?.length || 0}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Duration:</span>
                      <span className="ml-2 font-medium">
                        {execution?.total_duration_minutes 
                          ? `${execution.total_duration_minutes} minutes`
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Post-Checks</h4>
                  <div className="space-y-2">
                    {execution?.steps?.filter((s: any) => s.step_type === 'postcheck').map((step: any) => (
                      <div
                        key={step.step_number}
                        className="border border-gray-200 rounded-lg p-3"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm">{step.notes || 'Post-check'}</span>
                          {step.completed ? (
                            step.success ? (
                              <CheckCircleIcon className="h-5 w-5 text-green-500" />
                            ) : (
                              <XCircleIcon className="h-5 w-5 text-red-500" />
                            )
                          ) : (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


