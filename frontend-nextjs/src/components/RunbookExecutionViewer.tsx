'use client';

import { useState, useEffect } from 'react';
import { 
  PlayIcon, 
  CheckIcon, 
  XMarkIcon,
  ClipboardDocumentIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

interface RunbookStep {
  id?: number;
  step_number: number;
  type: 'precheck' | 'main' | 'postcheck';
  command: string;
  description?: string;
  completed: boolean | string;
  success?: boolean | string;
  output?: string;
  notes?: string;
}

interface ExecutionSession {
  id: number;
  runbook_id: number;
  runbook_title: string;
  issue_description: string;
  status: string;
  started_at: string;
  completed_at?: string;
  total_duration_minutes?: number;
  steps: RunbookStep[];
}

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
      setSession(data);
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

  const updateStep = async (step: RunbookStep, field: string, value: any) => {
    if (!session) return;
    
    setUpdating(true);
    
    try {
      const response = await fetch(`/api/v1/executions/demo/sessions/${session.id}/steps`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          step_number: step.step_number,
          step_type: step.type,
          completed: field === 'completed' ? value : step.completed === 'true' || step.completed === true,
          success: field === 'success' ? value : step.success === 'true' || step.success === true,
          output: field === 'output' ? value : step.output,
          notes: field === 'notes' ? value : step.notes
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update step');
      }

      // Reload session to get updated data
      const sessionResponse = await fetch(`/api/v1/executions/demo/sessions/${session.id}`);
      const updatedSession = await sessionResponse.json();
      setSession(updatedSession);
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
      
      // Show success message
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
    const completed = session.steps.filter(s => s.completed === 'true' || s.completed === true).length;
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
        
        {/* Progress Bar */}
        <div className="bg-gray-200 rounded-full h-4 mb-4">
          <div 
            className="bg-blue-600 h-4 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">
            {session.steps.filter(s => s.completed === 'true' || s.completed === true).length} / {session.steps.length} steps completed
          </span>
          <div className="flex items-center text-gray-600">
            <ClockIcon className="h-5 w-5 mr-2" />
            <span className="font-medium">{formatTime(elapsedSeconds)}</span>
          </div>
        </div>
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
                  onUpdate={(field, value) => updateStep(step, field, value)}
                  onCopy={() => step.command && copyToClipboard(step.command)}
                  getSeverityColor={getSeverityColor}
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
                onUpdate={(field, value) => updateStep(step, field, value)}
                onCopy={() => step.command && copyToClipboard(step.command)}
                getSeverityColor={getSeverityColor}
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
                  onUpdate={(field, value) => updateStep(step, field, value)}
                  onCopy={() => step.command && copyToClipboard(step.command)}
                  getSeverityColor={getSeverityColor}
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

interface StepCardProps {
  step: RunbookStep;
  onUpdate: (field: string, value: any) => void;
  onCopy: () => void;
  getSeverityColor: (severity?: string) => string;
}

function StepCard({ step, onUpdate, onCopy, getSeverityColor }: StepCardProps) {
  const [showNotes, setShowNotes] = useState(false);
  const isCompleted = step.completed === 'true' || step.completed === true;
  const isSuccess = step.success === 'true' || step.success === true;

  return (
    <div className={`border rounded-lg p-4 ${isCompleted ? 'bg-gray-50' : 'bg-white'}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={isCompleted}
              onChange={(e) => onUpdate('completed', e.target.checked)}
              className="h-5 w-5 text-blue-600"
            />
            <span className="font-medium text-gray-900">
              Step {step.step_number}
            </span>
          </div>
          {step.description && (
            <p className="text-sm text-gray-600 mt-1">{step.description}</p>
          )}
        </div>
        {isCompleted && (
          <div className="ml-2">
            {isSuccess ? (
              <CheckIcon className="h-6 w-6 text-green-600" />
            ) : (
              <XMarkIcon className="h-6 w-6 text-red-600" />
            )}
          </div>
        )}
      </div>

      {step.command && (
        <div className="mt-2 bg-gray-900 text-green-400 p-3 rounded font-mono text-sm relative">
          <pre className="overflow-x-auto">{step.command}</pre>
          <button
            onClick={onCopy}
            className="absolute top-2 right-2 text-gray-400 hover:text-white"
            title="Copy command"
          >
            <ClipboardDocumentIcon className="h-5 w-5" />
          </button>
        </div>
      )}

      {isCompleted && (
        <div className="mt-3 space-y-2">
          <div className="flex space-x-2">
            <button
              onClick={() => onUpdate('success', true)}
              className={`flex-1 px-3 py-1 text-sm rounded ${isSuccess === true ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Success
            </button>
            <button
              onClick={() => onUpdate('success', false)}
              className={`flex-1 px-3 py-1 text-sm rounded ${isSuccess === false ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Failed
            </button>
          </div>
          
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Output</label>
            <textarea
              value={step.output || ''}
              onChange={(e) => onUpdate('output', e.target.value)}
              rows={2}
              className="w-full text-xs border border-gray-300 rounded px-2 py-1"
              placeholder="Command output..."
            />
          </div>

          <button
            onClick={() => setShowNotes(!showNotes)}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            {showNotes ? 'Hide' : 'Add'} Notes
          </button>
          
          {showNotes && (
            <textarea
              value={step.notes || ''}
              onChange={(e) => onUpdate('notes', e.target.value)}
              rows={2}
              className="w-full text-xs border border-gray-300 rounded px-2 py-1"
              placeholder="Additional notes..."
            />
          )}
        </div>
      )}
    </div>
  );
}

