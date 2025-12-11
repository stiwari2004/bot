'use client';

import { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

interface AnalyticsSummary {
  period: {
    start: string;
    end: string;
    days: number;
  };
  recommendations: {
    total: number;
    accepted: number;
    rejected: number;
    acceptance_rate: number;
  };
  pattern_matching: {
    total_searches: number;
    successful_matches: number;
    accuracy: number;
    avg_confidence: number | null;
  };
  confidence_distribution: {
    high: number;
    medium: number;
    low: number;
    avg_confidence: number | null;
  };
  decision_outcomes: {
    auto_execute: number;
    manual_execute: number;
    escalations: number;
  };
  resolution_performance: {
    successful: number;
    failed: number;
    success_rate: number;
  };
}

interface Trend {
  period_start: string;
  period_end: string;
  acceptance_rate: number;
  pattern_accuracy: number;
  avg_confidence: number | null;
  resolution_success_rate: number;
}

export function DecisionAnalyticsDashboard() {
  const { token } = useAuth();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [periodType, setPeriodType] = useState<'daily' | 'weekly' | 'monthly'>('daily');

  useEffect(() => {
    fetchAnalytics();
    fetchTrends();
  }, [days, periodType]);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);

    try {
      const url = apiConfig.endpoints.analytics.decisionEngine(days);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch analytics');
      }

      const data = await response.json();
      setSummary(data);
    } catch (err) {
      console.error('Error fetching analytics:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  };

  const fetchTrends = async () => {
    try {
      const url = apiConfig.endpoints.analytics.decisionEngineTrends(periodType);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch trends');
      }

      const data = await response.json();
      setTrends(data);
    } catch (err) {
      console.error('Error fetching trends:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <div className="text-neutral-600 font-medium">Loading decision analytics...</div>
        </div>
      </div>
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

  if (!summary) {
    return (
      <Card variant="outlined" className="border-neutral-200 bg-neutral-50">
        <CardContent padding="lg">
          <div className="text-center py-8">
            <div className="mx-auto w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
              <ChartBarIcon className="h-8 w-8 text-neutral-400" />
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">No analytics yet</h3>
            <p className="text-neutral-600 text-sm">
              Analytics will appear here as decisions are made and recommendations are used.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-gradient-to-br from-neutral-50 via-white to-neutral-50">
      {/* Header */}
      <Card variant="elevated">
        <CardContent padding="md">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-3xl font-bold text-neutral-900 mb-1">Decision Engine Analytics</h2>
              <p className="text-neutral-600 text-sm">
                Performance metrics for the decision engine over the past {days} days.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-sm font-semibold text-neutral-700">Period</label>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="px-4 py-2.5 border-2 border-neutral-300 rounded-lg text-sm font-semibold text-neutral-900 bg-white hover:border-primary-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recommendation Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card variant="elevated">
          <CardContent padding="md">
            <div className="text-sm font-semibold text-neutral-600 mb-1">Total Recommendations</div>
            <div className="text-3xl font-bold text-neutral-900 bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">{summary.recommendations.total}</div>
          </CardContent>
        </Card>
        <Card variant="outlined" className="border-success-200 bg-success-50">
          <CardContent padding="md">
            <div className="text-sm font-semibold text-success-700 mb-1">Accepted</div>
            <div className="text-3xl font-bold text-success-900">{summary.recommendations.accepted}</div>
          </CardContent>
        </Card>
        <Card variant="outlined" className="border-error-200 bg-error-50">
          <CardContent padding="md">
            <div className="text-sm font-semibold text-error-700 mb-1">Rejected</div>
            <div className="text-3xl font-bold text-error-900">{summary.recommendations.rejected}</div>
          </CardContent>
        </Card>
        <Card variant="outlined" className="border-primary-200 bg-primary-50">
          <CardContent padding="md">
            <div className="text-sm font-semibold text-primary-700 mb-1">Acceptance Rate</div>
            <div className="text-3xl font-bold text-primary-900">
              {summary.recommendations.acceptance_rate.toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pattern Matching Metrics */}
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-900">Pattern Matching</h3>
        </CardHeader>
        <CardContent padding="md">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <p className="text-sm font-semibold text-neutral-600 mb-1">Total Searches</p>
              <p className="text-2xl font-bold text-neutral-900">{summary.pattern_matching.total_searches}</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-600 mb-1">Successful Matches</p>
              <p className="text-2xl font-bold text-success-600">{summary.pattern_matching.successful_matches}</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-600 mb-1">Accuracy</p>
              <p className="text-2xl font-bold text-primary-600">
                {summary.pattern_matching.accuracy.toFixed(1)}%
              </p>
            </div>
          </div>
          {summary.pattern_matching.avg_confidence !== null && (
            <div className="mt-4 pt-4 border-t border-neutral-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-neutral-600">Average Pattern Confidence</span>
                <span className="text-sm font-bold text-neutral-900">
                  {summary.pattern_matching.avg_confidence.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-neutral-200 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-primary-500 to-primary-600 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${summary.pattern_matching.avg_confidence}%` }}
                ></div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confidence Distribution */}
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-900">Confidence Distribution</h3>
        </CardHeader>
        <CardContent padding="md">
          <div className="grid grid-cols-3 gap-4">
            <Card variant="outlined" className="border-success-200 bg-success-50">
              <CardContent padding="sm">
                <p className="text-xs font-semibold text-success-700 mb-1">High (≥80%)</p>
                <p className="text-2xl font-bold text-success-900">{summary.confidence_distribution.high}</p>
              </CardContent>
            </Card>
            <Card variant="outlined" className="border-warning-200 bg-warning-50">
              <CardContent padding="sm">
                <p className="text-xs font-semibold text-warning-700 mb-1">Medium (50-80%)</p>
                <p className="text-2xl font-bold text-warning-900">{summary.confidence_distribution.medium}</p>
              </CardContent>
            </Card>
            <Card variant="outlined" className="border-error-200 bg-error-50">
              <CardContent padding="sm">
                <p className="text-xs font-semibold text-error-700 mb-1">Low (&lt;50%)</p>
                <p className="text-2xl font-bold text-error-900">{summary.confidence_distribution.low}</p>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      {/* Decision Outcomes */}
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-900">Decision Outcomes</h3>
        </CardHeader>
        <CardContent padding="md">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm font-semibold text-neutral-600 mb-1">Auto-Execute</p>
              <p className="text-2xl font-bold text-primary-600">{summary.decision_outcomes.auto_execute}</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-600 mb-1">Manual Execute</p>
              <p className="text-2xl font-bold text-neutral-900">{summary.decision_outcomes.manual_execute}</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-600 mb-1">Escalations</p>
              <p className="text-2xl font-bold text-error-600">{summary.decision_outcomes.escalations}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Resolution Performance */}
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-900">Resolution Performance</h3>
        </CardHeader>
        <CardContent padding="md">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <p className="text-sm font-semibold text-neutral-600 mb-1">Successful</p>
              <p className="text-2xl font-bold text-success-600">{summary.resolution_performance.successful}</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-600 mb-1">Failed</p>
              <p className="text-2xl font-bold text-error-600">{summary.resolution_performance.failed}</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-600 mb-1">Success Rate</p>
              <p className="text-2xl font-bold text-primary-600">
                {summary.resolution_performance.success_rate.toFixed(1)}%
              </p>
            </div>
          </div>
          <div className="w-full bg-neutral-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-success-500 to-success-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${summary.resolution_performance.success_rate}%` }}
            ></div>
          </div>
        </CardContent>
      </Card>

      {/* Trends */}
      {trends.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-neutral-900">Trends</h3>
              <select
                value={periodType}
                onChange={(e) => setPeriodType(e.target.value as 'daily' | 'weekly' | 'monthly')}
                className="px-3 py-2 border-2 border-neutral-300 rounded-lg text-sm font-semibold text-neutral-900 bg-white hover:border-primary-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
          </CardHeader>
          <CardContent padding="md">
            <div className="space-y-2">
              {trends.slice(0, 10).map((trend, idx) => (
                <Card key={idx} variant="default" className="bg-neutral-50">
                  <CardContent padding="sm">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <p className="text-xs font-semibold text-neutral-600">
                          {new Date(trend.period_start).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <div>
                          <span className="text-neutral-600">Acceptance: </span>
                          <span className="font-semibold text-neutral-900">{trend.acceptance_rate.toFixed(1)}%</span>
                        </div>
                        <div>
                          <span className="text-neutral-600">Accuracy: </span>
                          <span className="font-semibold text-neutral-900">{trend.pattern_accuracy.toFixed(1)}%</span>
                        </div>
                        <div>
                          <span className="text-neutral-600">Success: </span>
                          <span className="font-semibold text-neutral-900">{trend.resolution_success_rate.toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

