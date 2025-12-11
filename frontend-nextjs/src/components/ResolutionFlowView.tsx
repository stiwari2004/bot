'use client';

import { useState, useEffect } from 'react';
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';

interface ResolutionFlow {
  flow_id: number;
  ticket_id: number;
  current_phase: string;
  workflow_status: string;
  iteration_number: number;
  max_iterations: number;
  auto_resolution_enabled: boolean;
  decision_confidence: number | null;
  execution_session_id: number | null;
  runbook_id: number | null;
  started_at: string | null;
  completed_at: string | null;
  escalated_at: string | null;
  escalated_reason: string | null;
}

interface ResolutionFlowViewProps {
  ticketId: number;
  flowId?: number;
}

export function ResolutionFlowView({ ticketId, flowId }: ResolutionFlowViewProps) {
  const { token } = useAuth();
  const [flow, setFlow] = useState<ResolutionFlow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (flowId) {
      fetchFlowStatus();
    }
  }, [flowId]);

  const fetchFlowStatus = async () => {
    if (!flowId) return;

    setLoading(true);
    setError(null);

    try {
      const url = apiConfig.endpoints.resolution.flowStatus(flowId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch flow status');
      }

      const data = await response.json();
      setFlow(data);
    } catch (err) {
      console.error('Error fetching flow status:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch flow status');
    } finally {
      setLoading(false);
    }
  };

  const getPhaseColor = (phase: string): string => {
    switch (phase) {
      case 'precheck':
        return 'bg-blue-100 text-blue-800';
      case 'fix':
        return 'bg-yellow-100 text-yellow-800';
      case 'verification':
        return 'bg-green-100 text-green-800';
      case 'closure':
        return 'bg-gray-100 text-gray-800';
      case 'escalated':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-600" />;
      case 'failed':
      case 'escalated':
        return <XCircleIcon className="h-5 w-5 text-red-600" />;
      case 'in_progress':
        return <ClockIcon className="h-5 w-5 text-blue-600" />;
      default:
        return <ClockIcon className="h-5 w-5 text-gray-600" />;
    }
  };

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="flex items-center justify-center min-h-[200px]">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-2"></div>
              <div className="text-neutral-600 text-sm">Loading resolution flow...</div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="bg-error-50 border border-error-200 rounded-lg p-4">
            <p className="text-sm text-error-800">Error: {error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!flow) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-8 text-center">
            <ClockIcon className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">No resolution flow</h3>
            <p className="text-neutral-600 text-sm">
              Resolution flow will appear here when auto-resolution is initiated.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const phases = ['precheck', 'fix', 'verification', 'closure'];
  const currentPhaseIndex = phases.indexOf(flow.current_phase);

  return (
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-neutral-900">Resolution Flow</h3>
          <div className="flex items-center gap-2">
            {getStatusIcon(flow.workflow_status)}
            <span className="text-sm font-medium text-neutral-900 capitalize">
              {flow.workflow_status.replace('_', ' ')}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent padding="md">
        <div className="space-y-4">
          {/* Phase Progress */}
          <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-neutral-600">Progress</span>
              <span className="text-sm font-medium text-neutral-900">
                Iteration {flow.iteration_number} / {flow.max_iterations}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {phases.map((phase, idx) => (
                <div key={phase} className="flex-1 flex items-center">
                  <div className="flex-1 flex items-center">
                    <div
                      className={`flex-1 h-2 rounded ${
                        idx <= currentPhaseIndex
                          ? 'bg-primary-600'
                          : 'bg-neutral-200'
                      }`}
                    ></div>
                    {idx < phases.length - 1 && (
                      <div
                        className={`w-2 h-2 rounded-full ${
                          idx < currentPhaseIndex
                            ? 'bg-primary-600'
                            : 'bg-neutral-300'
                        }`}
                      ></div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-between mt-2">
              {phases.map((phase) => (
                <div
                  key={phase}
                  className={`text-xs px-2 py-1 rounded ${
                    phase === flow.current_phase
                      ? getPhaseColor(phase)
                      : 'bg-neutral-100 text-neutral-600'
                  }`}
                >
                  {phase}
                </div>
              ))}
            </div>
          </div>

          {/* Current Phase */}
          <div className="bg-white border border-neutral-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-neutral-900">Current Phase</span>
              <span className={`text-xs px-2 py-1 rounded ${getPhaseColor(flow.current_phase)}`}>
                {flow.current_phase}
              </span>
            </div>
            {flow.decision_confidence !== null && (
              <div className="mt-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-neutral-600">Decision Confidence</span>
                  <span className="text-xs font-medium text-neutral-900">
                    {(flow.decision_confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-neutral-200 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full ${
                      flow.decision_confidence >= 0.8
                        ? 'bg-success-600'
                        : flow.decision_confidence >= 0.5
                        ? 'bg-warning-600'
                        : 'bg-error-600'
                    }`}
                    style={{ width: `${flow.decision_confidence * 100}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>

          {/* Flow Details */}
          <div className="bg-white border border-neutral-200 rounded-lg p-4 space-y-2">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-neutral-600">Flow ID:</span>
                <span className="ml-2 font-medium text-neutral-900">{flow.flow_id}</span>
              </div>
              <div>
                <span className="text-neutral-600">Auto-Resolution:</span>
                <span className={`ml-2 font-medium ${flow.auto_resolution_enabled ? 'text-success-600' : 'text-neutral-600'}`}>
                  {flow.auto_resolution_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              {flow.execution_session_id && (
                <div>
                  <span className="text-neutral-600">Session ID:</span>
                  <span className="ml-2 font-medium text-neutral-900">{flow.execution_session_id}</span>
                </div>
              )}
              {flow.runbook_id && (
                <div>
                  <span className="text-neutral-600">Runbook ID:</span>
                  <span className="ml-2 font-medium text-neutral-900">{flow.runbook_id}</span>
                </div>
              )}
            </div>
            {flow.started_at && (
              <div className="text-xs text-neutral-500">
                Started: {new Date(flow.started_at).toLocaleString()}
              </div>
            )}
            {flow.completed_at && (
              <div className="text-xs text-success-600">
                Completed: {new Date(flow.completed_at).toLocaleString()}
              </div>
            )}
            {flow.escalated_at && (
              <div className="bg-error-50 border border-error-200 rounded p-3 mt-2">
                <div className="flex items-start gap-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-error-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-error-900">Escalated</p>
                    <p className="text-xs text-error-800 mt-1">
                      {new Date(flow.escalated_at).toLocaleString()}
                    </p>
                    {flow.escalated_reason && (
                      <p className="text-xs text-error-700 mt-1">{flow.escalated_reason}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

