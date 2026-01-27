'use client';

import { useState, useEffect } from 'react';
import {
  InformationCircleIcon,
  DocumentTextIcon,
  LinkIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface ExplanationPanelProps {
  ticketId: number;
  recommendationId?: number;
}

export function ExplanationPanel({ ticketId, recommendationId }: ExplanationPanelProps) {
  const { token } = useAuth();
  const [explanation, setExplanation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchExplanation();
  }, [ticketId, recommendationId]);

  const fetchExplanation = async () => {
    setLoading(true);
    setError(null);

    try {
      const url = `${apiConfig.baseUrl}/api/v1/demo/tickets/${ticketId}/explanation${
        recommendationId ? `?recommendation_id=${recommendationId}` : ''
      }`;

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch explanation');
      }

      const data = await response.json();
      setExplanation(data);
    } catch (err) {
      console.error('Error fetching explanation:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch explanation');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
            <span className="text-sm text-neutral-600">Loading explanation...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex items-center gap-2 text-error-600">
            <span>Error: {error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!explanation) {
    return null;
  }

  return (
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center gap-2">
          <DocumentTextIcon className="h-5 w-5 text-primary-600" />
          <h4 className="font-semibold text-neutral-900">Recommendation Explanation</h4>
        </div>
      </CardHeader>
      <CardContent padding="md">
        <div className="space-y-4">
          {explanation.confidence_breakdown && (
            <div>
              <h5 className="font-semibold text-sm text-neutral-900 mb-2">Confidence Breakdown</h5>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-neutral-600">Overall Confidence</span>
                  <span className="text-sm font-semibold">
                    {explanation.confidence_breakdown.overall_confidence.toFixed(1)}%
                  </span>
                </div>
                {explanation.confidence_breakdown.components && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(explanation.confidence_breakdown.components).map(([key, comp]: [string, any]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-neutral-600 capitalize">{key.replace('_', ' ')}</span>
                        <span>{comp.score?.toFixed(1) || 'N/A'}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {explanation.detailed_explanation && (
            <div>
              <h5 className="font-semibold text-sm text-neutral-900 mb-2">Detailed Explanation</h5>
              {explanation.detailed_explanation.reasoning_steps && (
                <div className="space-y-2">
                  {explanation.detailed_explanation.reasoning_steps.map((step: any, idx: number) => (
                    <div key={idx} className="flex gap-2 text-sm">
                      <span className="font-semibold text-primary-600">{step.step}.</span>
                      <div>
                        <p className="text-neutral-900">{step.description}</p>
                        {step.evidence && (
                          <p className="text-xs text-neutral-500 mt-1">{step.evidence}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {explanation.detailed_explanation?.citations && (
            <div>
              <h5 className="font-semibold text-sm text-neutral-900 mb-2 flex items-center gap-1">
                <LinkIcon className="h-4 w-4" />
                Citations ({explanation.detailed_explanation.citations.count})
              </h5>
              <div className="space-y-1">
                {explanation.detailed_explanation.citations.sources?.slice(0, 5).map((citation: any, idx: number) => (
                  <div key={idx} className="text-xs text-neutral-600 p-2 bg-neutral-50 rounded">
                    {citation.title || citation.source || `Citation ${idx + 1}`}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
