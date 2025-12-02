'use client';

import { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';

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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-gray-600">Loading decision analytics...</div>
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

  if (!summary) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <ChartBarIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No analytics yet</h3>
        <p className="text-gray-600 text-sm">
          Analytics will appear here as decisions are made and recommendations are used.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-slate-50">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Decision Engine Analytics</h2>
          <p className="text-gray-600 text-sm mt-1">
            Performance metrics for the decision engine over the past {days} days.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>

      {/* Recommendation Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Recommendations</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{summary.recommendations.total}</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="text-sm text-green-700">Accepted</div>
          <div className="text-2xl font-bold text-green-900 mt-1">{summary.recommendations.accepted}</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-sm text-red-700">Rejected</div>
          <div className="text-2xl font-bold text-red-900 mt-1">{summary.recommendations.rejected}</div>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="text-sm text-blue-700">Acceptance Rate</div>
          <div className="text-2xl font-bold text-blue-900 mt-1">
            {summary.recommendations.acceptance_rate.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Pattern Matching Metrics */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Pattern Matching</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-600">Total Searches</p>
            <p className="text-xl font-bold text-gray-900">{summary.pattern_matching.total_searches}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Successful Matches</p>
            <p className="text-xl font-bold text-green-600">{summary.pattern_matching.successful_matches}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Accuracy</p>
            <p className="text-xl font-bold text-blue-600">
              {summary.pattern_matching.accuracy.toFixed(1)}%
            </p>
          </div>
        </div>
        {summary.pattern_matching.avg_confidence !== null && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">Average Pattern Confidence</span>
              <span className="text-sm font-medium text-gray-900">
                {summary.pattern_matching.avg_confidence.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${summary.pattern_matching.avg_confidence}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Confidence Distribution */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Confidence Distribution</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <p className="text-xs text-green-700">High (≥80%)</p>
            <p className="text-2xl font-bold text-green-900">{summary.confidence_distribution.high}</p>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-xs text-yellow-700">Medium (50-80%)</p>
            <p className="text-2xl font-bold text-yellow-900">{summary.confidence_distribution.medium}</p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-xs text-red-700">Low (&lt;50%)</p>
            <p className="text-2xl font-bold text-red-900">{summary.confidence_distribution.low}</p>
          </div>
        </div>
      </div>

      {/* Decision Outcomes */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Outcomes</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-600">Auto-Execute</p>
            <p className="text-xl font-bold text-blue-600">{summary.decision_outcomes.auto_execute}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Manual Execute</p>
            <p className="text-xl font-bold text-gray-900">{summary.decision_outcomes.manual_execute}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Escalations</p>
            <p className="text-xl font-bold text-red-600">{summary.decision_outcomes.escalations}</p>
          </div>
        </div>
      </div>

      {/* Resolution Performance */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Resolution Performance</h3>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <p className="text-sm text-gray-600">Successful</p>
            <p className="text-xl font-bold text-green-600">{summary.resolution_performance.successful}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Failed</p>
            <p className="text-xl font-bold text-red-600">{summary.resolution_performance.failed}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Success Rate</p>
            <p className="text-xl font-bold text-blue-600">
              {summary.resolution_performance.success_rate.toFixed(1)}%
            </p>
          </div>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-green-600 h-3 rounded-full"
            style={{ width: `${summary.resolution_performance.success_rate}%` }}
          ></div>
        </div>
      </div>

      {/* Trends */}
      {trends.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Trends</h3>
            <select
              value={periodType}
              onChange={(e) => setPeriodType(e.target.value as 'daily' | 'weekly' | 'monthly')}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          <div className="space-y-2">
            {trends.slice(0, 10).map((trend, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <p className="text-xs text-gray-600">
                    {new Date(trend.period_start).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Acceptance: </span>
                    <span className="font-medium">{trend.acceptance_rate.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Accuracy: </span>
                    <span className="font-medium">{trend.pattern_accuracy.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Success: </span>
                    <span className="font-medium">{trend.resolution_success_rate.toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

