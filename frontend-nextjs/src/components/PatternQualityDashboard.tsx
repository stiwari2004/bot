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
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

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
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            <span className="ml-3 text-neutral-600 font-medium">Loading quality report...</span>
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
            <p className="text-error-800 font-medium">Error loading quality report</p>
          </div>
          <p className="text-error-700 mt-2 text-sm">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!report) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="text-center py-12">
            <div className="p-1.5 rounded-lg bg-primary-100 mx-auto mb-4 w-fit">
              <ChartBarIcon className="h-12 w-12 text-primary-600" />
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">No patterns yet</h3>
            <p className="text-neutral-600 text-sm">
              Execute some runbooks to generate patterns for quality analysis.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center mb-2">
            <div className="p-1.5 rounded-lg bg-secondary-100 mr-3">
              <ChartBarIcon className="h-6 w-6 text-secondary-600" />
            </div>
            <h2 className="text-2xl font-semibold text-neutral-900">Pattern Quality Dashboard</h2>
          </div>
          <p className="text-sm text-neutral-600">
            Monitor and manage execution pattern quality and lifecycle
          </p>
        </CardHeader>
      </Card>

      {/* Overall Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card variant="elevated">
          <CardContent padding="md">
            <div className="text-sm text-neutral-600">Total Patterns</div>
            <div className="text-2xl font-bold text-neutral-900 mt-1">{report.total_patterns}</div>
          </CardContent>
        </Card>
        <Card variant="elevated" className="bg-success-50 border-success-200">
          <CardContent padding="md">
            <div className="text-sm text-success-700">High Quality</div>
            <div className="text-2xl font-bold text-success-900 mt-1">{report.high_quality_count}</div>
          </CardContent>
        </Card>
        <Card variant="elevated" className="bg-warning-50 border-warning-200">
          <CardContent padding="md">
            <div className="text-sm text-warning-700">Medium Quality</div>
            <div className="text-2xl font-bold text-warning-900 mt-1">{report.medium_quality_count}</div>
          </CardContent>
        </Card>
        <Card variant="elevated" className="bg-error-50 border-error-200">
          <CardContent padding="md">
            <div className="text-sm text-error-700">Low Quality</div>
            <div className="text-2xl font-bold text-error-900 mt-1">{report.low_quality_count}</div>
          </CardContent>
        </Card>
        <Card variant="elevated" className="bg-neutral-50 border-neutral-200">
          <CardContent padding="md">
            <div className="text-sm text-neutral-700">Deprecated</div>
            <div className="text-2xl font-bold text-neutral-900 mt-1">{report.deprecated_count}</div>
          </CardContent>
        </Card>
      </div>

      {/* Average Quality Score */}
      <Card variant="elevated">
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-900">Average Quality Score</h3>
        </CardHeader>
        <CardContent padding="md">
          <div className="flex items-center gap-4">
            <div className="text-4xl font-bold text-primary-600">
              {report.avg_quality_score.toFixed(1)}
            </div>
            <div className="flex-1">
              <div className="w-full bg-neutral-200 rounded-full h-4">
                <div
                  className="bg-primary-600 h-4 rounded-full"
                  style={{ width: `${report.avg_quality_score}%` }}
                ></div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* High Quality Patterns */}
      {report.high_quality_patterns.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <h3 className="text-lg font-semibold text-neutral-900">High Quality Patterns</h3>
          </CardHeader>
          <CardContent padding="md">
            <div className="space-y-2">
              {report.high_quality_patterns.map((pattern) => (
                <Card
                  key={pattern.pattern_id}
                  variant="default"
                  className="bg-success-50 border-success-200"
                >
                  <CardContent padding="sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-neutral-900">
                          Pattern #{pattern.pattern_id} ({pattern.pattern_type})
                        </div>
                        <div className="text-sm text-neutral-600">
                          Quality: {pattern.quality_score?.toFixed(1) || 'N/A'}% | 
                          Success: {pattern.success_rate.toFixed(1)}% | 
                          Usage: {pattern.usage_count}
                        </div>
                      </div>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleUpdateQualityScore(pattern.pattern_id)}
                        disabled={actionLoading === `update-${pattern.pattern_id}`}
                        isLoading={actionLoading === `update-${pattern.pattern_id}`}
                      >
                        Update Score
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Low Quality Patterns */}
      {report.low_quality_patterns.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <h3 className="text-lg font-semibold text-neutral-900">Low Quality Patterns</h3>
          </CardHeader>
          <CardContent padding="md">
            <div className="space-y-2">
              {report.low_quality_patterns.map((pattern) => (
                <Card
                  key={pattern.pattern_id}
                  variant="default"
                  className="bg-error-50 border-error-200"
                >
                  <CardContent padding="sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-neutral-900">
                          Pattern #{pattern.pattern_id} ({pattern.pattern_type})
                        </div>
                        <div className="text-sm text-neutral-600">
                          Quality: {pattern.quality_score?.toFixed(1) || 'N/A'}% | 
                          Success: {pattern.success_rate.toFixed(1)}% | 
                          Usage: {pattern.usage_count}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleUpdateQualityScore(pattern.pattern_id)}
                          disabled={actionLoading === `update-${pattern.pattern_id}`}
                          isLoading={actionLoading === `update-${pattern.pattern_id}`}
                        >
                          Update
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handleDeprecate(pattern.pattern_id)}
                          disabled={actionLoading === `deprecate-${pattern.pattern_id}`}
                          isLoading={actionLoading === `deprecate-${pattern.pattern_id}`}
                        >
                          Deprecate
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Deprecated Patterns */}
      {report.deprecated_patterns.length > 0 && (
        <Card variant="elevated">
          <CardHeader>
            <h3 className="text-lg font-semibold text-neutral-900">Deprecated Patterns</h3>
          </CardHeader>
          <CardContent padding="md">
            <div className="space-y-2">
              {report.deprecated_patterns.map((pattern) => (
                <Card
                  key={pattern.pattern_id}
                  variant="default"
                  className="bg-neutral-50 border-neutral-200"
                >
                  <CardContent padding="sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-neutral-900">
                          Pattern #{pattern.pattern_id} ({pattern.pattern_type})
                        </div>
                        <div className="text-sm text-neutral-600">
                          Last reviewed: {pattern.last_reviewed_at ? new Date(pattern.last_reviewed_at).toLocaleDateString() : 'Never'}
                        </div>
                      </div>
                      <Button
                        variant="success"
                        size="sm"
                        onClick={() => handleRestore(pattern.pattern_id)}
                        disabled={actionLoading === `restore-${pattern.pattern_id}`}
                        isLoading={actionLoading === `restore-${pattern.pattern_id}`}
                      >
                        Restore
                      </Button>
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








