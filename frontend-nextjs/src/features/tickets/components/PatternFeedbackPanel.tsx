'use client';

import { useState } from 'react';
import { HandThumbUpIcon, HandThumbDownIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';

interface PatternFeedbackPanelProps {
  patternId: number | null;
  recommendationId?: number | null;
  ticketId: number;
  onFeedbackSubmitted?: () => void;
}

export function PatternFeedbackPanel({
  patternId,
  recommendationId,
  ticketId,
  onFeedbackSubmitted,
}: PatternFeedbackPanelProps) {
  const [selectedFeedback, setSelectedFeedback] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const feedbackTypes = [
    { value: 'thumbs_up', label: 'Helpful', icon: HandThumbUpIcon, color: 'text-green-600' },
    { value: 'thumbs_down', label: 'Not Helpful', icon: HandThumbDownIcon, color: 'text-red-600' },
    { value: 'wrong_runbook', label: 'Wrong Runbook', icon: HandThumbDownIcon, color: 'text-orange-600' },
    { value: 'outdated', label: 'Outdated', icon: HandThumbDownIcon, color: 'text-yellow-600' },
    { value: 'not_relevant', label: 'Not Relevant', icon: HandThumbDownIcon, color: 'text-gray-600' },
  ];

  const handleSubmit = async () => {
    if (!selectedFeedback) {
      setError('Please select a feedback type');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const endpoint = patternId
        ? apiConfig.endpoints.decision.patternFeedback(patternId)
        : apiConfig.endpoints.decision.recommendationFeedback();

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          pattern_id: patternId,
          recommendation_id: recommendationId,
          ticket_id: ticketId,
          feedback_type: selectedFeedback,
          reason: reason || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to submit feedback: ${response.status}`);
      }

      setSubmitted(true);
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted();
      }
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
        <p className="text-sm text-green-800">Thank you for your feedback!</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      <h5 className="text-sm font-medium text-gray-900">Was this recommendation helpful?</h5>
      
      <div className="flex flex-wrap gap-2">
        {feedbackTypes.map((type) => {
          const Icon = type.icon;
          const isSelected = selectedFeedback === type.value;
          return (
            <button
              key={type.value}
              onClick={() => setSelectedFeedback(type.value)}
              disabled={submitting}
              className={`flex items-center gap-1 px-3 py-2 rounded-lg border text-sm transition-colors ${
                isSelected
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <Icon className={`h-4 w-4 ${type.color}`} />
              <span>{type.label}</span>
            </button>
          );
        })}
      </div>

      {selectedFeedback && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Reason (optional)
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Tell us why..."
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={submitting}
          />
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-2">
          <p className="text-xs text-red-800">{error}</p>
        </div>
      )}

      {selectedFeedback && (
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? 'Submitting...' : 'Submit Feedback'}
        </button>
      )}
    </div>
  );
}








