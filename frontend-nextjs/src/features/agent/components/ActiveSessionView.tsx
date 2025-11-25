'use client';

import { CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';
import { useActiveSession, type StepExecutionState } from '../hooks/useActiveSession';

interface ActiveSessionViewProps {
  sessionId: number;
}

export function ActiveSessionView({ sessionId }: ActiveSessionViewProps) {
  const {
    execution,
    loading,
    error,
    stepStates,
    wsConnected,
    eventLog,
    outputRefs,
    formatDuration,
  } = useActiveSession(sessionId);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-gray-600">Loading execution session...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center gap-2">
          <XCircleIcon className="h-5 w-5 text-red-600" />
          <p className="text-red-800 font-medium">Error loading session</p>
        </div>
        <p className="text-red-700 mt-2 text-sm">{error}</p>
      </div>
    );
  }

  if (!execution) {
    return (
      <div className="p-6 text-center text-gray-500">
        <p>No execution session found</p>
      </div>
    );
  }

  // Debug: Log current state
  console.log('[ActiveSessionView] Render:', {
    sessionId,
    execution,
    stepStatesSize: stepStates.size,
    wsConnected,
    steps: execution?.steps?.length,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Active Session #{sessionId}
            </h2>
            <p className="text-gray-600 mt-1">
              {execution.runbook_title || 'Execution Session'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className={`h-3 w-3 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-sm text-gray-600">
                {wsConnected ? 'Live' : 'Disconnected - Polling'}
              </span>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              execution.status === 'completed' ? 'bg-green-100 text-green-800' :
              execution.status === 'failed' ? 'bg-red-100 text-red-800' :
              execution.status === 'waiting_approval' ? 'bg-yellow-100 text-yellow-800' :
              'bg-blue-100 text-blue-800'
            }`}>
              {execution.status}
            </span>
          </div>
        </div>
        {execution.issue_description && (
          <p className="text-gray-700 mt-3">{execution.issue_description}</p>
        )}
      </div>

      {/* Command Execution Telemetry */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Command Execution</h3>
        <div className="space-y-4 max-h-[60vh] overflow-y-auto">
          {execution.steps?.map((step: any) => {
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
                {/* Step Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-gray-900">
                        Step {stepState.step_number}
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
                
                {/* Command */}
                <div className="bg-gray-900 text-green-400 p-3 rounded font-mono text-xs mb-3">
                  <div className="text-gray-400 mb-1">$ {stepState.command}</div>
                </div>
                
                {/* Output - Always show if executing, completed, failed, or has output */}
                {(stepState.status === 'executing' || stepState.status === 'completed' || stepState.status === 'failed' || stepState.output) && (
                  <div className="mb-3">
                    <div className="text-xs font-semibold text-gray-700 mb-1">
                      Response {stepState.status === 'executing' && !stepState.output && '(Waiting for output...)'}:
                    </div>
                    <div
                      ref={(el) => {
                        if (el) outputRefs.current.set(step.step_number, el);
                      }}
                      className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs max-h-48 overflow-y-auto min-h-[100px]"
                    >
                      {stepState.output ? (
                        <pre className="whitespace-pre-wrap">{stepState.output}</pre>
                      ) : stepState.status === 'executing' ? (
                        <div className="text-gray-500 italic flex items-center gap-2">
                          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-500"></div>
                          Waiting for command output...
                        </div>
                      ) : (
                        <div className="text-gray-500 italic">No output yet</div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Error */}
                {stepState.error && (
                  <div>
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
      </div>

      {/* Debug Panel - Show recent events */}
      {process.env.NODE_ENV === 'development' && (
        <div className="border-t border-gray-200 pt-4">
          <details className="text-sm">
            <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
              Debug: Recent Events ({eventLog.length})
            </summary>
            <div className="mt-2 bg-gray-50 rounded p-3 max-h-48 overflow-y-auto font-mono text-xs">
              {eventLog.length === 0 ? (
                <div className="text-gray-500">No events received yet</div>
              ) : (
                eventLog.slice(-10).map((log, idx) => (
                  <div key={idx} className="mb-2 border-b border-gray-200 pb-2">
                    <div className="text-gray-500">{log.timestamp}</div>
                    <pre className="text-xs mt-1">{JSON.stringify(log.data, null, 2)}</pre>
                  </div>
                ))
              )}
            </div>
          </details>
        </div>
      )}

      {/* Step Status Summary - Bottom */}
      <div className="border-t border-gray-200 pt-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Step Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {execution.steps?.map((step: any) => {
            const stepState = stepStates.get(step.step_number);
            const status = stepState?.status || (step.completed 
              ? (step.success ? 'completed' : 'failed')
              : (step.step_number === execution.current_step ? 'executing' : 'pending'));

            return (
              <div
                key={step.step_number}
                className="border border-gray-200 rounded-lg p-3"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">
                    Step {step.step_number}
                  </span>
                  {status === 'executing' && (
                    <ClockIcon className="h-5 w-5 text-blue-500 animate-pulse" />
                  )}
                  {status === 'completed' && (
                    <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  )}
                  {status === 'failed' && (
                    <XCircleIcon className="h-5 w-5 text-red-500" />
                  )}
                  {status === 'pending' && (
                    <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
                  )}
                </div>
                <div className="text-xs text-gray-600 truncate" title={step.command}>
                  {step.command}
                </div>
                {stepState?.duration_ms && (
                  <div className="text-xs text-gray-500 mt-1">
                    Duration: {formatDuration(stepState.duration_ms)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

