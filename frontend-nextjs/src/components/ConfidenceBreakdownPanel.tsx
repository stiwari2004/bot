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
    if (score === null) return 'bg-gray-100 text-gray-600';
    if (score >= 80) return 'bg-green-100 text-green-800';
    if (score >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getScoreLabel = (score: number | null): string => {
    if (score === null) return 'N/A';
    if (score >= 80) return 'High';
    if (score >= 60) return 'Medium';
    return 'Low';
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="text-sm text-gray-600">Loading confidence breakdown...</span>
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
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ChartBarIcon className="h-5 w-5 text-gray-600" />
          <h4 className="font-medium text-gray-900">Confidence Breakdown</h4>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      <div className="space-y-3">
        {/* Overall Confidence */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-900">Overall Confidence</span>
            <span className={`text-lg font-bold px-2 py-1 rounded ${getScoreColor(breakdown.overall_confidence)}`}>
              {breakdown.overall_confidence.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${
                breakdown.overall_confidence >= 80
                  ? 'bg-green-600'
                  : breakdown.overall_confidence >= 60
                  ? 'bg-yellow-600'
                  : 'bg-red-600'
              }`}
              style={{ width: `${breakdown.overall_confidence}%` }}
            ></div>
          </div>
        </div>

        {/* Component Scores */}
        {expanded && (
          <div className="space-y-2">
            {components.map((item) => (
              <div key={item.name} className="border border-gray-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">{item.name}</span>
                    <span className="text-xs text-gray-500">({(item.component.weight * 100).toFixed(0)}% weight)</span>
                    <InformationCircleIcon className="h-4 w-4 text-gray-400" title={item.description} />
                  </div>
                  {item.component.score !== null && (
                    <span className={`text-sm font-medium px-2 py-1 rounded ${getScoreColor(item.component.score)}`}>
                      {item.component.score.toFixed(1)}% ({getScoreLabel(item.component.score)})
                    </span>
                  )}
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  {item.component.score !== null && (
                    <div
                      className={`h-1.5 rounded-full ${
                        item.component.score >= 80
                          ? 'bg-green-600'
                          : item.component.score >= 60
                          ? 'bg-yellow-600'
                          : 'bg-red-600'
                      }`}
                      style={{ width: `${item.component.score}%` }}
                    ></div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Warnings and Flags */}
        {(breakdown.warnings.length > 0 || breakdown.flags.length > 0) && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-yellow-900">Warnings</p>
                {breakdown.warnings.map((warning, idx) => (
                  <p key={idx} className="text-xs text-yellow-800 mt-1">
                    • {warning}
                  </p>
                ))}
                {breakdown.flags.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-yellow-700 font-medium">Flags:</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {breakdown.flags.map((flag, idx) => (
                        <span
                          key={idx}
                          className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded"
                        >
                          {flag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

