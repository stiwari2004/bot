'use client';

import { useState } from 'react';
import { 
  MagnifyingGlassIcon, 
  CheckCircleIcon, 
  ExclamationTriangleIcon,
  SparklesIcon,
  DocumentTextIcon,
  BoltIcon
} from '@heroicons/react/24/outline';
import { RunbookList } from './RunbookList';

interface RunbookMatch {
  id: number;
  title: string;
  similarity_score: number;
  confidence_score: number;
  success_rate: number | null;
  times_used: number;
  last_used: string | null;
  reasoning: string;
}

interface AnalysisResponse {
  recommendation: 'existing_runbook' | 'generate_new' | 'escalate';
  confidence: number;
  reasoning: string;
  matched_runbooks: RunbookMatch[];
  suggested_actions: string[];
  threshold_used: number;
}

export function TicketAnalyzer() {
  const [issueDescription, setIssueDescription] = useState('');
  const [severity, setSeverity] = useState('medium');
  const [serviceType, setServiceType] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueDescription.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/tickets/demo/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          issue_description: issueDescription,
          severity: severity,
          service_type: serviceType || undefined,
          environment: 'prod',
        }),
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const getRecommendationIcon = () => {
    if (!analysis) return null;
    
    switch (analysis.recommendation) {
      case 'existing_runbook':
        return <CheckCircleIcon className="h-8 w-8 text-green-500" />;
      case 'generate_new':
        return <SparklesIcon className="h-8 w-8 text-blue-500" />;
      case 'escalate':
        return <ExclamationTriangleIcon className="h-8 w-8 text-yellow-500" />;
    }
  };

  const getRecommendationColor = () => {
    if (!analysis) return '';
    
    switch (analysis.recommendation) {
      case 'existing_runbook':
        return 'bg-green-50 border-green-200 text-green-900';
      case 'generate_new':
        return 'bg-blue-50 border-blue-200 text-blue-900';
      case 'escalate':
        return 'bg-yellow-50 border-yellow-200 text-yellow-900';
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
          <BoltIcon className="h-7 w-7 mr-2 text-blue-600" />
          Intelligent Ticket Analysis
        </h2>
        <p className="text-gray-600">
          Enter an issue description to get AI-powered recommendations with existing solutions or generate a new runbook
        </p>
      </div>

      <form onSubmit={handleAnalyze} className="mb-6">
        <div className="space-y-4">
          <div>
            <label htmlFor="issue-description" className="block text-sm font-medium text-gray-700 mb-2">
              Issue Description *
            </label>
            <textarea
              id="issue-description"
              value={issueDescription}
              onChange={(e) => setIssueDescription(e.target.value)}
              placeholder="e.g., Production database connections timing out, causing intermittent failures..."
              rows={4}
              className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="severity" className="block text-sm font-medium text-gray-700 mb-2">
                Severity
              </label>
              <select
                id="severity"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div>
              <label htmlFor="service-type" className="block text-sm font-medium text-gray-700 mb-2">
                Service Type (Optional)
              </label>
              <input
                id="service-type"
                type="text"
                value={serviceType}
                onChange={(e) => setServiceType(e.target.value)}
                placeholder="e.g., server, network, database"
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !issueDescription.trim()}
            className="w-full flex items-center justify-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <MagnifyingGlassIcon className="h-5 w-5 mr-2" />
            {loading ? 'Analyzing...' : 'Analyze Ticket'}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {analysis && (
        <div className="space-y-6">
          {/* Recommendation Card */}
          <div className={`border-2 rounded-lg p-6 ${getRecommendationColor()}`}>
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center">
                {getRecommendationIcon()}
                <div className="ml-3">
                  <h3 className="text-lg font-semibold">
                    {analysis.recommendation === 'existing_runbook' && 'Use Existing Runbook'}
                    {analysis.recommendation === 'generate_new' && 'Generate New Runbook'}
                    {analysis.recommendation === 'escalate' && 'Escalate to Human'}
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
          </div>

          {/* Matched Runbooks */}
          {analysis.matched_runbooks.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <DocumentTextIcon className="h-5 w-5 mr-2 text-blue-600" />
                Similar Runbooks Found ({analysis.matched_runbooks.length})
              </h3>
              <div className="space-y-4">
                {analysis.matched_runbooks.map((match, idx) => (
                  <div
                    key={match.id}
                    className={`border rounded-lg p-4 ${
                      idx === 0 && match.confidence_score >= analysis.threshold_used
                        ? 'border-green-300 bg-green-50'
                        : 'border-gray-200 bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-gray-900">{match.title}</h4>
                      <div className="flex items-center space-x-3">
                        <span className="text-sm font-medium text-blue-600">
                          {(match.confidence_score * 100).toFixed(0)}% match
                        </span>
                        {match.success_rate !== null && (
                          <span className="text-sm text-gray-600">
                            {(match.success_rate * 100).toFixed(0)}% success
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 mb-2">{match.reasoning}</p>
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span>Used {match.times_used}x</span>
                      {match.last_used && <span>Last: {new Date(match.last_used).toLocaleDateString()}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis.matched_runbooks.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No similar runbooks found in the knowledge base.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

