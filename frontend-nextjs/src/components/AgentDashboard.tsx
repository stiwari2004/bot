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
import { authFetch } from '@/lib/auth-fetch';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

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
      const response = await authFetch(apiConfig.endpoints.agent.pendingApprovals());
      if (!response.ok) {
        const errorText = await response.text().catch(() => '');
        throw new Error(`Failed to fetch pending approvals: ${response.status} ${errorText || ''}`);
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
      const response = await authFetch(
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
      const response = await authFetch(apiConfig.endpoints.agent.execution(sessionId));
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
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            <span className="ml-3 text-neutral-600 font-medium">Loading pending approvals...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-error-600" />
            <p className="text-error-800 font-medium">Error loading approvals</p>
          </div>
          <p className="text-error-700 mt-2 text-sm">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (pendingApprovals.length === 0) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="text-center py-12">
            <div className="p-1.5 rounded-lg bg-primary-100 mx-auto mb-4 w-fit">
              <CheckCircleIcon className="h-12 w-12 text-primary-600" />
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">No Pending Approvals</h3>
            <p className="text-neutral-600 text-sm">
              All execution sessions are running smoothly. No approvals needed at this time.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center mb-2">
                <div className="p-1.5 rounded-lg bg-secondary-100 mr-3">
                  <ExclamationTriangleIcon className="h-6 w-6 text-secondary-600" />
                </div>
                <h2 className="text-2xl font-semibold text-neutral-900">Agent Execution Dashboard</h2>
              </div>
              <p className="text-sm text-neutral-600">Review and approve execution steps</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-error-100 text-error-800 rounded-full text-sm font-medium">
                {pendingApprovals.length} Pending
              </span>
            </div>
          </div>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 gap-4">
        {pendingApprovals.map((approval) => (
          <Card
            key={approval.session_id}
            variant="elevated"
            className="hover:border-primary-300 transition-colors"
          >
            <CardContent padding="md">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <ExclamationTriangleIcon className="h-5 w-5 text-warning-500" />
                    <h3 className="text-lg font-semibold text-neutral-900">
                      {approval.runbook_title}
                    </h3>
                  </div>
                  
                  <p className="text-neutral-600 text-sm mb-4">{approval.issue_description}</p>
                  
                  <Card variant="default" className="bg-neutral-50 mb-4">
                    <CardContent padding="sm">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-semibold text-neutral-500 uppercase">
                          Step {approval.step_number}
                        </span>
                        <span className="text-xs px-2 py-1 bg-primary-100 text-primary-800 rounded capitalize">
                          {approval.step_type}
                        </span>
                      </div>
                      <code className="text-sm text-neutral-800 block bg-white p-2 rounded border border-neutral-200">
                        {approval.command}
                      </code>
                    </CardContent>
                  </Card>
                  
                  <div className="flex items-center gap-2 text-xs text-neutral-500">
                    <ClockIcon className="h-4 w-4" />
                    <span>
                      {new Date(approval.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-3 mt-6 pt-6 border-t border-neutral-200">
                <Button
                  variant="success"
                  onClick={() => handleApprove(approval.session_id, approval.step_number, true)}
                  leftIcon={<CheckCircleIcon className="h-5 w-5" />}
                  className="flex-1"
                >
                  Approve & Continue
                </Button>
                <Button
                  variant="danger"
                  onClick={() => handleApprove(approval.session_id, approval.step_number, false)}
                  leftIcon={<XCircleIcon className="h-5 w-5" />}
                  className="flex-1"
                >
                  Reject & Stop
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setSelectedSession(approval.session_id)}
                  rightIcon={<ArrowRightIcon className="h-4 w-4" />}
                >
                  View Details
                </Button>
              </div>
            </CardContent>
          </Card>
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
      const response = await authFetch(apiConfig.endpoints.agent.execution(sessionId));
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
        <Card variant="elevated">
          <CardContent padding="lg">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          </CardContent>
        </Card>
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
          className="fixed inset-0 transition-opacity bg-neutral-500 bg-opacity-75"
          onClick={onClose}
        />
        
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-6xl sm:w-full">
          <Card variant="elevated" className="border-0 shadow-xl">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h3 className="text-xl font-semibold text-neutral-900">Execution Session #{sessionId}</h3>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    execution?.status === 'completed' ? 'bg-success-100 text-success-800' :
                    execution?.status === 'failed' ? 'bg-error-100 text-error-800' :
                    execution?.status === 'waiting_approval' ? 'bg-warning-100 text-warning-800' :
                    'bg-primary-100 text-primary-800'
                  }`}>
                    {execution?.status || 'loading'}
                  </span>
                  <div className="flex items-center gap-2">
                    <div className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-success-500' : 'bg-error-500'}`} />
                    <span className="text-xs text-neutral-500">
                      {wsConnected ? 'Live' : 'Disconnected'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1 border-2 border-neutral-300 rounded-lg">
                    <Button
                      variant={viewMode === 'detailed' ? 'primary' : 'ghost'}
                      size="sm"
                      onClick={() => setViewMode('detailed')}
                      className="rounded-l-lg rounded-r-none"
                    >
                      Detailed
                    </Button>
                    <Button
                      variant={viewMode === 'summary' ? 'primary' : 'ghost'}
                      size="sm"
                      onClick={() => setViewMode('summary')}
                      className="rounded-r-lg rounded-l-none"
                    >
                      Summary
                    </Button>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                  >
                    <XCircleIcon className="h-6 w-6" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent padding="md">
            
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
                      <Card
                        key={step.step_number}
                        variant="elevated"
                        className={`${
                          stepState.status === 'executing' ? 'border-primary-400 bg-primary-50' :
                          stepState.status === 'completed' ? 'border-success-300 bg-success-50' :
                          stepState.status === 'failed' ? 'border-error-300 bg-error-50' :
                          ''
                        }`}
                      >
                        <CardContent padding="md">
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-neutral-900">
                                  Step {step.step_number}
                                </span>
                                <span className="text-xs px-2 py-1 bg-neutral-100 text-neutral-700 rounded capitalize">
                                  {stepState.step_type}
                                </span>
                                {stepState.status === 'executing' && (
                                  <div className="flex items-center gap-1 text-primary-600">
                                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-primary-600" />
                                    <span className="text-xs font-medium">Executing...</span>
                                  </div>
                                )}
                                {stepState.status === 'completed' && (
                                  <div className="flex items-center gap-1 text-success-600">
                                    <CheckCircleIcon className="h-4 w-4" />
                                    <span className="text-xs font-medium">Completed</span>
                                  </div>
                                )}
                                {stepState.status === 'failed' && (
                                  <div className="flex items-center gap-1 text-error-600">
                                    <XCircleIcon className="h-4 w-4" />
                                    <span className="text-xs font-medium">Failed</span>
                                  </div>
                                )}
                                {stepState.duration_ms && (
                                  <span className="text-xs text-neutral-500">
                                    ({formatDuration(stepState.duration_ms)})
                                  </span>
                                )}
                              </div>
                              {stepState.description && (
                                <p className="text-sm text-neutral-600 mb-2">{stepState.description}</p>
                              )}
                            </div>
                          </div>
                          
                          <div className="bg-neutral-900 text-success-400 p-3 rounded font-mono text-xs mb-2">
                            <div className="text-neutral-400 mb-1">$ {stepState.command}</div>
                          </div>
                          
                          {stepState.output && (
                            <div className="mt-2">
                              <div className="text-xs font-semibold text-neutral-700 mb-1">Output:</div>
                              <div
                                ref={(el) => {
                                  if (el) outputRefs.current.set(step.step_number, el);
                                }}
                                className="bg-neutral-900 text-neutral-100 p-3 rounded font-mono text-xs max-h-48 overflow-y-auto"
                              >
                                <pre className="whitespace-pre-wrap">{stepState.output}</pre>
                              </div>
                            </div>
                          )}
                          
                          {stepState.error && (
                            <div className="mt-2">
                              <div className="text-xs font-semibold text-error-700 mb-1">Error:</div>
                              <div className="bg-error-50 border border-error-200 text-error-800 p-3 rounded font-mono text-xs max-h-48 overflow-y-auto">
                                <pre className="whitespace-pre-wrap">{stepState.error}</pre>
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              ) : (
                <div className="space-y-4">
                  <Card variant="default" className="bg-neutral-50">
                    <CardContent padding="md">
                      <h4 className="font-semibold text-neutral-900 mb-3">Summary</h4>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-neutral-600">Total Steps:</span>
                          <span className="ml-2 font-semibold">{execution?.steps?.length || 0}</span>
                        </div>
                        <div>
                          <span className="text-neutral-600">Duration:</span>
                          <span className="ml-2 font-semibold">
                            {execution?.total_duration_minutes 
                              ? `${execution.total_duration_minutes} minutes`
                              : 'N/A'}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <div>
                    <h4 className="font-semibold text-neutral-900 mb-2">Post-Checks</h4>
                    <div className="space-y-2">
                      {execution?.steps?.filter((s: any) => s.step_type === 'postcheck').map((step: any) => (
                        <Card key={step.step_number} variant="default">
                          <CardContent padding="sm">
                            <div className="flex items-center justify-between">
                              <span className="text-sm">{step.notes || 'Post-check'}</span>
                              {step.completed ? (
                                step.success ? (
                                  <CheckCircleIcon className="h-5 w-5 text-success-500" />
                                ) : (
                                  <XCircleIcon className="h-5 w-5 text-error-500" />
                                )
                              ) : (
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600" />
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}


