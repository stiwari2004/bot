'use client';

import { useState, useEffect } from 'react';
import { PlayIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { PatternFeedbackPanel } from './PatternFeedbackPanel';
import { useAuth } from '@/contexts/AuthContext';

interface Recommendation {
  runbook_id: number | null;
  runbook_title: string | null;
  confidence: number;
  pattern_id: number | null;
  pattern_success_rate: number | null;
  reasoning: string;
  should_auto_execute: boolean;
  should_escalate: boolean;
  context_signals: Record<string, any>;
}

interface DecisionRecommendationPanelProps {
  ticketId: number;
  onExecute?: (runbookId: number) => void;
  onFeedbackSubmitted?: () => void;
}

export function DecisionRecommendationPanel({ ticketId, onExecute, onFeedbackSubmitted }: DecisionRecommendationPanelProps) {
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { token, loading: authLoading } = useAuth();

  useEffect(() => {
    const fetchRecommendation = async () => {
      // Wait for auth to finish loading
      if (authLoading) return;
      
      // Get token from localStorage as fallback
      const authToken = token || (typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null);
      
      if (!authToken) {
        setLoading(false);
        setError('Authentication required');
        return;
      }
      
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(apiConfig.endpoints.decision.recommendation(ticketId), {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        });
        if (!response.ok) {
          throw new Error(`Failed to fetch recommendation: ${response.status}`);
        }
        const data = await response.json();
        setRecommendation(data);
      } catch (err) {
        console.error('Error fetching recommendation:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch recommendation');
      } finally {
        setLoading(false);
      }
    };

    if (ticketId) {
      fetchRecommendation();
    }
  }, [ticketId, token, authLoading]);

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="text-sm text-gray-600">Loading recommendation...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-sm text-red-800">Error: {error}</p>
      </div>
    );
  }

  if (!recommendation) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-sm text-gray-600">No recommendation available</p>
      </div>
    );
  }

  const confidencePercent = (recommendation.confidence * 100).toFixed(0);
  const confidenceColor =
    recommendation.confidence >= 0.8
      ? 'bg-green-100 text-green-800'
      : recommendation.confidence >= 0.5
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-red-100 text-red-800';

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-gray-900">AI Recommendation</h4>
        <span className={`text-xs px-2 py-1 rounded ${confidenceColor}`}>
          {confidencePercent}% confidence
        </span>
      </div>

      {recommendation.runbook_id && recommendation.runbook_title && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-start justify-between mb-2">
            <div>
              <h5 className="font-medium text-gray-900">{recommendation.runbook_title}</h5>
              {recommendation.pattern_success_rate !== null && (
                <p className="text-xs text-gray-600 mt-1">
                  Pattern success rate: {recommendation.pattern_success_rate.toFixed(1)}%
                </p>
              )}
            </div>
            {recommendation.should_auto_execute && (
              <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-800">
                Auto-execute
              </span>
            )}
          </div>
          <p className="text-sm text-gray-700 mb-3">{recommendation.reasoning}</p>
          {onExecute && recommendation.runbook_id && (
            <button
              onClick={() => onExecute(recommendation.runbook_id!)}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              <PlayIcon className="h-4 w-4" />
              Execute Recommended Runbook
            </button>
          )}
        </div>
      )}

      {recommendation.should_escalate && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 flex items-start gap-2">
          <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-yellow-900">Escalation Recommended</p>
            <p className="text-xs text-yellow-800 mt-1">
              Low confidence or no matching patterns found. Manual review recommended.
            </p>
          </div>
        </div>
      )}

      {!recommendation.runbook_id && !recommendation.should_escalate && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <p className="text-sm text-gray-700">{recommendation.reasoning}</p>
        </div>
      )}

      {/* Feedback Panel */}
      {(recommendation.pattern_id || recommendation.runbook_id) && (
        <PatternFeedbackPanel
          patternId={recommendation.pattern_id}
          recommendationId={recommendation.runbook_id}
          ticketId={ticketId}
          onFeedbackSubmitted={onFeedbackSubmitted}
        />
      )}
    </div>
  );
}

