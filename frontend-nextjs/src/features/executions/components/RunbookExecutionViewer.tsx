'use client';

import { useState, useEffect } from 'react';
import {
  ClockIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import type { ExecutionSession, RunbookStep, StepUpdatePayload } from '../types';
import { StepCard } from './StepCard';

const normalizeStep = (step: any): RunbookStep => ({
  id: step.id,
  step_number: step.step_number,
  type: (step.step_type || step.type || 'main') as RunbookStep['type'],
  command: step.command || '',
  description: step.description || '',
  completed: step.completed === true || step.completed === 'true',
  success:
    typeof step.success === 'boolean'
      ? step.success
      : step.success === 'true'
      ? true
      : step.success === 'false'
      ? false
      : null,
  output: step.output ?? '',
  notes: step.notes ?? '',
  requires_approval:
    step.requires_approval === true || step.requires_approval === 'true',
  approved:
    typeof step.approved === 'boolean'
      ? step.approved
      : step.approved === 'true'
      ? true
      : step.approved === 'false'
      ? false
      : null,
  severity: step.severity,
  rollback_command: step.rollback_command ?? '',
});

const normalizeSession = (raw: any): ExecutionSession => ({
  id: raw.id,
  runbook_id: raw.runbook_id,
  runbook_title: raw.runbook_title || 'Runbook Execution',
  issue_description: raw.issue_description || '',
  status: raw.status || 'pending',
  started_at: raw.started_at,
  completed_at: raw.completed_at,
  total_duration_minutes: raw.total_duration_minutes,
  current_step: raw.current_step ?? null,
  waiting_for_approval: raw.waiting_for_approval ?? false,
  steps: Array.isArray(raw.steps) ? raw.steps.map(normalizeStep) : [],
});

const formatStepType = (type?: string) => {
  if (!type) return 'Step';
  return type.charAt(0).toUpperCase() + type.slice(1);
};

interface RunbookExecutionViewerProps {
  runbookId: number;
  issueDescription: string;
  onComplete?: () => void;
}

export function RunbookExecutionViewer({ 
  runbookId, 
  issueDescription,
  onComplete 
}: RunbookExecutionViewerProps) {
  const [session, setSession] = useState<ExecutionSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startTime, setStartTime] = useState<Date | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [updating, setUpdating] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackData, setFeedbackData] = useState({
    was_successful: false,
    issue_resolved: false,
    rating: 5,
    feedback_text: '',
    suggestions: ''
  });
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  useEffect(() => {
    startExecution();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (startTime) {
      const interval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000);
        setElapsedSeconds(elapsed);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [startTime]);

  const startExecution = async () => {
    setLoading(true);
    setError(null);
    setStartTime(new Date());

    try {
      const response = await fetch('/api/v1/executions/demo/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          runbook_id: runbookId,
          issue_description: issueDescription
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start execution session');
      }

      const data = await response.json();
      const normalized = normalizeSession(data);
      setSession(normalized);
      setStartTime(normalized.started_at ? new Date(normalized.started_at) : new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start execution');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const updateStep = async (step: RunbookStep, updates: StepUpdatePayload) => {
    if (!session) return;
    
    setUpdating(true);
    setError(null);
    
    try {
      const currentCompleted = step.completed;
      const currentSuccess = step.success;

      const payload: Record<string, any> = {
        step_number: step.step_number,
        step_type: step.type,
        completed: updates.completed ?? currentCompleted,
        output:
          updates.output !== undefined
            ? updates.output
            : step.output !== undefined
            ? step.output
            : '',
        notes:
          updates.notes !== undefined
            ? updates.notes
            : step.notes !== undefined
            ? step.notes
            : '',
      };

      if (updates.success !== undefined) {
        payload.success = updates.success;
      } else if (currentSuccess !== undefined) {
        payload.success = currentSuccess;
      }

      if (updates.approved !== undefined) {
        payload.approved = updates.approved;
      }

      const response = await fetch(`/api/v1/executions/demo/sessions/${session.id}/steps`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error('Failed to update step');
      }

      // If this was an approval, wait a bit for execution to complete, then reload
      if (updates.approved === true && step.requires_approval) {
        await new Promise(resolve => setTimeout(resolve, 2000));
      }

      // Reload session to get updated data
      const sessionResponse = await fetch(`/api/v1/executions/demo/sessions/${session.id}`);
      if (!sessionResponse.ok) {
        throw new Error('Failed to reload session');
      }
      const updatedSession = await sessionResponse.json();
      setSession(normalizeSession(updatedSession));
      
      // If session is still waiting for approval on next step, poll for updates
      if (updatedSession.waiting_for_approval && updatedSession.status === 'waiting_approval') {
        let pollCount = 0;
        const pollInterval = setInterval(async () => {
          pollCount++;
          if (pollCount > 10) {
            clearInterval(pollInterval);
            return;
          }
          try {
            const pollResponse = await fetch(`/api/v1/executions/demo/sessions/${session.id}`);
            if (pollResponse.ok) {
              const polledSession = await pollResponse.json();
              setSession(normalizeSession(polledSession));
              if (!polledSession.waiting_for_approval || polledSession.status !== 'waiting_approval') {
                clearInterval(pollInterval);
              }
            }
          } catch (err) {
            console.error('Error polling session:', err);
            clearInterval(pollInterval);
          }
        }, 3000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update step');
    } finally {
      setUpdating(false);
    }
  };

  const handleComplete = () => {
    setShowFeedback(true);
  };

  const submitFeedback = async () => {
    if (!session) return;
    
    setSubmittingFeedback(true);
    
    try {
      const response = await fetch(`/api/v1/executions/demo/sessions/${session.id}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedbackData)
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      if (onComplete) {
        onComplete();
      }
      
      alert('Execution completed and feedback recorded!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getProgress = () => {
    if (!session) return 0;
    if (session.steps.length === 0) return 0;
    const completed = session.steps.filter((s) => s.completed).length;
    return (completed / session.steps.length) * 100;
  };

  const getSeverityColor = (severity?: string) => {
    if (!severity) return 'bg-gray-100 text-gray-700';
    switch (severity.toLowerCase()) {
      case 'safe': return 'bg-green-100 text-green-700';
      case 'moderate': return 'bg-yellow-100 text-yellow-700';
      case 'dangerous': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center">
          <ArrowPathIcon className="animate-spin h-8 w-8 text-blue-600" />
          <span className="ml-2 text-gray-600">Initializing execution session...</span>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error || 'Failed to load execution session'}</p>
        </div>
      </div>
    );
  }

  const prechecks = session.steps.filter(s => s.type === 'precheck');
  const mainSteps = session.steps.filter(s => s.type === 'main');
  const postchecks = session.steps.filter(s => s.type === 'postcheck');
  const progress = getProgress();

  if (showFeedback) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">Execution Feedback</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Was the execution successful?
              </label>
              <div className="flex space-x-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={feedbackData.was_successful === true}
                    onChange={() => setFeedbackData({ ...feedbackData, was_successful: true })}
                    className="mr-2"
                  />
                  Yes
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={feedbackData.was_successful === false}
                    onChange={() => setFeedbackData({ ...feedbackData, was_successful: false })}
                    className="mr-2"
                  />
                  No
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Was the issue resolved?
              </label>
              <div className="flex space-x-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={feedbackData.issue_resolved === true}
                    onChange={() => setFeedbackData({ ...feedbackData, issue_resolved: true })}
                    className="mr-2"
                  />
                  Yes
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={feedbackData.issue_resolved === false}
                    onChange={() => setFeedbackData({ ...feedbackData, issue_resolved: false })}
                    className="mr-2"
                  />
                  No
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rating (1-5)
              </label>
              <input
                type="range"
                min="1"
                max="5"
                value={feedbackData.rating}
                onChange={(e) => setFeedbackData({ ...feedbackData, rating: parseInt(e.target.value) })}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>Poor</span>
                <span className="text-lg font-bold">{feedbackData.rating}</span>
                <span>Excellent</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Additional Feedback
              </label>
              <textarea
                value={feedbackData.feedback_text}
                onChange={(e) => setFeedbackData({ ...feedbackData, feedback_text: e.target.value })}
                rows={4}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                placeholder="Any additional comments or observations..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Suggestions for Improvement
              </label>
              <textarea
                value={feedbackData.suggestions}
                onChange={(e) => setFeedbackData({ ...feedbackData, suggestions: e.target.value })}
                rows={3}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                placeholder="How could this runbook be improved?"
              />
            </div>

            <div className="flex space-x-4">
              <button
                onClick={submitFeedback}
                disabled={submittingFeedback}
                className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {submittingFeedback ? 'Submitting...' : 'Submit Feedback'}
              </button>
              <button
                onClick={() => setShowFeedback(false)}
                className="flex-1 bg-gray-200 text-gray-800 px-6 py-3 rounded-lg hover:bg-gray-300"
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">{session.runbook_title}</h2>
        <p className="text-gray-600 mb-4">{session.issue_description}</p>

        <div className="flex flex-wrap items-center gap-3 mb-4">
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-indigo-100 text-indigo-700 uppercase tracking-wide">
            {session.status.replace(/_/g, ' ')}
          </span>
          {session.waiting_for_approval && (
            <span className="px-3 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-700">
              Waiting for approval
            </span>
          )}
          {typeof session.current_step === 'number' && (
            <span className="text-xs font-medium text-gray-500">
              Current step: {session.current_step}
            </span>
          )}
        </div>
        
        {/* Progress Bar */}
        <div className="bg-gray-200 rounded-full h-4 mb-4">
          <div 
            className="bg-blue-600 h-4 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">
            {session.steps.filter((s) => s.completed).length} / {session.steps.length} steps completed
          </span>
          <div className="flex items-center text-gray-600">
            <ClockIcon className="h-5 w-5 mr-2" />
            <span className="font-medium">{formatTime(elapsedSeconds)}</span>
          </div>
        </div>
      </div>

      {/* Compact Step Overview */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Execution Steps</h3>
        <ol className="space-y-3">
          {session.steps.map((step) => (
            <li key={`overview-${step.step_number}`} className="border border-gray-200 rounded-lg p-3 bg-white shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-800">Step {step.step_number}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                      {formatStepType(step.type)}
                    </span>
                    {step.requires_approval && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
                        Requires Approval
                      </span>
                    )}
                  </div>
                  {step.description && (
                    <p className="text-xs text-gray-500 mt-1">{step.description}</p>
                  )}
                  {step.command && (
                    <p className="text-xs text-gray-600 mt-2 font-mono truncate">{step.command}</p>
                  )}
                </div>
                <div className="flex flex-col items-end text-xs text-gray-500">
                  <span className={`font-semibold ${
                    step.completed ? (step.success === false ? 'text-red-600' : 'text-green-600') : 'text-gray-500'
                  }`}>
                    {step.completed ? (step.success === false ? 'Failed' : 'Completed') : 'Pending'}
                  </span>
                  {step.approved !== null && (
                    <span className={`mt-1 ${step.approved ? 'text-green-600' : 'text-red-600'}`}>
                      {step.approved ? 'Approved' : 'Changes requested'}
                    </span>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Steps Display */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Prechecks */}
        {prechecks.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Prechecks</h3>
            <div className="space-y-4">
              {prechecks.map((step) => (
                <StepCard
                  key={step.step_number}
                  step={step}
                  onUpdate={(updates) => updateStep(step, updates)}
                  onCopy={() => step.command && copyToClipboard(step.command)}
                  isUpdating={updating}
                />
              ))}
            </div>
          </div>
        )}

        {/* Main Steps */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Main Steps</h3>
          <div className="space-y-4">
            {mainSteps.map((step) => (
              <StepCard
                key={step.step_number}
                step={step}
                onUpdate={(updates) => updateStep(step, updates)}
                onCopy={() => step.command && copyToClipboard(step.command)}
                isUpdating={updating}
              />
            ))}
          </div>
        </div>

        {/* Postchecks */}
        {postchecks.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Postchecks</h3>
            <div className="space-y-4">
              {postchecks.map((step) => (
                <StepCard
                  key={step.step_number}
                  step={step}
                  onUpdate={(updates) => updateStep(step, updates)}
                  onCopy={() => step.command && copyToClipboard(step.command)}
                  isUpdating={updating}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Complete Button */}
      {progress === 100 && (
        <div className="mt-8 text-center">
          <button
            onClick={handleComplete}
            className="bg-green-600 text-white px-8 py-3 rounded-lg hover:bg-green-700 font-medium"
          >
            Complete Execution & Submit Feedback
          </button>
        </div>
      )}
    </div>
  );
}



