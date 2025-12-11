'use client';

import { useState, useEffect } from 'react';
import { PlayIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { PatternFeedbackPanel } from './PatternFeedbackPanel';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

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
          if (response.status === 401 || response.status === 403) {
            throw new Error('Authentication required. Please log in again.');
          } else if (response.status === 404) {
            throw new Error('Ticket not found or access denied.');
          } else {
            const errorText = await response.text().catch(() => '');
            throw new Error(`Failed to fetch recommendation: ${response.status} ${errorText || ''}`);
          }
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
      <Card variant="default">
        <CardContent padding="md">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
            <span className="text-sm text-neutral-600 font-medium">Loading recommendation...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="outlined" className="border-error-200 bg-error-50">
        <CardContent padding="md">
          <p className="text-sm text-error-800 font-medium">Error: {error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!recommendation) {
    return (
      <Card variant="outlined" className="bg-neutral-50">
        <CardContent padding="md">
          <p className="text-sm text-neutral-600">No recommendation available</p>
        </CardContent>
      </Card>
    );
  }

  const confidencePercent = (recommendation.confidence * 100).toFixed(0);
  const confidenceVariant =
    recommendation.confidence >= 0.8
      ? 'success'
      : recommendation.confidence >= 0.5
      ? 'warning'
      : 'error';

  return (
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center justify-between">
          <h4 className="font-semibold text-neutral-900">AI Recommendation</h4>
          <Badge variant={confidenceVariant} size="sm">
            {confidencePercent}% confidence
          </Badge>
        </div>
      </CardHeader>
      <CardContent padding="md" className="space-y-4">
        {recommendation.runbook_id && recommendation.runbook_title && (
          <Card variant="outlined" className="border-primary-200 bg-primary-50">
            <CardContent padding="md">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h5 className="font-semibold text-neutral-900 mb-1">{recommendation.runbook_title}</h5>
                  {recommendation.pattern_success_rate !== null && (
                    <p className="text-xs text-neutral-600 mt-1">
                      Pattern success rate: {recommendation.pattern_success_rate.toFixed(1)}%
                    </p>
                  )}
                </div>
                {recommendation.should_auto_execute && (
                  <Badge variant="success" size="sm">Auto-execute</Badge>
                )}
              </div>
              <p className="text-sm text-neutral-700 mb-4">{recommendation.reasoning}</p>
              {onExecute && recommendation.runbook_id && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => onExecute(recommendation.runbook_id!)}
                  leftIcon={<PlayIcon className="h-4 w-4" />}
                >
                  Execute Recommended Runbook
                </Button>
              )}
            </CardContent>
          </Card>
        )}

        {recommendation.should_escalate && (
          <Card variant="outlined" className="border-warning-200 bg-warning-50">
            <CardContent padding="md">
              <div className="flex items-start gap-3">
                <ExclamationTriangleIcon className="h-5 w-5 text-warning-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-warning-900">Escalation Recommended</p>
                  <p className="text-xs text-warning-800 mt-1">
                    Low confidence or no matching patterns found. Manual review recommended.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {!recommendation.runbook_id && !recommendation.should_escalate && (
          <Card variant="outlined" className="bg-neutral-50">
            <CardContent padding="md">
              <p className="text-sm text-neutral-700">{recommendation.reasoning}</p>
            </CardContent>
          </Card>
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
      </CardContent>
    </Card>
  );
}

