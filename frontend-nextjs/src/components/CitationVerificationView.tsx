'use client';

import { useState, useEffect } from 'react';
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { apiConfig } from '@/lib/api-config';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface CitationHealth {
  runbook_id: number;
  total_citations: number;
  verified: number;
  broken: number;
  pending: number;
  avg_quality_score: number | null;
  health_status: string;
  broken_citations?: Array<{
    citation_id: number;
    verification_status: string;
    overall_quality_score: number | null;
  }>;
}

interface CitationVerificationViewProps {
  runbookId: number;
}

export function CitationVerificationView({ runbookId }: CitationVerificationViewProps) {
  const { token } = useAuth();
  const [health, setHealth] = useState<CitationHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    fetchHealth();
  }, [runbookId]);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);

    try {
      const url = apiConfig.endpoints.runbooks.citationHealth(runbookId);
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) {
        throw new Error('Failed to fetch citation health');
      }

      const data = await response.json();
      setHealth(data);
    } catch (err) {
      console.error('Error fetching citation health:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch citation health');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    setError(null);

    try {
      const url = apiConfig.endpoints.runbooks.verifyCitations(runbookId);
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
        throw new Error('Failed to verify citations');
      }

      // Refresh health data
      await fetchHealth();
    } catch (err) {
      console.error('Error verifying citations:', err);
      setError(err instanceof Error ? err.message : 'Failed to verify citations');
    } finally {
      setVerifying(false);
    }
  };

  const getHealthStatusColor = (status: string): string => {
    switch (status) {
      case 'healthy':
        return 'bg-success-100 text-success-800';
      case 'unhealthy':
        return 'bg-error-100 text-error-800';
      case 'low_quality':
        return 'bg-warning-100 text-warning-800';
      case 'needs_verification':
        return 'bg-primary-100 text-primary-800';
      default:
        return 'bg-neutral-100 text-neutral-800';
    }
  };

  if (loading) {
    return (
      <Card variant="elevated">
        <CardContent padding="lg">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <span className="ml-3 text-neutral-600 font-medium">Loading citation health...</span>
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
            <XCircleIcon className="h-5 w-5 text-error-600" />
            <p className="text-sm text-error-800">Error: {error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!health) {
    return null;
  }

  return (
    <div className="space-y-4">
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center mb-2">
              <div className="p-1.5 rounded-lg bg-secondary-100 mr-3">
                <CheckCircleIcon className="h-6 w-6 text-secondary-600" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900">Citation Verification</h3>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={handleVerify}
              disabled={verifying}
              isLoading={verifying}
              leftIcon={<ArrowPathIcon className="h-4 w-4" />}
            >
              {verifying ? 'Verifying...' : 'Verify Citations'}
            </Button>
          </div>
        </CardHeader>

        <CardContent padding="md">
          {/* Health Status */}
          <Card variant="default" className="mb-4">
            <CardContent padding="md">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-semibold text-neutral-900">Health Status</span>
                <span className={`text-sm px-3 py-1 rounded ${getHealthStatusColor(health.health_status)}`}>
                  {health.health_status.replace('_', ' ').toUpperCase()}
                </span>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div>
                  <p className="text-xs text-neutral-600">Total</p>
                  <p className="text-lg font-semibold text-neutral-900">{health.total_citations}</p>
                </div>
                <div>
                  <p className="text-xs text-neutral-600">Verified</p>
                  <p className="text-lg font-semibold text-success-600">{health.verified}</p>
                </div>
                <div>
                  <p className="text-xs text-neutral-600">Broken</p>
                  <p className="text-lg font-semibold text-error-600">{health.broken}</p>
                </div>
                <div>
                  <p className="text-xs text-neutral-600">Pending</p>
                  <p className="text-lg font-semibold text-warning-600">{health.pending}</p>
                </div>
              </div>

              {/* Average Quality Score */}
              {health.avg_quality_score !== null && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-neutral-600">Average Quality Score</span>
                    <span className="text-sm font-semibold text-neutral-900">
                      {health.avg_quality_score.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-neutral-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        health.avg_quality_score >= 80
                          ? 'bg-success-600'
                          : health.avg_quality_score >= 60
                          ? 'bg-warning-600'
                          : 'bg-error-600'
                      }`}
                      style={{ width: `${health.avg_quality_score}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Broken Citations */}
          {health.broken > 0 && health.broken_citations && health.broken_citations.length > 0 && (
            <Card variant="default" className="bg-error-50 border-error-200">
              <CardContent padding="md">
                <div className="flex items-center gap-2 mb-3">
                  <XCircleIcon className="h-5 w-5 text-error-600" />
                  <h4 className="text-sm font-semibold text-error-900">Broken Citations</h4>
                </div>
                <div className="space-y-2">
                  {health.broken_citations.map((citation) => (
                    <Card key={citation.citation_id} variant="default" className="bg-white border-error-200">
                      <CardContent padding="sm">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-neutral-900">Citation #{citation.citation_id}</span>
                          <span className="text-xs px-2 py-1 bg-error-100 text-error-800 rounded">
                            {citation.verification_status}
                          </span>
                        </div>
                        {citation.overall_quality_score !== null && (
                          <p className="text-xs text-neutral-600 mt-1">
                            Quality: {citation.overall_quality_score.toFixed(1)}%
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {health.total_citations === 0 && (
            <Card variant="elevated">
              <CardContent padding="lg">
                <div className="text-center py-12">
                  <div className="p-1.5 rounded-lg bg-neutral-100 mx-auto mb-4 w-fit">
                    <CheckCircleIcon className="h-12 w-12 text-neutral-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-neutral-900 mb-2">No citations found</h3>
                  <p className="text-neutral-600 text-sm">
                    This runbook doesn't have any citations to verify.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>
    </div>
  );
}








