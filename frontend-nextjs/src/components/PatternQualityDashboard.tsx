'use client';

import { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';

interface PatternQuality {
  pattern_id: number;
  pattern_type: string;
  quality_score: number | null;
  success_rate: number;
  usage_count: number;
}

interface QualityReport {
  total_patterns: number;
  high_quality_count: number;
  medium_quality_count: number;
  low_quality_count: number;
  deprecated_count: number;
  avg_quality_score: number;
  high_quality_patterns: PatternQuality[];
  low_quality_patterns: PatternQuality[];
  deprecated_patterns: Array<{
    pattern_id: number;
    pattern_type: string;
    last_reviewed_at: string | null;
  }>;
}

export function PatternQualityDashboard() {
  const { token } = useAuth();
  const [report, setReport] = useState<QualityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minQualityScore, setMinQualityScore] = useState<number | undefined>(undefined);
  const [includeDeprecated, setIncludeDeprecated] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchReport();
  }, [minQualityScore, includeDeprecated]);

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = apiConfig.endpoints.decision.qualityReport(minQualityScore, includeDeprecated);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch quality report');
      }
      const data = await response.json();
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch quality report');
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const handleDeprecate = async (patternId: number) => {
    setActionLoading(`deprecate-${patternId}`);
    try {
      const url = apiConfig.endpoints.decision.deprecatePattern(patternId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({ reason: 'Manual deprecation' }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to deprecate pattern');
      }
      
      await fetchReport();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to deprecate pattern');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestore = async (patternId: number) => {
    setActionLoading(`restore-${patternId}`);
    try {
      const url = apiConfig.endpoints.decision.restorePattern(patternId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers,
      });
      
      if (!response.ok) {
        throw new Error('Failed to restore pattern');
      }
      
      await fetchReport();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to restore pattern');
    } finally {
      setActionLoading(null);
    }
  };

  const handleUpdateQualityScore = async (patternId: number) => {
    setActionLoading(`update-${patternId}`);
    try {
      const url = apiConfig.endpoints.decision.updateQualityScore(patternId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers,
      });
      
      if (!response.ok) {
        throw new Error('Failed to update quality score');
      }
      
      await fetchReport();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update quality score');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center min-h-[320px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <div className="text-gray-600">Loading quality report...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
            <p className="text-red-800 font-medium">Error loading quality report</p>
          </div>
          <p className="text-red-700 mt-2 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center">
          <ChartBarIcon className="h-12 w-12 text-blue-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No patterns yet</h3>
          <p className="text-gray-600 text-sm">
            Execute some runbooks to generate patterns for quality analysis.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-slate-50">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Pattern Quality Dashboard</h2>
        <p className="text-gray-600 text-sm">
          Monitor and manage execution pattern quality and lifecycle
        </p>
      </div>

      {/* Overall Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Patterns</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{report.total_patterns}</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="text-sm text-green-700">High Quality</div>
          <div className="text-2xl font-bold text-green-900 mt-1">{report.high_quality_count}</div>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="text-sm text-yellow-700">Medium Quality</div>
          <div className="text-2xl font-bold text-yellow-900 mt-1">{report.medium_quality_count}</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-sm text-red-700">Low Quality</div>
          <div className="text-2xl font-bold text-red-900 mt-1">{report.low_quality_count}</div>
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-700">Deprecated</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{report.deprecated_count}</div>
        </div>
      </div>

      {/* Average Quality Score */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Average Quality Score</h3>
        <div className="flex items-center gap-4">
          <div className="text-4xl font-bold text-blue-600">
            {report.avg_quality_score.toFixed(1)}
          </div>
          <div className="flex-1">
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-blue-600 h-4 rounded-full"
                style={{ width: `${report.avg_quality_score}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* High Quality Patterns */}
      {report.high_quality_patterns.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">High Quality Patterns</h3>
          <div className="space-y-2">
            {report.high_quality_patterns.map((pattern) => (
              <div
                key={pattern.pattern_id}
                className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg"
              >
                <div>
                  <div className="font-medium text-gray-900">
                    Pattern #{pattern.pattern_id} ({pattern.pattern_type})
                  </div>
                  <div className="text-sm text-gray-600">
                    Quality: {pattern.quality_score?.toFixed(1) || 'N/A'}% | 
                    Success: {pattern.success_rate.toFixed(1)}% | 
                    Usage: {pattern.usage_count}
                  </div>
                </div>
                <button
                  onClick={() => handleUpdateQualityScore(pattern.pattern_id)}
                  disabled={actionLoading === `update-${pattern.pattern_id}`}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading === `update-${pattern.pattern_id}` ? 'Updating...' : 'Update Score'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Low Quality Patterns */}
      {report.low_quality_patterns.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Low Quality Patterns</h3>
          <div className="space-y-2">
            {report.low_quality_patterns.map((pattern) => (
              <div
                key={pattern.pattern_id}
                className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg"
              >
                <div>
                  <div className="font-medium text-gray-900">
                    Pattern #{pattern.pattern_id} ({pattern.pattern_type})
                  </div>
                  <div className="text-sm text-gray-600">
                    Quality: {pattern.quality_score?.toFixed(1) || 'N/A'}% | 
                    Success: {pattern.success_rate.toFixed(1)}% | 
                    Usage: {pattern.usage_count}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleUpdateQualityScore(pattern.pattern_id)}
                    disabled={actionLoading === `update-${pattern.pattern_id}`}
                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {actionLoading === `update-${pattern.pattern_id}` ? 'Updating...' : 'Update'}
                  </button>
                  <button
                    onClick={() => handleDeprecate(pattern.pattern_id)}
                    disabled={actionLoading === `deprecate-${pattern.pattern_id}`}
                    className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                  >
                    {actionLoading === `deprecate-${pattern.pattern_id}` ? 'Deprecating...' : 'Deprecate'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Deprecated Patterns */}
      {report.deprecated_patterns.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Deprecated Patterns</h3>
          <div className="space-y-2">
            {report.deprecated_patterns.map((pattern) => (
              <div
                key={pattern.pattern_id}
                className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg"
              >
                <div>
                  <div className="font-medium text-gray-900">
                    Pattern #{pattern.pattern_id} ({pattern.pattern_type})
                  </div>
                  <div className="text-sm text-gray-600">
                    Last reviewed: {pattern.last_reviewed_at ? new Date(pattern.last_reviewed_at).toLocaleDateString() : 'Never'}
                  </div>
                </div>
                <button
                  onClick={() => handleRestore(pattern.pattern_id)}
                  disabled={actionLoading === `restore-${pattern.pattern_id}`}
                  className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {actionLoading === `restore-${pattern.pattern_id}` ? 'Restoring...' : 'Restore'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

