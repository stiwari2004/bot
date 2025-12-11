'use client';

import { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface ConfidenceComponent {
  score: number | null;
  weight: number;
  details?: any;
}

interface ConfidenceBreakdown {
  id: number;
  overall_confidence: number;
  components: {
    search_quality: ConfidenceComponent;
    llm_consistency: ConfidenceComponent;
    yaml_quality: ConfidenceComponent;
    citation_coverage: ConfidenceComponent;
  };
  warnings: string[];
  flags: string[];
  created_at?: string;
}

interface ConfidenceBreakdownPanelProps {
  runbookId?: number;
  recommendationId?: number;
  ticketId?: number;
}

export function ConfidenceBreakdownPanel({
  runbookId,
  recommendationId,
  ticketId,
}: ConfidenceBreakdownPanelProps) {
  const { token } = useAuth();
  const [breakdown, setBreakdown] = useState<ConfidenceBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchBreakdown();
  }, [runbookId, recommendationId, ticketId]);

  const fetchBreakdown = async () => {
    if (!runbookId && !recommendationId && !ticketId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let url: string;
      if (runbookId) {
        url = apiConfig.endpoints.decision.runbookConfidence(runbookId);
      } else if (recommendationId) {
        url = apiConfig.endpoints.decision.recommendationConfidence(recommendationId);
      } else {
        setLoading(false);
        return;
      }

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch confidence breakdown');
      }

      const data = await response.json();
      setBreakdown(data);
    } catch (err) {
      console.error('Error fetching confidence breakdown:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch confidence breakdown');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number | null): string => {
    if (score === null) return 'bg-neutral-100 text-neutral-600';
    if (score >= 80) return 'bg-success-100 text-success-800';
    if (score >= 60) return 'bg-warning-100 text-warning-800';
    return 'bg-error-100 text-error-800';
  };

  const getScoreLabel = (score: number | null): string => {
    if (score === null) return 'N/A';
    if (score >= 80) return 'High';
    if (score >= 60) return 'Medium';
    return 'Low';
  };

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
            <span className="text-sm text-neutral-600">Loading confidence breakdown...</span>
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
            <p className="text-sm text-error-800">Error: {error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!breakdown) {
    return null;
  }

  const components = [
    {
      name: 'Search Quality',
      component: breakdown.components.search_quality,
      description: 'Based on search result relevance and coverage',
    },
    {
      name: 'LLM Consistency',
      component: breakdown.components.llm_consistency,
      description: 'How well the output matches retrieved context',
    },
    {
      name: 'YAML Quality',
      component: breakdown.components.yaml_quality,
      description: 'Structure validation and completeness',
    },
    {
      name: 'Citation Coverage',
      component: breakdown.components.citation_coverage,
      description: 'Number and quality of source references',
    },
  ];

  return (
    <Card variant="elevated">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-secondary-100">
              <ChartBarIcon className="h-5 w-5 text-secondary-600" />
            </div>
            <h4 className="font-semibold text-neutral-900">Confidence Breakdown</h4>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? 'Collapse' : 'Expand'}
          </Button>
        </div>
      </CardHeader>
      <CardContent padding="md">
        <div className="space-y-3">

          {/* Overall Confidence */}
          <Card variant="default" className="bg-primary-50 border-primary-200">
            <CardContent padding="sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-neutral-900">Overall Confidence</span>
                <span className={`text-lg font-bold px-2 py-1 rounded ${getScoreColor(breakdown.overall_confidence)}`}>
                  {breakdown.overall_confidence.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-neutral-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    breakdown.overall_confidence >= 80
                      ? 'bg-success-600'
                      : breakdown.overall_confidence >= 60
                      ? 'bg-warning-600'
                      : 'bg-error-600'
                  }`}
                  style={{ width: `${breakdown.overall_confidence}%` }}
                ></div>
              </div>
            </CardContent>
          </Card>

          {/* Component Scores */}
          {expanded && (
            <div className="space-y-2">
              {components.map((item) => (
                <Card key={item.name} variant="default" className="hover:border-primary-300 transition-colors">
                  <CardContent padding="sm">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-neutral-900">{item.name}</span>
                        <span className="text-xs text-neutral-500">({(item.component.weight * 100).toFixed(0)}% weight)</span>
                        <InformationCircleIcon className="h-4 w-4 text-neutral-400" title={item.description} />
                      </div>
                      {item.component.score !== null && (
                        <span className={`text-sm font-medium px-2 py-1 rounded ${getScoreColor(item.component.score)}`}>
                          {item.component.score.toFixed(1)}% ({getScoreLabel(item.component.score)})
                        </span>
                      )}
                    </div>
                    <div className="w-full bg-neutral-200 rounded-full h-1.5">
                      {item.component.score !== null && (
                        <div
                          className={`h-1.5 rounded-full ${
                            item.component.score >= 80
                              ? 'bg-success-600'
                              : item.component.score >= 60
                              ? 'bg-warning-600'
                              : 'bg-error-600'
                          }`}
                          style={{ width: `${item.component.score}%` }}
                        ></div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Warnings and Flags */}
          {(breakdown.warnings.length > 0 || breakdown.flags.length > 0) && (
            <Card variant="default" className="bg-warning-50 border-warning-200">
              <CardContent padding="sm">
                <div className="flex items-start gap-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-warning-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-warning-900">Warnings</p>
                    {breakdown.warnings.map((warning, idx) => (
                      <p key={idx} className="text-xs text-warning-800 mt-1">
                        • {warning}
                      </p>
                    ))}
                    {breakdown.flags.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-warning-700 font-medium">Flags:</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {breakdown.flags.map((flag, idx) => (
                            <span
                              key={idx}
                              className="text-xs px-2 py-0.5 bg-warning-100 text-warning-800 rounded"
                            >
                              {flag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </CardContent>
    </Card>
  );
}








