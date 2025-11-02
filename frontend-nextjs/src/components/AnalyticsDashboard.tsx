'use client';

import { useState, useEffect } from 'react';

interface UsageStats {
  period_days: number;
  total_uses: number;
  avg_confidence: number;
  success_rate: number;
  popular_runbooks: Array<{
    id: number;
    title: string;
    usage_count: number;
    avg_confidence: number;
  }>;
}

interface QualityMetrics {
  confidence_distribution: Record<string, number>;
  high_quality_runbooks: Array<{
    id: number;
    title: string;
    total_uses: number;
    success_rate: number;
  }>;
  underperforming_runbooks: Array<{
    id: number;
    title: string;
    total_uses: number;
    success_rate: number;
  }>;
  avg_execution_time_minutes: number;
  total_runbooks_with_stats: number;
}

interface CoverageAnalysis {
  total_approved: number;
  total_drafts: number;
  service_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
  common_issue_patterns: Array<{
    issue: string;
    runbook_count: number;
  }>;
}

interface SearchQuality {
  period_days: number;
  source_distribution: Record<string, number>;
  avg_citation_relevance: number;
  total_citations: number;
}

export default function AnalyticsDashboard() {
  const [loading, setLoading] = useState(true);
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [qualityMetrics, setQualityMetrics] = useState<QualityMetrics | null>(null);
  const [coverage, setCoverage] = useState<CoverageAnalysis | null>(null);
  const [searchQuality, setSearchQuality] = useState<SearchQuality | null>(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [usageRes, qualityRes, coverageRes, searchRes] = await Promise.all([
        fetch(`/api/v1/analytics/demo/usage-stats?days=${days}`),
        fetch('/api/v1/analytics/demo/quality-metrics'),
        fetch('/api/v1/analytics/demo/coverage'),
        fetch(`/api/v1/analytics/demo/search-quality?days=${days}`)
      ]);

      setUsageStats(await usageRes.json());
      setQualityMetrics(await qualityRes.json());
      setCoverage(await coverageRes.json());
      setSearchQuality(await searchRes.json());
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-gray-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-800">Analytics Dashboard</h1>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Period:</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border border-gray-300 rounded px-3 py-2 text-sm"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
        </div>
      </div>

      {/* Usage Statistics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-semibold mb-4 text-gray-800">Usage Statistics</h2>
        {usageStats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Total Uses</div>
              <div className="text-3xl font-bold text-blue-600">{usageStats.total_uses}</div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Avg Confidence</div>
              <div className="text-3xl font-bold text-green-600">
                {(usageStats.avg_confidence * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Success Rate</div>
              <div className="text-3xl font-bold text-purple-600">
                {usageStats.success_rate.toFixed(1)}%
              </div>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Period</div>
              <div className="text-3xl font-bold text-orange-600">{usageStats.period_days} days</div>
            </div>
          </div>
        )}

        {usageStats && usageStats.popular_runbooks.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-3 text-gray-700">Most Popular Runbooks</h3>
            <div className="space-y-2">
              {usageStats.popular_runbooks.map((rb) => (
                <div key={rb.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <div>
                    <div className="font-medium text-gray-800">{rb.title}</div>
                    <div className="text-sm text-gray-600">
                      Used {rb.usage_count} time{rb.usage_count !== 1 ? 's' : ''}
                    </div>
                  </div>
                  <div className="text-lg font-bold text-blue-600">
                    {(rb.avg_confidence * 100).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Coverage Analysis */}
      {coverage && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4 text-gray-800">Coverage Analysis</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-semibold mb-3 text-gray-700">Service Distribution</h3>
              <div className="space-y-2">
                {Object.entries(coverage.service_distribution).map(([service, count]) => (
                  <div key={service} className="flex justify-between items-center">
                    <span className="text-gray-700 capitalize">{service}</span>
                    <span className="font-bold text-gray-800">{count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-3 text-gray-700">Risk Distribution</h3>
              <div className="space-y-2">
                {Object.entries(coverage.risk_distribution).map(([risk, count]) => (
                  <div key={risk} className="flex justify-between items-center">
                    <span className="text-gray-700 capitalize">{risk}</span>
                    <span className="font-bold text-gray-800">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-6 pt-6 border-t">
            <h3 className="text-lg font-semibold mb-3 text-gray-700">Common Issue Patterns</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {coverage.common_issue_patterns.slice(0, 10).map((pattern, idx) => (
                <div key={idx} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                  <span className="text-sm text-gray-700 flex-1">{pattern.issue}</span>
                  <span className="font-bold text-blue-600 ml-4">{pattern.runbook_count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Quality Metrics */}
      {qualityMetrics && qualityMetrics.total_runbooks_with_stats > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4 text-gray-800">Quality Metrics</h2>
          {qualityMetrics.high_quality_runbooks.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3 text-green-700">High Quality Runbooks (&gt;70% success)</h3>
              <div className="space-y-2">
                {qualityMetrics.high_quality_runbooks.map((rb) => (
                  <div key={rb.id} className="flex justify-between items-center p-3 bg-green-50 rounded">
                    <div>
                      <div className="font-medium text-gray-800">{rb.title}</div>
                      <div className="text-sm text-gray-600">
                        {rb.total_uses} uses, {rb.success_rate}% success
                      </div>
                    </div>
                    <div className="text-2xl font-bold text-green-600">
                      {rb.success_rate.toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {qualityMetrics.underperforming_runbooks.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-3 text-red-700">Underperforming Runbooks (&lt;50% success)</h3>
              <div className="space-y-2">
                {qualityMetrics.underperforming_runbooks.map((rb) => (
                  <div key={rb.id} className="flex justify-between items-center p-3 bg-red-50 rounded">
                    <div>
                      <div className="font-medium text-gray-800">{rb.title}</div>
                      <div className="text-sm text-gray-600">
                        {rb.total_uses} uses, {rb.success_rate}% success
                      </div>
                    </div>
                    <div className="text-2xl font-bold text-red-600">
                      {rb.success_rate.toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Overall Stats */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-lg p-6 text-white">
        <h2 className="text-2xl font-bold mb-4">Overall Health</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm opacity-90">Total Approved</div>
            <div className="text-3xl font-bold">{coverage?.total_approved || 0}</div>
          </div>
          <div>
            <div className="text-sm opacity-90">Draft Runbooks</div>
            <div className="text-3xl font-bold">{coverage?.total_drafts || 0}</div>
          </div>
          <div>
            <div className="text-sm opacity-90">Avg Execution Time</div>
            <div className="text-3xl font-bold">
              {qualityMetrics?.avg_execution_time_minutes || 0} min
            </div>
          </div>
          <div>
            <div className="text-sm opacity-90">Total Uses</div>
            <div className="text-3xl font-bold">{usageStats?.total_uses || 0}</div>
          </div>
        </div>
      </div>
    </div>
  );
}


