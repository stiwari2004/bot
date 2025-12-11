/**
 * View: Component for displaying analysis results
 */
'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DocumentTextIcon } from '@heroicons/react/24/outline';
import { AnalysisResponse } from '../types';
import { getRecommendationIcon, getRecommendationColor, getRecommendationTitle } from '../utils/recommendationUtils';
import { RunbookList } from '@/features/runbooks';

interface AnalysisResultViewProps {
  analysis: AnalysisResponse;
}

export function AnalysisResultView({ analysis }: AnalysisResultViewProps) {
  return (
    <div className="space-y-6">
      {/* Recommendation Card */}
      <Card variant="elevated" className={getRecommendationColor(analysis)}>
        <CardContent padding="md">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center">
              {getRecommendationIcon(analysis)}
              <div className="ml-3">
                <h3 className="text-lg font-semibold">
                  {getRecommendationTitle(analysis)}
                </h3>
                <p className="text-sm opacity-80">
                  Confidence: {(analysis.confidence * 100).toFixed(0)}%
                </p>
              </div>
            </div>
          </div>
          <p className="mb-4">{analysis.reasoning}</p>

          {analysis.suggested_actions.length > 0 && (
            <div className="mt-4">
              <h4 className="font-medium mb-2">Suggested Actions:</h4>
              <ul className="list-disc list-inside space-y-1">
                {analysis.suggested_actions.map((action, idx) => (
                  <li key={idx} className="text-sm opacity-90">{action}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Matched Runbooks */}
      {analysis.matched_runbooks.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center mb-2">
              <div className="p-1.5 rounded-lg bg-primary-100 mr-3">
                <DocumentTextIcon className="h-5 w-5 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900">
                Similar Runbooks Found ({analysis.matched_runbooks.length})
              </h3>
            </div>
          </CardHeader>
          <CardContent padding="md">
            <div className="space-y-4">
              {analysis.matched_runbooks.map((match, idx) => (
                <Card
                  key={match.id}
                  variant="elevated"
                  className={`${
                    idx === 0 && match.confidence_score >= analysis.threshold_used
                      ? 'border-success-300 bg-success-50'
                      : 'hover:border-primary-300'
                  }`}
                >
                  <CardContent padding="md">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-semibold text-neutral-900">{match.title}</h4>
                      <div className="flex items-center space-x-3">
                        <span className="text-sm font-semibold text-primary-600">
                          {(match.confidence_score * 100).toFixed(0)}% match
                        </span>
                        {match.success_rate !== null && (
                          <span className="text-sm text-neutral-600">
                            {(match.success_rate * 100).toFixed(0)}% success
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-neutral-700 mb-2">{match.reasoning}</p>
                    <div className="flex items-center space-x-4 text-xs text-neutral-500">
                      <span>Used {match.times_used}x</span>
                      {match.last_used && (
                        <span>Last: {new Date(match.last_used).toLocaleDateString()}</span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {analysis.matched_runbooks.length === 0 && (
        <Card variant="elevated">
          <CardContent padding="lg">
            <div className="text-center py-8 text-neutral-500">
              No similar runbooks found in the knowledge base.
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}





