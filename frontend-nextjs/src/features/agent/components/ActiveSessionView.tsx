'use client';

import { CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';
import { useActiveSession, type StepExecutionState } from '../hooks/useActiveSession';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <div className="text-neutral-600 font-medium">Loading execution session...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="outlined" className="border-error-200 bg-error-50">
        <CardContent padding="md">
          <div className="flex items-center gap-3">
            <XCircleIcon className="h-5 w-5 text-error-600 flex-shrink-0" />
            <div>
              <p className="text-error-800 font-semibold">Error loading session</p>
              <p className="text-error-700 mt-1 text-sm">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!execution) {
    return (
      <Card variant="default" className="text-center py-12">
        <CardContent>
          <p className="text-neutral-500">No execution session found</p>
        </CardContent>
      </Card>
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
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-3xl font-bold text-neutral-900">
                Active Session #{sessionId}
              </h2>
              <p className="text-neutral-600 mt-1 text-lg">
                {execution.runbook_title || 'Execution Session'}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-neutral-100">
                <div className={`h-3 w-3 rounded-full ${wsConnected ? 'bg-success-500 animate-pulse' : 'bg-error-500'}`} />
                <span className="text-sm font-semibold text-neutral-700">
                  {wsConnected ? 'Live' : 'Disconnected - Polling'}
                </span>
              </div>
              <Badge variant="status" status={execution.status as any} size="md">
                {execution.status}
              </Badge>
            </div>
          </div>
          {execution.issue_description && (
            <p className="text-neutral-700 mt-3 p-3 bg-neutral-50 rounded-lg border border-neutral-200">{execution.issue_description}</p>
          )}
        </CardContent>
      </Card>

      {/* Command Execution Telemetry */}
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-900">Command Execution</h3>
        </CardHeader>
        <CardContent padding="md">
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

              const getCardVariant = () => {
                if (stepState.status === 'executing') return 'outlined';
                if (stepState.status === 'completed') return 'default';
                if (stepState.status === 'failed') return 'outlined';
                return 'default';
              };

              const getCardClassName = () => {
                if (stepState.status === 'executing') return 'border-primary-400 bg-primary-50';
                if (stepState.status === 'completed') return 'border-success-300 bg-success-50';
                if (stepState.status === 'failed') return 'border-error-300 bg-error-50';
                return '';
              };

              return (
                <Card
                  key={step.step_number}
                  variant={getCardVariant()}
                  className={getCardClassName()}
                >
                  <CardContent padding="md">
                    {/* Step Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span className="font-semibold text-neutral-900">
                            Step {stepState.step_number}
                          </span>
                          <Badge variant="secondary" size="sm" className="capitalize">
                            {stepState.step_type}
                          </Badge>
                          {stepState.status === 'executing' && (
                            <div className="flex items-center gap-1 text-primary-600">
                              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-primary-600" />
                              <span className="text-xs font-semibold">Executing...</span>
                            </div>
                          )}
                          {stepState.status === 'completed' && (
                            <div className="flex items-center gap-1 text-success-600">
                              <CheckCircleIcon className="h-4 w-4" />
                              <span className="text-xs font-semibold">Completed</span>
                            </div>
                          )}
                          {stepState.status === 'failed' && (
                            <div className="flex items-center gap-1 text-error-600">
                              <XCircleIcon className="h-4 w-4" />
                              <span className="text-xs font-semibold">Failed</span>
                            </div>
                          )}
                          {stepState.duration_ms && (
                            <span className="text-xs text-neutral-500">
                              ({formatDuration(stepState.duration_ms)})
                            </span>
                          )}
                        </div>
                        {stepState.description && (
                          <p className="text-sm text-neutral-600 mb-3">{stepState.description}</p>
                        )}
                      </div>
                    </div>
                    
                    {/* Command */}
                    <div className="bg-neutral-900 text-accent-400 p-3 rounded-lg font-mono text-xs mb-3">
                      <div className="text-neutral-400 mb-1">$ {stepState.command}</div>
                    </div>
                    
                    {/* Output - Always show if executing, completed, failed, or has output */}
                    {(stepState.status === 'executing' || stepState.status === 'completed' || stepState.status === 'failed' || stepState.output) && (
                      <div className="mb-3">
                        <div className="text-xs font-semibold text-neutral-700 mb-2">
                          Response {stepState.status === 'executing' && !stepState.output && '(Waiting for output...)'}:
                        </div>
                        <div
                          ref={(el) => {
                            if (el) outputRefs.current.set(step.step_number, el);
                          }}
                          className="bg-neutral-900 text-neutral-100 p-3 rounded-lg font-mono text-xs max-h-48 overflow-y-auto min-h-[100px]"
                        >
                          {stepState.output ? (
                            <pre className="whitespace-pre-wrap">{stepState.output}</pre>
                          ) : stepState.status === 'executing' ? (
                            <div className="text-neutral-400 italic flex items-center gap-2">
                              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-neutral-400"></div>
                              Waiting for command output...
                            </div>
                          ) : (
                            <div className="text-neutral-400 italic">No output yet</div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Error */}
                    {stepState.error && (
                      <Card variant="outlined" className="border-error-200 bg-error-50">
                        <CardContent padding="sm">
                          <div className="text-xs font-semibold text-error-700 mb-2">Error:</div>
                          <div className="text-error-800 p-3 rounded-lg font-mono text-xs max-h-48 overflow-y-auto bg-error-100">
                            <pre className="whitespace-pre-wrap">{stepState.error}</pre>
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Debug Panel - Show recent events */}
      {process.env.NODE_ENV === 'development' && (
        <Card variant="outlined" className="border-t-2 border-neutral-200">
          <CardContent padding="md">
            <details className="text-sm">
              <summary className="cursor-pointer text-neutral-600 hover:text-neutral-900 font-semibold">
                Debug: Recent Events ({eventLog.length})
              </summary>
              <div className="mt-3 bg-neutral-50 rounded-lg p-3 max-h-48 overflow-y-auto font-mono text-xs border border-neutral-200">
                {eventLog.length === 0 ? (
                  <div className="text-neutral-500">No events received yet</div>
                ) : (
                  eventLog.slice(-10).map((log, idx) => (
                    <div key={idx} className="mb-2 border-b border-neutral-200 pb-2">
                      <div className="text-neutral-500">{log.timestamp}</div>
                      <pre className="text-xs mt-1 text-neutral-700">{JSON.stringify(log.data, null, 2)}</pre>
                    </div>
                  ))
                )}
              </div>
            </details>
          </CardContent>
        </Card>
      )}

      {/* Step Status Summary - Bottom */}
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-900">Step Status</h3>
        </CardHeader>
        <CardContent padding="md">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {execution.steps?.map((step: any) => {
              const stepState = stepStates.get(step.step_number);
              const status = stepState?.status || (step.completed 
                ? (step.success ? 'completed' : 'failed')
                : (step.step_number === execution.current_step ? 'executing' : 'pending'));

              return (
                <Card key={step.step_number} variant="default">
                  <CardContent padding="sm">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-neutral-900">
                        Step {step.step_number}
                      </span>
                      {status === 'executing' && (
                        <ClockIcon className="h-5 w-5 text-primary-500 animate-pulse" />
                      )}
                      {status === 'completed' && (
                        <CheckCircleIcon className="h-5 w-5 text-success-500" />
                      )}
                      {status === 'failed' && (
                        <XCircleIcon className="h-5 w-5 text-error-500" />
                      )}
                      {status === 'pending' && (
                        <div className="h-5 w-5 rounded-full border-2 border-neutral-300" />
                      )}
                    </div>
                    <div className="text-xs text-neutral-600 truncate font-mono" title={step.command}>
                      {step.command}
                    </div>
                    {stepState?.duration_ms && (
                      <div className="text-xs text-neutral-500 mt-2">
                        Duration: {formatDuration(stepState.duration_ms)}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

